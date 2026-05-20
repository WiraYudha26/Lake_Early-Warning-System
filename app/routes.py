import os
import pandas as pd
from flask import Blueprint, render_template, request, jsonify
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import smtplib
import pytz
import requests
from app.utils import (
    angin_kencang_warning, gelombang_tinggi_warning, arus_gelombang_warning,
    klasifikasi_umum, level_peringatan, generate_wave_plot,
    generate_wave_current_plot, generate_windrose, derajat_ke_arah,
    calculate_current_direction, calculate_fetch, calculate_depth,
    adjust_fetch_for_barriers, calculate_slope, calculate_hs,
    calculate_wave_current, predict_realtime, rute_dict,
    generate_rute_list, generate_rute_arah_dict,
    harbor_coords  # satu sumber kebenaran dari utils.py
)

main = Blueprint('main', __name__, template_folder='../templates')

# Cache realtime per pelabuhan
realtime_cache = {}
CACHE_EXPIRY_MINUTES = 10

# ---------- ROUTES ----------
@main.route('/', endpoint='home')
def landing():
    return render_template('landing.html')

@main.route('/map')
def map_page():
    return render_template('index.html')

@main.route('/about')
def about_page():
    return render_template('about.html')

@main.route('/contact', methods=["GET"])
def contact_page():
    return render_template('contact.html')

# ---------- FORM KONTAK (AJAX-Compatible) ----------
@main.route("/contact", methods=["POST"])
def handle_contact():
    name = request.form.get("name")
    email = request.form.get("email")
    subject = request.form.get("subject")
    message = request.form.get("message")

    # Susun isi email
    content = f"Pesan dari: {name} <{email}>\nSubjek: {subject}\n\n{message}"
    msg = MIMEText(content)
    msg["Subject"] = f"[SIGADANA] {subject}"
    msg["From"] = os.getenv("EMAIL_FROM") or email
    msg["To"] = os.getenv("EMAIL_TO") or "your@email.com"

    try:
        # Koneksi ke Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(
                os.getenv("EMAIL_USER"), 
                os.getenv("EMAIL_PASS")
            )
            server.send_message(msg)

        return jsonify({
            "status": "success",
            "message": "Pesan Anda telah berhasil dikirim. Terima kasih!"
        })

    except Exception as e:
        print("Gagal mengirim email:", e)
        return jsonify({
            "status": "danger",
            "message": "Terjadi kesalahan saat mengirim pesan. Coba lagi nanti."
        }), 500

# Convert nama "bulan" di Indonesia
def format_bulan_indonesia(dt):
    nama_bulan = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember"
    }
    bulan = dt.strftime("%B")
    tahun = dt.year
    return f"{nama_bulan.get(bulan, bulan)} {tahun}"

# Setting peringatan
def get_warning_level(level):     
    return {
        3: "danger",
        2: "high",
        1: "alert",
        0: "safe"
    }.get(level, "safe")

