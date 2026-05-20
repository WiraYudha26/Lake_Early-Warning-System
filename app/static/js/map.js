/* ============================ */
/*   Javascript for Toba Lake   */
/* ============================ */

// Inisialisasi peta
document.addEventListener('DOMContentLoaded', function () {
    const map = L.map('map').setView([2.585, 98.860], 10);
    window.map = map;

    // Tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    const pelabuhan = [
        { name: "Ajibata", coords: [2.65917, 98.93444] },
        { name: "Balige", coords: [2.33722, 99.06278] },
        { name: "Simanindo", coords: [2.75361, 98.74528] },
        { name: "Tigaras", coords: [2.79778, 98.78889] },
        { name: "Muara", coords: [2.33583, 98.90694] },
        { name: "Ambarita", coords: [2.68167, 98.83194] },
        { name: "Sipinggan", coords: [2.43472, 98.89806] }
    ];

    window.selectedPort = '';

    // Tambah marker
    pelabuhan.forEach(port => {
        const marker = L.marker(port.coords).addTo(map).bindPopup(`<b>${port.name}</b>`);
        marker.on('mouseover', () => marker.openPopup());
        marker.on('mouseout', () => marker.closePopup());
    });

    // Fungsi saat lokasi dipilih dari dropdown
    window.moveToLocation = function () {
        const value = document.getElementById("locations").value;
        if (value) {
            const [lat, lon, name] = value.split(',');
            map.setView([parseFloat(lat), parseFloat(lon)], 13);
            selectedPort = name;

            const options = document.getElementById("monitoring-options");
            if (options) options.style.display = 'flex';
        }
    };

    // Real-time redirect
    window.redirectToRealtime = function (portName) {
        try {
            window.location.href = `/realtime/${portName}`;
        } catch (err) {
            console.error('Redirect failed:', err);
            showInlineWarning('Gagal mengarahkan ke halaman real-time.');
        }
    };

    // Pilih tanggal redirect
    window.redirectToDate = function (portName) {
        const datetimeInput = document.getElementById("datetime-input");

        if (!datetimeInput.checkValidity()) {
            datetimeInput.reportValidity();
            return;
        }

        const rawDate = new Date(datetimeInput.value);
        rawDate.setMinutes(0, 0, 0); // Pastikan HH:00

        const selectedYear = rawDate.getFullYear();
        if (selectedYear < 2020 || selectedYear > 2024) {
            showInlineWarning("Data Monitoring 'Pilih Tanggal' hanya tersedia untuk tahun 2020 hingga 2024.");
            return;
        }

        // Format lokal (bukan UTC)
        const localISO = rawDate.getFullYear()
        + '-' + String(rawDate.getMonth() + 1).padStart(2, '0')
        + '-' + String(rawDate.getDate()).padStart(2, '0')
        + 'T' + String(rawDate.getHours()).padStart(2, '0')
        + ':' + String(rawDate.getMinutes()).padStart(2, '0');

        try {
            const encoded = encodeURIComponent(localISO);
            window.location.href = `/monitoring?pelabuhan=${portName}&datetime=${encoded}`;
        } catch (err) {
            console.error('Redirect by date failed:', err);
            showInlineWarning('Gagal mengarahkan ke halaman berdasarkan tanggal.');
        }
    };

    // Tampilkan pesan warning di bawah input tanggal
    function showInlineWarning(message) {
        let warnBox = document.getElementById("date-warning");
        if (!warnBox) {
            warnBox = document.createElement("div");
            warnBox.id = "date-warning";
            warnBox.className = "alert alert-danger";
            warnBox.style.marginTop = "8px";
            warnBox.style.fontSize = "14px";
            warnBox.style.padding = "8px 12px";
            warnBox.style.borderRadius = "6px";
            warnBox.style.color = "#9d1f1f";
            warnBox.style.backgroundColor = "#fce3e3";
            warnBox.style.border = "1px solid #e47070";

            const container = document.querySelector(".date-selector");
            if (container) container.appendChild(warnBox);
        }

        warnBox.textContent = message;
        warnBox.style.display = "block";

        setTimeout(() => {
            warnBox.style.display = "none";
        }, 3000);
    }

    // Pastikan ukuran map diatur ulang
    setTimeout(() => {
        map.invalidateSize();
    }, 300);
});
