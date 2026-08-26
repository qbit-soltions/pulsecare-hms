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
      if (button) {
        const bedId = button.getAttribute("data-bed-id");
        const bedSelect = admitModal.querySelector("#modal-admit-bed-select");
        if (bedSelect && bedId) {
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
  // -------------------------------------------------------------------
  // 5. Teleconsultation Room & Call Timer
  // -------------------------------------------------------------------
  const timerElem = document.getElementById("callTimer");
  if (timerElem) {
    let seconds = 522;
    setInterval(function () {
      seconds++;
      const mins = Math.floor(seconds / 60);
      const secs = seconds % 60;
      timerElem.innerText = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }, 1000);
  }

  const addRxBtn = document.getElementById("addRxItemBtn");
  const rxContainer = document.getElementById("rxItemsContainer");
  if (addRxBtn && rxContainer) {
    addRxBtn.addEventListener("click", function () {
      const sampleRow = rxContainer.querySelector(".rx-item-row");
      if (sampleRow) {
        const newRow = sampleRow.cloneNode(true);
        newRow.querySelectorAll("input").forEach(i => i.value = "");
        rxContainer.appendChild(newRow);
      }
    });
  }
});