# ---------- FUNGSI MONITORING DATA HISTORIS ----------
@main.route("/monitoring")
def monitoring():

    pelabuhan = request.args.get("pelabuhan")
    datetime_str = request.args.get("datetime")

    if not pelabuhan:
        return render_template("index.html", pelabuhan=None, data=None, warning="Pelabuhan tidak dipilih.")

    filename = f"{pelabuhan}_gelombang.csv"
    basedir = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(basedir, "..", "data", "output_gelombang", filename)

    if not os.path.exists(filepath):
        warning = f"File CSV untuk {pelabuhan} tidak ditemukan di folder data/output_gelombang."
        return render_template("index.html", pelabuhan=pelabuhan, data=None, warning=warning)

    # Muat CSV
    df = pd.read_csv(filepath, parse_dates=["time"])
    df.rename(columns={"time": "timestamp"}, inplace=True)
    
    # beri tahu pandas bahwa 'time' itu UTC:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp_wib"] = df["timestamp"].dt.tz_convert("Asia/Jakarta")

    data = None
    warning = None
    target_time = None

    # === Ambil data sesuai waktu ===
    if datetime_str:
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
            target_time = pytz.timezone("Asia/Jakarta").localize(dt)
        except Exception as e:
            warning = f"Format tanggal salah: {e}"
            return render_template("index.html", pelabuhan=pelabuhan, data=None, warning=warning, suhu=None, kelembaban=None)

        row = df[df["timestamp_wib"].dt.strftime("%Y-%m-%d %H:%M") == target_time.strftime("%Y-%m-%d %H:%M")]
     
        if row.empty:
            waktu_human = target_time.strftime("%d-%m-%Y pukul %H:%M")
            warning = f"Tidak ada data pada {waktu_human}"
            return render_template("index.html", pelabuhan=pelabuhan, data=None, warning=warning, suhu=None, kelembaban=None)
        else:
            row = row.iloc[0]
            data = row.to_dict()            
            data["timestamp_wib"] = row["timestamp"].tz_convert("Asia/Jakarta")
            suhu = data.get("temperature_2m")
            kelembaban = data.get("relative_humidity_2m")
    else:
        data = df.tail(1).iloc[0].to_dict()
        target_time = pd.to_datetime(data["timestamp"])
        data["timestamp_wib"] = data["timestamp"].tz_convert("Asia/Jakarta")
        suhu = data.get("temperature_2m")
        kelembaban = data.get("relative_humidity_2m")
        
    # === Hitung arah arus permukaan (berdasarkan arah angin saat itu) ===
    if "wind_direction_10m" in data:
        data["wind_dir_text"] = derajat_ke_arah(data["wind_direction_10m"])
        data["current_direction"] = calculate_current_direction(data["wind_direction_10m"])
        data["current_direction_text"] = derajat_ke_arah(data["current_direction"])
    else:
        data["current_direction"] = 0.0
        data["current_direction_text"] = "Kesalahan Sensor!"
    
    # === Klasifikasi ambang bahaya ===
    peringatan_angin = angin_kencang_warning(data.get("wind_speed_10m", 0))
    peringatan_gelombang = gelombang_tinggi_warning(data.get("Hs_m", 0))
    peringatan_arus = arus_gelombang_warning(data.get("Wave_Current", 0))

    peringatan_umum = klasifikasi_umum(peringatan_angin, peringatan_gelombang, peringatan_arus)

    # === Arah angin dominan (per hari target) ===
    day_data = df[df["timestamp_wib"].dt.date == target_time.date()]
    arah_dominan_label = None
    dominant_deg = None

    if not day_data.empty and "wind_direction_10m" in day_data.columns:
        dominant_deg = day_data["wind_direction_10m"].mode().iloc[0]
        arah_dominan_label = derajat_ke_arah(dominant_deg)
    
    # === Grafik bulanan (bulan & tahun target) ===
    month_data = df[
        (df["timestamp"].dt.month == target_time.month) &
        (df["timestamp"].dt.year == target_time.year)
    ]

    img_timeseries = generate_wave_plot(month_data) or ""
    img_wavecurrent = generate_wave_current_plot(month_data) or ""
    img_windrose = generate_windrose(month_data) or ""

    bulan_label = format_bulan_indonesia(target_time)
    
    # === Return ke template ===
    return render_template(
        "index.html",
        pelabuhan=pelabuhan,
        data=data,
        suhu=suhu,
        kelembaban=kelembaban,
        bulan_label=bulan_label,
        warning=warning,
        peringatan_angin=peringatan_angin,
        peringatan_gelombang=peringatan_gelombang,
        peringatan_arus=peringatan_arus,
        peringatan_umum=peringatan_umum,
        arah_dominan=dominant_deg,
        arah_dominan_label=arah_dominan_label,
        arah_dominan_derajat=round(dominant_deg, 1) if dominant_deg is not None else None,
        grafik_timeseries=img_timeseries,
        grafik_wavecurrent=img_wavecurrent,
        grafik_windrose=img_windrose,
        warning_level=get_warning_level(
            max([
                level_peringatan(peringatan_angin),
                level_peringatan(peringatan_gelombang),
                level_peringatan(peringatan_arus)
            ])
        )
    )

# ---------- FUNGSI AMBIL DATA CUACA PER JAM DALAM ZONA LOKAL ----------

