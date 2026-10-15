// Admin Dashboard JavaScript
document.addEventListener("DOMContentLoaded", () => {
  // Mobile Sidebar Toggle
  const toggleBtn = document.getElementById("mobileToggle");
  const sidebar = document.getElementById("sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("open");
    });
  }

  // Auto-dismiss alert toast after 4s
  const toast = document.querySelector(".alert-toast");
  if (toast) {
    setTimeout(() => {
      toast.style.transition = "opacity 0.5s ease";
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 500);
    }, 4000);
  }

  // Event Delegation for Buttons
  document.addEventListener("click", (e) => {
    // 1. Open Detail Modal
    const detailBtn = e.target.closest(".btn-detail");
    if (detailBtn) {
      const resId = detailBtn.getAttribute("data-id");
      if (resId) openReservationDetail(resId);
      return;
    }

    // 2. Open Edit Wisata Modal
    const editWisataBtn = e.target.closest(".btn-edit-wisata");
    if (editWisataBtn) {
      const wisata = {
        id: editWisataBtn.getAttribute("data-id"),
        name: editWisataBtn.getAttribute("data-name"),
        category: editWisataBtn.getAttribute("data-category"),
        price: editWisataBtn.getAttribute("data-price"),
        description: editWisataBtn.getAttribute("data-description") || "",
        is_active: editWisataBtn.getAttribute("data-active")
      };
      openEditWisata(wisata);
      return;
    }

    // 3. Open Modal by data-modal
    const openModalBtn = e.target.closest("[data-open-modal]");
    if (openModalBtn) {
      const modalId = openModalBtn.getAttribute("data-open-modal");
      if (modalId) openModal(modalId);
      return;
    }

    // 4. Close Modal by data-close-modal
    const closeModalBtn = e.target.closest("[data-close-modal]");
    if (closeModalBtn) {
      const modalId = closeModalBtn.getAttribute("data-close-modal");
      if (modalId) closeModal(modalId);
      return;
    }

    // 5. Copy Button
    const copyBtn = e.target.closest(".btn-copy");
    if (copyBtn) {
      const text = copyBtn.getAttribute("data-copy");
      if (text) copyToClipboard(text, copyBtn);
      return;
    }
  });
});

// Modal helpers
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("show");
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("show");
}

// Copy to clipboard
function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = btn.innerHTML;
    btn.innerHTML = "✅ Tersalin!";
    setTimeout(() => {
      btn.innerHTML = originalText;
    }, 1500);
  });
}

// Populate and open Reservation Detail Modal
async function openReservationDetail(resId) {
  try {
    const res = await fetch(`/api/reservations/${resId}`);
    if (!res.ok) throw new Error("Gagal mengambil data reservasi");
    const data = await res.json();

    document.getElementById("modalBookingCode").innerText = data.booking_code;
    const copyBtn = document.getElementById("modalCopyBtn");
    if (copyBtn) copyBtn.setAttribute("data-copy", data.booking_code);

    document.getElementById("modalVisitDate").innerText = data.visit_date;
    document.getElementById("modalTicketName").innerText = data.ticket_name;
    document.getElementById("modalTicketCategory").innerText = data.ticket_category || "Wisata";
    document.getElementById("modalQty").innerText = data.ticket_qty + " Orang";
    const payAmount = data.payment_amount || data.total_price;
    document.getElementById("modalTotalPrice").innerText = "Rp " + Number(payAmount).toLocaleString("id-ID");
    
    document.getElementById("modalUserName").innerText = data.user_name;
    document.getElementById("modalUserPhone").innerText = data.user_phone;
    
    // WhatsApp link
    const cleanPhone = (data.user_phone || "").replace(/\D/g, "");
    const waPhone = cleanPhone.startsWith("0") ? "62" + cleanPhone.substring(1) : cleanPhone;
    const waBtn = document.getElementById("modalWhatsAppBtn");
    if (waBtn) {
      waBtn.href = `https://wa.me/${waPhone}?text=Halo%20${encodeURIComponent(data.user_name)},%20kami%20dari%20Wisata%20Ngrembel%20Asri%20Semarang%20mengenai%20reservasi%20${data.booking_code}`;
    }

    // Payment proof or Casaku info
    const proofContainer = document.getElementById("modalProofContainer");
    if (data.casaku_trx_id) {
      proofContainer.innerHTML = `
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; margin-top: 6px;">
          <div style="font-weight: 700; color: #166534; font-size: 13px;">⚡️ Transaksi QRIS Otomatis (Casaku)</div>
          <div style="font-size: 12px; color: #334155; margin-top: 4px;">ID Transaksi: <code style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-family: monospace;">${data.casaku_trx_id}</code></div>
          <div style="font-size: 12px; color: #334155; margin-top: 2px;">Metode: <b>${data.payment_method || 'QRIS Otomatis'}</b></div>
          <div style="font-size: 12px; color: #15803d; margin-top: 2px;">Total Tagihan: <b>Rp ${Number(payAmount).toLocaleString("id-ID")}</b> (termasuk kode unik)</div>
        </div>
      `;
    } else if (data.payment_proof) {
      proofContainer.innerHTML = `
        <div style="margin-top: 10px;">
          <a href="/static/uploads/${data.payment_proof}" target="_blank">
            <img src="/static/uploads/${data.payment_proof}" style="max-height: 200px; border-radius: 8px; border: 1px solid #cbd5e1; cursor: pointer; display: block;" title="Klik untuk memperbesar">
          </a>
          <span style="font-size: 11px; color: #64748b; margin-top: 4px; display: block;">*Klik gambar untuk membuka ukuran penuh</span>
        </div>
      `;
    } else {
      proofContainer.innerHTML = `<span style="font-size: 13px; color: #94a3b8; font-style: italic;">Belum ada bukti pembayaran diunggah.</span>`;
    }

    // Setup download ticket button
    const dlTicketBtn = document.getElementById("modalDownloadTicketBtn");
    if (dlTicketBtn) {
      dlTicketBtn.href = `/reservations/${data.id}/invoice`;
    }

    // Setup status update form
    const statusForm = document.getElementById("updateStatusForm");
    statusForm.action = `/reservations/status/${data.id}`;
    document.getElementById("modalStatusSelect").value = data.status;
    document.getElementById("modalAdminNotes").value = data.admin_notes || "";

    openModal("reservationDetailModal");
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Populate and open Edit Wisata Modal
function openEditWisata(wisata) {
  document.getElementById("editWisataForm").action = `/wisata/edit/${wisata.id}`;
  document.getElementById("editWisataName").value = wisata.name;
  document.getElementById("editWisataCategory").value = wisata.category;
  document.getElementById("editWisataPrice").value = wisata.price;
  document.getElementById("editWisataDesc").value = wisata.description || "";
  document.getElementById("editWisataActive").value = wisata.is_active;

  openModal("editWisataModal");
}
