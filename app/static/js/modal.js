// =========================
//     Modal Controller
// =========================

// Daftar ID modal yang akan dikontrol
const modalIDs = ['modal1', 'modal2', 'modal3'];

// Fungsi untuk membuka modal berdasarkan ID
function openModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return; // jika modal tidak ditemukan, keluar
  modal.style.display = "flex";
  modal.classList.add("show");
}

// Fungsi untuk menutup modal berdasarkan ID
function closeModal(id) {
  const modal = document.getElementById(id);
  if (!modal) return;
  modal.style.display = "none";
  modal.classList.remove("show");
}

// Tutup modal jika tombol 'x' (close-button) diklik
document.addEventListener("DOMContentLoaded", function () {
  // Tunggu hingga seluruh elemen DOM siap
  document.querySelectorAll(".close-button").forEach(button => {
    button.addEventListener("click", function () {
      // Ambil elemen modal terdekat dari tombol yang diklik
      const modal = button.closest(".modal");
      if (modal && modal.id) {
        closeModal(modal.id);
      }
    });
  });
});

// Tutup modal jika pengguna menekan tombol ESC
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    modalIDs.forEach(id => {
      const modal = document.getElementById(id);
      if (modal && modal.style.display === "flex") {
        closeModal(id);
      }
    });
  }
});

// Tutup modal jika pengguna mengklik di luar isi modal
window.addEventListener("click", function (event) {
  modalIDs.forEach(id => {
    const modal = document.getElementById(id);
    if (event.target === modal) {
      closeModal(id);
    }
  });
});