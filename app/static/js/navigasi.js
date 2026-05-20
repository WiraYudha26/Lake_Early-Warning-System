/* ============================ */
/*   Javascript for Navigasi    */
/* ============================ */
// Fungsi konversi derajat ke arah mata angin
function arahDariDerajat(degree) {
    const arahMataAngin = [
        "Utara", "Timur Laut", "Timur", "Tenggara",
        "Selatan", "Barat Daya", "Barat", "Barat Laut", "Utara"
    ];
    const index = Math.round(degree / 45) % 8;
    return arahMataAngin[index];
}

// Fungsi rekomendasi arah alternatif berdasarkan arah dilarang
function rekomendasiArah(dilarangDerajat) {
    const arahDilarang = arahDariDerajat(dilarangDerajat);
    const alternatif = [];
    for (let deg = 0; deg < 360; deg += 45) {
        const selisih = Math.abs(deg - dilarangDerajat);
        const deviasi = Math.min(selisih, 360 - selisih);  // koreksi arah searah jarum jam
        if (deviasi > 60) {
            alternatif.push(arahDariDerajat(deg));
        }
    }
    return { arahDilarang, alternatif };
}

// Fungsi utama untuk update tampilan rekomendasi
function tampilkanRekomendasi(windDirection) {
    const { arahDilarang, alternatif } = rekomendasiArah(windDirection);

    const box = document.getElementById("rekomendasi-box");
    box.innerHTML = `
        <p><strong>Arah Angin Saat Ini:</strong> ${windDirection}° (${arahDilarang})</p>
        <p><strong>Rute yang Sebaiknya Dihindari:</strong> Mengarah ke ${arahDilarang}</p>
        <p><strong>Alternatif Arah Aman:</strong> ${alternatif.join(", ")}</p>
    `;
}

// Eksekusi saat dokumen siap
document.addEventListener("DOMContentLoaded", () => {
    const winddirElement = document.getElementById("winddir-data");
    if (winddirElement) {
        const winddir = parseFloat(winddirElement.dataset.winddir);
        if (!isNaN(winddir)) {
            tampilkanRekomendasi(winddir);
        } else {
            console.error("Wind direction data invalid");
        }
    }
});