import os
os.environ["MPLBACKEND"] = "Agg"

import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from geopy.distance import geodesic
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from windrose import WindroseAxes
from io import BytesIO
import base64
import math

# =========================== #
#  KLASIFIKASI AMBANG BAHAYA  #
# =========================== #

# Fungsi klasifikasi kecepatan angin (m/s)
# 1 m/s ≈ 1.94384 knot
def angin_kencang_warning(kecepatan_angin):
    if kecepatan_angin > 12.6:  # 24.5 knot
        # Waspada untuk kapal dengan Gross Tonnage lebih dari 500
        return "dalam kondisi BERBAHAYA UNTUK SEMUA KAPAL!"
    elif kecepatan_angin > 9.75:  # 18.95 knot
        # berbahaya untuk kapal dengan Gross Tonnage antara 300 - 500
        return "berbahaya untuk kapal dengan Gross Tonnage di bawah 300 GT"
    elif kecepatan_angin > 6.9:  # 13.41 knot
        # berbahaya untuk kapal dengan Gross Tonnage antara 150 - 300
        return "berbahaya untuk kapal dengan Gross Tonnage di bawah 150 GT"
    else:
        return "masih dalam rentang yang Aman"

# Fungsi klasifikasi tinggi gelombang (m)
def gelombang_tinggi_warning(wave_height):
    if wave_height > 0.38:
        # Waspada untuk kapal dengan Gross Tonnage lebih dari 500
        return "dalam kondisi BERBAHAYA UNTUK SEMUA KAPAL!"
    elif wave_height > 0.28:
        # berbahaya untuk kapal dengan Gross Tonnage antara 200 - 300
        return "berbahaya untuk kapal dengan Gross Tonnage di bawah 300 GT"
    elif wave_height > 0.17:
        return "berbahaya untuk kapal dengan Gross Tonnage di bawah 150 GT"
    else:
        return "masih dalam rentang yang Aman"

# Fungsi klasifikasi kecepatan arus gelombang (m/s)
def arus_gelombang_warning(wave_current):
    if wave_current > 0.51:
        # Waspada untuk kapal dengan Gross Tonnage lebih dari 500
        return "dalam kondisi BERBAHAYA UNTUK SEMUA KAPAL!"
    elif wave_current > 0.39:
        # berbahaya untuk kapal dengan Gross Tonnage antara 200 - 300
        return "berbahaya untuk kapal dengan Gross Tonnage di bawah 300 GT"
    elif wave_current > 0.27:
        return "berbahaya untuk kapal dengan Gross Tonnage di bawah 150 GT"
    else:
        return "masih dalam rentang yang Aman"

# Klasifikasi Umum
def level_peringatan(teks):
    """Mengembalikan level: 0 = Aman, 1 = Waspada, 2 = Bahaya, 3 = Sangat Berbahaya"""
    if "BERBAHAYA UNTUK SEMUA KAPAL!" in teks:
        return 3
    elif "Gross Tonnage di bawah 300 GT" in teks:
        return 2
    elif "Gross Tonnage di bawah 150 GT" in teks:
        return 1
    else:
        return 0

def klasifikasi_umum(peringatan_angin, peringatan_gelombang, peringatan_arus):
    semua = [peringatan_angin, peringatan_gelombang, peringatan_arus]
    level = [level_peringatan(p) for p in semua]

    if 3 in level:
        return "HENTIKAN AKTIVITAS! SELURUH KAPAL DILARANG BERLAYAR!"
    elif level.count(2) == 3:
        return "Hanya kapal dengan Gross Tonnage di atas 300 GT yang diizinkan berlayar!"
    elif level.count(1) == 3:
        return "Hanya kapal dengan Gross Tonnage di atas 150 GT yang diizinkan berlayar!"
    elif level.count(2) == 2 and level.count(0) == 1:
        return "Hanya kapal dengan Gross Tonnage di atas 150 GT yang diizinkan berlayar!"
    elif 1 in level or 2 in level:
        batas_gt = []
        for p in semua:
            if "Gross Tonnage di bawah" in p:
                try:
                    angka = int("".join(filter(str.isdigit, p.split("di bawah")[-1])))
                    batas_gt.append(angka)
                except:
                    continue
        if batas_gt:
            batas_terkecil = min(batas_gt)
            return f"Mohon tingkatkan kewaspadaan untuk kapal dengan Gross Tonnage di bawah {batas_terkecil} GT!"

    return "Kondisi aman. Silahkan berlayar dan hati-hati di perjalanan!"