# Ambil cuaca 3 jam ke depan dari Open-Meteo untuk koordinat tertentu
# Mengembalikan tuple (df_filtered, times_needed) agar times_needed selalu sinkron
def fetch_realtime_weather_by_coords(lat, lon):
    # Dihitung per-request agar selalu fresh
    now = datetime.now(pytz.timezone("Asia/Jakarta")).replace(minute=0, second=0, microsecond=0)
    times_needed = [now + timedelta(hours=i) for i in range(3)]
    start_date = now.strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m"
        f"&timezone=Asia%2FJakarta"
        f"&start_date={start_date}&end_date={end_date}"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        df_weather = pd.DataFrame(data["hourly"])
        df_weather["time"] = pd.to_datetime(df_weather["time"])
        df_weather.set_index("time", inplace=True)

        # Hilangkan timezone agar konsisten
        df_weather.index = df_weather.index.tz_localize(None)

        requested_times = [t.replace(tzinfo=None) for t in times_needed]

        matched_rows = []
        for req in requested_times:
            deltas = df_weather.index - req
            seconds = [abs(d.total_seconds()) for d in deltas]
            nearest_idx = seconds.index(min(seconds))
            matched_rows.append(df_weather.iloc[nearest_idx])

        df_filtered = pd.DataFrame(matched_rows)
        df_filtered.index = requested_times

        return df_filtered, times_needed

    except Exception as e:
        print(f"[ERROR] Gagal ambil data cuaca untuk lat={lat}, lon={lon}: {e}")
        return None, []

# Ambil cuaca 3 jam ke depan dari Open-Meteo untuk pelabuhan
def fetch_realtime_weather(pelabuhan):
    if pelabuhan not in harbor_coords:
        print(f"[ERROR] Pelabuhan {pelabuhan} tidak dikenali")
        return None, []
    lat, lon = harbor_coords[pelabuhan]
    return fetch_realtime_weather_by_coords(lat, lon)

