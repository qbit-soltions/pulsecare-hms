/**
 * PulseCare Hospital Management System - Interactive Frontend Logic
 */

document.addEventListener("DOMContentLoaded", function () {
  // Initialize Tooltips if bootstrap is loaded
  if (typeof bootstrap !== "undefined") {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }

  // -------------------------------------------------------------------
  // 1. Live Table Search Filter
  // -------------------------------------------------------------------
  const liveSearchInputs = document.querySelectorAll(".table-live-search");
  liveSearchInputs.forEach(function (input) {
    input.addEventListener("input", function () {
      const targetTableId = input.getAttribute("data-target-table");
      const filter = input.value.toLowerCase();
      const rows = document.querySelectorAll(`#${targetTableId} tbody tr`);

      rows.forEach(function (row) {
        const text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? "" : "none";
      });
    });
  });

  // -------------------------------------------------------------------
  // 2. Prescription Builder (Doctor Clinical Consultation)
  // -------------------------------------------------------------------
  const addMedicineBtn = document.getElementById("btn-add-medicine-row");
  const medicineTableBody = document.getElementById("prescription-items-tbody");

  if (addMedicineBtn && medicineTableBody) {
    addMedicineBtn.addEventListener("click", function () {
      const sampleRow = medicineTableBody.querySelector("tr");
      if (!sampleRow) return;

      const newRow = sampleRow.cloneNode(true);
      // Reset inputs in new row
      newRow.querySelectorAll("input, select").forEach(function (elem) {
        if (elem.tagName === "SELECT") {
          elem.selectedIndex = 0;
        } else {
          elem.value = "";
          if (elem.name.includes("duration")) elem.value = "5";
          if (elem.name.includes("quantity")) elem.value = "10";
        }
      });

      // Bind remove button
      const removeBtn = newRow.querySelector(".btn-remove-row");
      if (removeBtn) {
        removeBtn.addEventListener("click", function () {
          if (medicineTableBody.querySelectorAll("tr").length > 1) {
            newRow.remove();
          } else {
            alert("At least one prescription line item is required.");
          }
        });
      }

      medicineTableBody.appendChild(newRow);
    });

    // Bind initial remove buttons
    document.querySelectorAll(".btn-remove-row").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        const row = e.target.closest("tr");
        if (medicineTableBody.querySelectorAll("tr").length > 1) {
          row.remove();
        }
      });
    });
  }

  // -------------------------------------------------------------------
  // 3. Dynamic Invoice Builder (Billing & Invoicing)
  // -------------------------------------------------------------------
  const addInvoiceItemBtn = document.getElementById("btn-add-invoice-row");
  const invoiceTableBody = document.getElementById("invoice-items-tbody");

  function calculateInvoiceTotals() {
    let subtotal = 0;
    document.querySelectorAll("#invoice-items-tbody tr").forEach(function (row) {
      const qtyInput = row.querySelector(".item-qty");
      const priceInput = row.querySelector(".item-price");
      const totalInput = row.querySelector(".item-total");

      const qty = parseFloat(qtyInput ? qtyInput.value : 1) || 0;
      const price = parseFloat(priceInput ? priceInput.value : 0) || 0;
      const lineTotal = qty * price;

      if (totalInput) totalInput.value = lineTotal.toFixed(2);
      subtotal += lineTotal;
    });

    const taxPercentInput = document.getElementById("invoice-tax-percent");
    const discountInput = document.getElementById("invoice-discount");
    const amountPaidInput = document.getElementById("invoice-amount-paid");

    const taxPercent = parseFloat(taxPercentInput ? taxPercentInput.value : 5) || 0;
    const discount = parseFloat(discountInput ? discountInput.value : 0) || 0;
    const taxAmount = (subtotal * (taxPercent / 100));
    const grandTotal = Math.max(0, subtotal + taxAmount - discount);

    if (document.getElementById("calc-subtotal")) {
      document.getElementById("calc-subtotal").innerText = "$" + subtotal.toFixed(2);
    }
    if (document.getElementById("calc-tax")) {
      document.getElementById("calc-tax").innerText = "$" + taxAmount.toFixed(2);
    }
    if (document.getElementById("calc-grand-total")) {
      document.getElementById("calc-grand-total").innerText = "$" + grandTotal.toFixed(2);
    }
  }

  if (addInvoiceItemBtn && invoiceTableBody) {
    addInvoiceItemBtn.addEventListener("click", function () {
      const sampleRow = invoiceTableBody.querySelector("tr");
      if (!sampleRow) return;

      const newRow = sampleRow.cloneNode(true);
      newRow.querySelectorAll("input, select").forEach(function (elem) {
        if (elem.classList.contains("item-qty")) elem.value = "1";
        else if (elem.classList.contains("item-price")) elem.value = "0.00";
        else if (elem.classList.contains("item-total")) elem.value = "0.00";
        else elem.value = "";
      });

      invoiceTableBody.appendChild(newRow);
      bindInvoiceRowEvents(newRow);
      calculateInvoiceTotals();
    });

    function bindInvoiceRowEvents(row) {
      row.querySelectorAll(".item-qty, .item-price").forEach(function (input) {
        input.addEventListener("input", calculateInvoiceTotals);
      });
      const removeBtn = row.querySelector(".btn-remove-invoice-row");
      if (removeBtn) {
        removeBtn.addEventListener("click", function () {
          if (invoiceTableBody.querySelectorAll("tr").length > 1) {
            row.remove();
            calculateInvoiceTotals();
          }
        });
      }
    }

    document.querySelectorAll("#invoice-items-tbody tr").forEach(bindInvoiceRowEvents);

    const taxInput = document.getElementById("invoice-tax-percent");
    const discInput = document.getElementById("invoice-discount");
    if (taxInput) taxInput.addEventListener("input", calculateInvoiceTotals);
    if (discInput) discInput.addEventListener("input", calculateInvoiceTotals);
  }

  // -------------------------------------------------------------------
  // 4. Modal Triggers & Prefill Data Helpers
  // -------------------------------------------------------------------
  // Admit modal prefill bed ID
  const admitModal = document.getElementById("admitPatientModal");
  if (admitModal) {
    admitModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      const bedSelect = admitModal.querySelector("#modal-admit-bed-select");
      if (button && bedSelect) {
        const bedId = button.getAttribute("data-bed-id");
        if (bedId) {
          bedSelect.value = bedId;
        }
      }
    });
  }

  // Discharge modal prefill admission ID
  const dischargeModal = document.getElementById("dischargePatientModal");
  if (dischargeModal) {
    dischargeModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      if (button) {
        const admId = button.getAttribute("data-admission-id");
        const patientName = button.getAttribute("data-patient-name");
        const bedNumber = button.getAttribute("data-bed-number");

        const form = dischargeModal.querySelector("form");
        if (form && admId) {
          form.action = `/wards/discharge/${admId}`;
        }
        const patientLabel = dischargeModal.querySelector("#discharge-patient-name");
        if (patientLabel && patientName) {
          patientLabel.innerText = `${patientName} (Bed: ${bedNumber || 'N/A'})`;
        }
      }
    });
  }

  // -------------------------------------------------------------------
  // 5. Mobile Sidebar Drawer & Backdrop Toggle
  // -------------------------------------------------------------------
  const sidebar = document.getElementById("sidebar");
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");

  function openSidebar() {
    if (sidebar) sidebar.classList.add("sidebar-open");
    if (sidebarBackdrop) sidebarBackdrop.classList.add("show");
    document.body.classList.add("sidebar-active");
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove("sidebar-open");
    if (sidebarBackdrop) sidebarBackdrop.classList.remove("show");
    document.body.classList.remove("sidebar-active");
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      if (sidebar && sidebar.classList.contains("sidebar-open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });
  }

  if (sidebarCloseBtn) {
    sidebarCloseBtn.addEventListener("click", closeSidebar);
  }

  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", closeSidebar);
  }

  // Close sidebar when clicking any navigation link on mobile
  if (sidebar) {
    sidebar.querySelectorAll(".nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth < 992) {
          closeSidebar();
        }
      });
    });
  }

  // Close sidebar on Escape key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && sidebar && sidebar.classList.contains("sidebar-open")) {
      closeSidebar();
    }
  });

  // Auto-close mobile drawer on window resize to desktop
  window.addEventListener("resize", function () {
    if (window.innerWidth >= 992 && sidebar && sidebar.classList.contains("sidebar-open")) {
      closeSidebar();
    }
  });
});