# Konversi derajat numerik menjadi arah mata angin
def derajat_ke_arah(derajat):
    arah = ["Utara", "Timur Laut", "Timur", "Tenggara", 
            "Selatan", "Barat Daya", "Barat", "Barat Laut"]
    idx = int(((derajat + 22.5) % 360) // 45)
    return arah[idx]

# Plot Grafik
def plot_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded

# Grafik Time-Series untuk Tinggi Gelombang
def generate_wave_plot(month_data):
    if month_data.empty:
        return None  # Tidak ada data di bulan tersebut

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(
        month_data["timestamp"],
        month_data["Hs_m"],
        label="Tinggi Gelombang Signifikan",
        color="royalblue",
        linewidth=1.5,
        marker="o",
        markersize=3
    )

    ax.set_ylabel("Hs (m)", fontsize=12)
    ax.set_xlabel("Tanggal", fontsize=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.set_xlim(month_data["timestamp"].min(), month_data["timestamp"].max())
    ax.set_ylim(0, month_data["Hs_m"].max() + 0.5)

    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    return plot_to_base64(fig)

# Grafik Time-Series untuk Kecepatan Arus
def generate_wave_current_plot(month_data):
    if month_data.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(
        month_data["timestamp"],
        month_data["Wave_Current"],
        label="Kecepatan Arus Gelombang",
        color="seagreen",
        linewidth=1.5,
        marker="o",
        markersize=3
    )

    ax.set_ylabel("Wave Current (m/s)", fontsize=12)
    ax.set_xlabel("Tanggal", fontsize=12)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    ax.set_xlim(month_data["timestamp"].min(), month_data["timestamp"].max())
    ax.set_ylim(0, month_data["Wave_Current"].max() + 0.1)

    plt.xticks(rotation=45)
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    return plot_to_base64(fig)

# Windrose - Distribusi Kecepatan dan Arah Angin
def generate_windrose(df):
    fig = plt.figure(figsize=(6, 6))
    ax = WindroseAxes.from_ax(fig=fig)
    
    ax.bar(
        df["wind_direction_10m"],
        df["wind_speed_10m"],
        normed=True,
        opening=0.8,
        edgecolor="white"
    )
    
    ax.set_legend(title="Kecepatan (m/s)", fontsize=8, title_fontsize=9, loc="lower right")
    return plot_to_base64(fig)

# =========================== #
#  Fungsi Prediksi Real-Time  #
# =========================== #

# --- Muat data fetch dan kontur slope ---
base_dir = os.path.dirname(os.path.abspath(__file__))
support_dir = os.path.join(base_dir, "..", "data", "support")

fetch_depth = pd.read_csv(os.path.join(support_dir, "Fetch_Depth_DanauTobaPort.csv"))
contour_slope = pd.read_csv(os.path.join(support_dir, "Contour_Slope_DanauTobaPort.csv"))

# --- Koordinat Pelabuhan ---
harbor_coords = {
    "Ajibata": [2.65917, 98.93444],
    "Ambarita": [2.68167, 98.83194],
    "Balige": [2.33722, 99.06278],
    "Simanindo": [2.75361, 98.74528],
    "Sipinggan": [2.43472, 98.89806],
    "Muara": [2.33583, 98.90694],
    "Tigaras": [2.79778, 98.78889],

    "Tomok": [2.65210, 98.86080],  # Perkiraan berdasarkan lokasi di Pulau Samosir
    "Onan Runggu": [2.4620, 98.9660],  # Perkiraan dari Desa Pakpahan
    "Nainggolan": [2.4135, 98.6213]  # Perkiraan dari Kecamatan Nainggolan
}

# --- Fungsi hitung fetch dari arah angin ---
def calculate_fetch(wind_dir, harbor_name):
    angles = fetch_depth['Arah (°)'].values
    values = fetch_depth[f'fetch_{harbor_name}'].values
    f = interp1d(angles, values, kind='linear', fill_value='extrapolate')
    return np.maximum(f(wind_dir), 0)

# --- Fungsi hitung depth dari arah angin ---
def calculate_depth(wind_dir, harbor_name):
    angles = fetch_depth['Arah (°)'].values
    values = fetch_depth[f'depth_{harbor_name}'].values
    f = interp1d(angles, values, kind='linear', fill_value='extrapolate')
    return np.maximum(f(wind_dir), 0.1)

# --- Fungsi hitung slope dari kontur terdekat ---
def calculate_slope(harbor_name):
    lat, lon = harbor_coords[harbor_name]
    contour_slope['distance'] = contour_slope.apply(
        lambda row: geodesic((lat, lon), (row['latitude'], row['longitude'])).meters, axis=1
    )
    return contour_slope.nsmallest(10, 'distance')['slope_degree'].mean()

# --- Fungsi koreksi fetch jika ada penghalang ---
def adjust_fetch_for_barriers(fetch, wind_dir, harbor_name):
    barriers = {
        # Pulau Samosir di sisi tengah danau menghalangi arah 90°–270°
        "Ajibata":   [(90, 270, 0.7)],  
        "Ambarita":  [(90, 270, 0.7)],
        "Simanindo": [(90, 270, 0.7)],
        "Sipinggan": [(90, 270, 0.7)],

        # Pelabuhan di sisi timur (Balige & Muara) terpengaruh oleh Bukit Barisan
        # Terutama arah 0°–30° (utara) dan 180°–210° (selatan) yang terbendung
        "Balige": [(0, 30, 0.8), (180, 210, 0.8)],
        "Muara":  [(0, 30, 0.8), (180, 210, 0.8)],

        # Tigaras terpengaruh oleh Bukit Tele di barat daya (210°–240°)
        "Tigaras": [(210, 240, 0.8)]
    }
    fetch_adj = fetch.copy()
    for lower, upper, factor in barriers.get(harbor_name, []):
        mask = (wind_dir >= lower) & (wind_dir <= upper)
        fetch_adj[mask] *= factor # Kurangi fetch karena arah angin terhalang
    return fetch_adj

# --- Fungsi hitung Hs (gelombang signifikan) ---
def calculate_hs(U10, fetch, depth):
    g = 9.81
    fetch_km = fetch / 1000
    Tp = 0.286 * (U10 / g) * (g * fetch_km * 1000 / U10**2)**0.33
    L0 = (g * Tp**2) / (2 * np.pi)
    Hs_deep = 0.0016 * (U10**2 / g) * np.sqrt(g * fetch_km * 1000 / U10**2)

    mask_shallow = depth < L0 / 20
    Hs = Hs_deep.copy()
    Hs[mask_shallow] *= np.tanh(2 * np.pi * depth[mask_shallow] / L0[mask_shallow])
    return np.maximum(Hs, 0)

# --- Fungsi hitung arus gelombang ---
def calculate_wave_current(Hs, depth, slope):
    g = 9.81
    mask_shallow = depth < 10
    wave_current = np.zeros_like(Hs)
    wave_current[mask_shallow] = np.sqrt(g * Hs[mask_shallow] * np.deg2rad(slope))
    wave_current[~mask_shallow] = 0.2 * np.sqrt(g * Hs[~mask_shallow])
    return np.maximum(wave_current, 0)

# Tambahkan fungsi untuk menghitung arah arus berdasarkan prinsip Ekman
def calculate_current_direction(wind_dir_deg):
    """
    Hitung arah arus permukaan berdasarkan arah angin (derajat),
    dengan asumsi defleksi Ekman sekitar 45 derajat ke kanan (belahan bumi utara).
    """
    return (wind_dir_deg + 45) % 360

# --- Fungsi utama prediksi realtime ---
def predict_realtime(input_df, harbor_name):
    """
    Menerima dataframe dengan cuaca real-time (3 jam: 0, +1, +2),
    menghitung Hs dan Wave Current secara empirik.
    """
    # Hitung parameter topografi
    slope = calculate_slope(harbor_name)
    wind_dir = input_df["wind_direction_10m"].values
    wind_speed = input_df["wind_speed_10m"].values
    fetch = calculate_fetch(wind_dir, harbor_name)
    depth = calculate_depth(wind_dir, harbor_name)
    fetch_adj = adjust_fetch_for_barriers(fetch, wind_dir, harbor_name)

    # Hitung Hs dan Arus Gelombang
    hs = calculate_hs(wind_speed, fetch_adj, depth)
    wave_current = calculate_wave_current(hs, depth, slope)
    current_dir = calculate_current_direction(wind_dir)

    # Gabungkan hasil
    results = input_df.copy()
    results["Hs"] = np.round(hs, 3)
    results["Wave_Current"] = np.round(wave_current, 3)
    results["Current_Direction"] = np.round(current_dir, 1)  # hasil dalam derajat

    # Tambahkan kolom arah angin dan arah arus dalam teks
    results["wind_dir_text"] = results["wind_direction_10m"].apply(derajat_ke_arah)
    results["current_dir_text"] = results["Current_Direction"].apply(derajat_ke_arah)

    return results

# === Daftar Rute Ferry Publik ===
rute_list = [
    ["Ajibata", "Ambarita"],
    ["Ajibata", "Tomok"],
    ["Balige", "Onan Runggu"],
    ["Balige", "Nainggolan"],
    ["Simanindo", "Tigaras"],
    ["Sipinggan", "Muara"]
]

rute_dict = {}

for asal, tujuan in rute_list:
    rute_dict.setdefault(asal, []).append([asal, tujuan])
    rute_dict.setdefault(tujuan, []).append([tujuan, asal])

def generate_rute_list(pelabuhan_asal, arah_angin, rute_arah,
                       kecepatan_angin, wave_height, wave_current):
    """
    Bangun daftar rute dari pelabuhan_asal ke tujuan-tujuan lain berdasarkan arah angin,
    arus, dan intensitas cuaca laut.
    """

    arah_arus = calculate_current_direction(arah_angin)

    rute_list = []
    tujuan_dict = rute_arah.get(pelabuhan_asal, {})

    for tujuan, arah in tujuan_dict.items():
        selisih_angin = abs((arah - arah_angin + 180) % 360 - 180)
        selisih_arus = abs((arah - arah_arus + 180) % 360 - 180)

        if selisih_angin <= 60 or selisih_arus <= 60:
            if kecepatan_angin >= 15 or wave_height >= 1.5 or wave_current >= 1.0:
                status = "Awas"
            else:
                status = "Waspada"
        elif selisih_angin <= 100 or selisih_arus <= 100:
            if kecepatan_angin >= 20 or wave_height >= 2.0:
                status = "Waspada"
            else:
                status = "Aman"
        else:
            status = "Aman"

        rute = {
            "tujuan": tujuan,
            "arah_rute": arah,
            "status": status
        }

        if status != "Aman":
            rute["arah_bahaya"] = derajat_ke_arah(arah)
            alternatif = [
                t for t, a in tujuan_dict.items()
                if abs((a - arah_angin + 180) % 360 - 180) > 100
                and abs((a - arah_arus + 180) % 360 - 180) > 100
            ]
            if alternatif:
                rute["arah_aman"] = ", ".join([
                    derajat_ke_arah(tujuan_dict[a]) for a in alternatif
                ])
            else:
                rute["arah_aman"] = "Tidak ada"

        rute_list.append(rute)

    return rute_list

def calculate_bearing(lat1, lon1, lat2, lon2):
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - \
        math.sin(lat1) * math.cos(lat2) * math.cos(dlon)

    bearing = math.atan2(x, y)
    bearing = math.degrees(bearing)
    return (bearing + 360) % 360

def generate_rute_arah_dict(rute_dict, harbor_coords):
    rute_arah_dict = {}

    for asal, rute_list in rute_dict.items():
        arah_dict = {}
        lat1, lon1 = harbor_coords.get(asal, (None, None))
        if lat1 is None:
            continue

        for rute in rute_list:
            _, tujuan = rute
            lat2, lon2 = harbor_coords.get(tujuan, (None, None))
            if lat2 is None:
                continue

            arah = calculate_bearing(lat1, lon1, lat2, lon2)
            arah_dict[tujuan] = round(arah)

        rute_arah_dict[asal] = arah_dict

    return rute_arah_dict