# ---------- ENDPOINT MONITORING REAL-TIME ----------
@main.route("/realtime/<pelabuhan>")
def realtime(pelabuhan):

    # Validasi pelabuhan
    print(f"[INFO] Memproses /realtime/{pelabuhan}")

    if pelabuhan not in harbor_coords:
        print(f"[ERROR] Pelabuhan {pelabuhan} tidak dikenali")
        return render_template(
            "realtime.html",
            pelabuhan=pelabuhan,
            warning=f"Pelabuhan {pelabuhan} tidak dikenali"
        )

    # Cek cache
    now = datetime.now(pytz.timezone("Asia/Jakarta")).replace(minute=0, second=0, microsecond=0)
    if pelabuhan in realtime_cache and realtime_cache[pelabuhan]["expires"] > now:
        print(f"[INFO] Menggunakan data dari cache untuk {pelabuhan}")
        cache = realtime_cache[pelabuhan]["data"]
        return render_template(
            "realtime.html",
            pelabuhan=pelabuhan,
            data=cache["data"],
            suhu=cache["suhu"],
            kelembaban=cache["kelembaban"],
            peringatan_umum=cache["peringatan_umum"],
            peringatan_angin=cache["peringatan_angin"],
            peringatan_gelombang=cache["peringatan_gelombang"],
            peringatan_arus=cache["peringatan_arus"],
            arah_dominan_label=cache["arah_dominan_label"],
            warning_level=cache["warning_level"],
            prediksi=cache["prediksi"]
        )

    # Ambil data cuaca real-time
    print("[INFO] Ambil data cuaca real-time")
    
    df_weather, times_needed = fetch_realtime_weather(pelabuhan)
    if df_weather is None or df_weather.empty:
        print(f"[ERROR] Gagal mengambil data cuaca untuk {pelabuhan}")
        return render_template(
            "realtime.html",
            pelabuhan=pelabuhan,
            warning="Gagal mengambil data cuaca real-time"
        )

    # Hitung Fetch, Hs, dan Wave Current
    wind_speed = df_weather["wind_speed_10m"].values
    wind_dir = df_weather["wind_direction_10m"].values
    
    print("[INFO] Hitung fetch berdasarkan arah angin")
    fetch = calculate_fetch(wind_dir, pelabuhan)
    fetch_adj = adjust_fetch_for_barriers(fetch, wind_dir, pelabuhan)
    depth = calculate_depth(wind_dir, pelabuhan)
    slope = calculate_slope(pelabuhan)
    
    print("[INFO] Hitung tinggi gelombang signifikan (Hs)")
    hs = calculate_hs(wind_speed, fetch_adj, depth)
    
    print("[INFO] Hitung arus permukaan akibat angin (windwave)")
    wave_current = calculate_wave_current(hs, depth, slope)

    # Tambahkan Hs dan Wave Current ke DataFrame
    df_weather["Hs_m"] = hs
    df_weather["Wave_Current"] = wave_current

    # Ambil data saat ini (jam terdekat)
    data = df_weather.iloc[0].to_dict()
    data["timestamp"] = df_weather.index[0].tz_localize("Asia/Jakarta")
    suhu = data.get("temperature_2m", 0)
    kelembaban = data.get("relative_humidity_2m", 0)

    # Klasifikasi peringatan
    peringatan_angin = angin_kencang_warning(data.get("wind_speed_10m", 0))
    peringatan_gelombang = gelombang_tinggi_warning(data.get("Hs_m", 0))
    peringatan_arus = arus_gelombang_warning(data.get("Wave_Current", 0))
    peringatan_umum = klasifikasi_umum(peringatan_angin, peringatan_gelombang, peringatan_arus)
    warning_level = get_warning_level(
        max([
            level_peringatan(peringatan_angin),
            level_peringatan(peringatan_gelombang),
            level_peringatan(peringatan_arus)
        ])
    )

    # Arah angin dominan
    dominant_deg = df_weather["wind_direction_10m"].mode().iloc[0] if "wind_direction_10m" in df_weather.columns else None
    arah_dominan_label = derajat_ke_arah(dominant_deg) if dominant_deg is not None else "Kesalahan Sensor!"

    # Prediksi untuk 3 jam ke depan
    print("[INFO] Periksa apakah ada peringatan kondisi ekstrem")
    
    prediksi = []
    for i, t in enumerate(times_needed):
        if i < len(df_weather):
            row = df_weather.iloc[i]
            prediksi.append({
                "waktu": t.strftime("%H:%M"),
                "hs": round(row.get("Hs_m", 0), 3),
                "wave_current": round(row.get("Wave_Current", 0), 3),
                "wind_speed": round(row.get("wind_speed_10m", 0), 3),
                "wind_dir": round(row.get("wind_direction_10m", 0), 1),
                "wind_dir_text": derajat_ke_arah(row.get("wind_direction_10m", 0)),
                "current_direction": round(calculate_current_direction(row.get("wind_direction_10m", 0))),
                "current_direction_text": derajat_ke_arah(calculate_current_direction(row.get("wind_direction_10m", 0)))
            })
        else:
            prediksi.append({
                "waktu": t.strftime("%H:%M"),
                "hs": 0.0,
                "wave_current": 0.0,
                "wind_speed": 0.0,
                "wind_dir": 0.0,
                "current_direction": 0.0,
                "wind_dir_text": "Kesalahan Sensor",
                "current_direction_text": "Kesalahan Sensor"
            })

    # Simpan ke cache
    cache_data = {
        "data": data,
        "suhu": suhu,
        "kelembaban": kelembaban,
        "peringatan_umum": peringatan_umum,
        "peringatan_angin": peringatan_angin,
        "peringatan_gelombang": peringatan_gelombang,
        "peringatan_arus": peringatan_arus,
        "arah_dominan_label": arah_dominan_label,
        "warning_level": warning_level,
        "prediksi": prediksi
    }
    realtime_cache[pelabuhan] = {
        "data": cache_data,
        "expires": now + timedelta(minutes=CACHE_EXPIRY_MINUTES)
    }
    print(f"[CACHE] Menyimpan hasil ke cache untuk {pelabuhan}")

    return render_template(
        "realtime.html",
        pelabuhan=pelabuhan,
        data=data,
        suhu=suhu,
        kelembaban=kelembaban,
        peringatan_umum=peringatan_umum,
        peringatan_angin=peringatan_angin,
        peringatan_gelombang=peringatan_gelombang,
        peringatan_arus=peringatan_arus,
        arah_dominan_label=arah_dominan_label,
        warning_level=warning_level,
        prediksi=prediksi
    )
    
# ---------- ENDPOINT REKOMENDASI NAVIGASI ----------
rute_arah_dict = generate_rute_arah_dict(rute_dict, harbor_coords)
wib = pytz.timezone("Asia/Jakarta")

# Himbauan Navigasi Data Real-Time
@main.route("/navigasi/<pelabuhan>")
def navigasi(pelabuhan):
    if pelabuhan not in harbor_coords:
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Pelabuhan tidak dikenal")

    df_raw, _ = fetch_realtime_weather(pelabuhan)
    if df_raw is None or df_raw.empty:
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Gagal mengambil data realtime")
    
    df = predict_realtime(df_raw, pelabuhan)
    if df is None or df.empty:
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Gagal mengambil data realtime")

    # Ambil waktu dari query param (WIB), default ke now dibulatkan ke jam
    time_str = request.args.get("datetime")
    if time_str:
        try:
            waktu_wib = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
            waktu_wib = pytz.timezone("Asia/Jakarta").localize(waktu_wib).replace(minute=0, second=0, microsecond=0)
        except:
            return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Format datetime tidak valid")
    else:
        waktu_wib = datetime.now(pytz.timezone("Asia/Jakarta")).replace(minute=0, second=0, microsecond=0)

    # Cocokkan dengan index dataframe
    try:
        row = df.loc[waktu_wib.replace(tzinfo=None)]
    except KeyError:
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Data untuk waktu tersebut tidak tersedia")

    data = row.to_dict()
    data["timestamp"] = waktu_wib
    data["timestamp_wib"] = data["timestamp"]

    try:
        arah_angin = float(data.get("wind_direction_10m"))
    except (TypeError, ValueError):
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Data arah angin tidak tersedia")

    data["angin_arah"] = round(arah_angin)

    rute_list = generate_rute_list(
        pelabuhan,
        arah_angin,
        rute_arah_dict,
        data.get("wind_speed_10m", 0),
        data.get("Hs", 0),
        data.get("Wave_Current", 0)
    )

    return render_template(
        "navigasi.html",
        pelabuhan=pelabuhan,
        data=data,
        arah_angin=round(arah_angin),
        arah_text=derajat_ke_arah(arah_angin),
        rute_list=rute_list,
        rute_arah=rute_arah_dict.get(pelabuhan, {})
    )

# Himbauan Navigasi Data Monitoring
@main.route("/navigasi_v2/<pelabuhan>")
def navigasi_v2(pelabuhan):
    if pelabuhan not in harbor_coords:
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Pelabuhan tidak dikenal")

    filename = f"{pelabuhan}_gelombang.csv"
    basedir = os.path.abspath(os.path.dirname(__file__))
    filepath = os.path.join(basedir, "..", "data", "output_gelombang", filename)

    if not os.path.exists(filepath):
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="File CSV tidak ditemukan")

    df = pd.read_csv(filepath, parse_dates=["time"])
    df.rename(columns={"time": "timestamp"}, inplace=True)
    
    # beri tahu pandas bahwa 'time' itu UTC:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["timestamp_wib"] = df["timestamp"].dt.tz_convert("Asia/Jakarta")
    
    if df.empty:
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Data monitoring kosong")

    # Ambil waktu dari query param (WIB)
    time_str = request.args.get("datetime")
    if time_str:
        try:
            waktu_wib = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
            waktu_wib = wib.localize(waktu_wib)
        except:
            return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Format datetime tidak valid")
    else:
        waktu_wib = datetime.now(wib)

    waktu_utc = waktu_wib.astimezone(pytz.utc)

    # Cari baris dengan timestamp UTC terdekat
    df["selisih"] = abs(df["timestamp"] - waktu_utc)
    row = df.loc[df["selisih"].idxmin()]
    
    data = row.to_dict()
    data["timestamp"] = row["timestamp_wib"]

    try:
        arah_angin = float(data.get("wind_direction_10m"))
    except (TypeError, ValueError):
        return render_template("navigasi.html", pelabuhan=pelabuhan, warning="Data arah angin tidak tersedia")

    data["angin_arah"] = round(arah_angin)

    rute_list = generate_rute_list(
        pelabuhan,
        arah_angin,
        rute_arah_dict,
        data.get("wind_speed_10m", 0),
        data.get("Hs_m", 0),
        data.get("Wave_Current", 0)            
    )

    return render_template(
        "navigasi.html",
        pelabuhan=pelabuhan,
        data=data,
        arah_angin=round(arah_angin),
        arah_text=derajat_ke_arah(arah_angin),
        rute_list=rute_list,
        rute_arah=rute_arah_dict.get(pelabuhan, {})
    )