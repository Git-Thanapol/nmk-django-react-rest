/**
 * Global Search — Ctrl+K modal
 * Searches Products, Vendors, Invoices, Purchases, Companies via /api/search/
 */

(function () {
  "use strict";

  const ICONS = {
    products: "bi-phone",
    vendors: "bi-person-lines-fill",
    invoices: "bi-receipt",
    purchases: "bi-cart",
    companies: "bi-building",
  };
  const LABELS = {
    products: "สินค้า",
    vendors: "ผู้ขาย/ผู้ซื้อ",
    invoices: "ใบขาย",
    purchases: "ใบซื้อ",
    companies: "บริษัท",
  };

  let debounceTimer = null;
  let highlighted = -1;
  let flatResults = []; // flat list of {url} for keyboard nav

  // ── DOM refs (created once DOMContentLoaded fires) ──────────────────────
  let modal, input, resultsEl, spinner;

  function openModal() {
    modal.show();
    setTimeout(() => input.focus(), 150);
  }

  function closeModal() {
    modal.hide();
    input.value = "";
    resultsEl.innerHTML = "";
    flatResults = [];
    highlighted = -1;
  }

  // ── Render ───────────────────────────────────────────────────────────────

  function renderResults(data) {
    resultsEl.innerHTML = "";
    flatResults = [];
    highlighted = -1;

    const categories = Object.keys(ICONS);
    let hasAny = false;

    categories.forEach((cat) => {
      const items = data[cat];
      if (!items || !items.length) return;
      hasAny = true;

      const header = document.createElement("div");
      header.className = "search-category-header px-3 py-1 text-muted small fw-semibold";
      header.textContent = LABELS[cat];
      resultsEl.appendChild(header);

      items.forEach((item) => {
        const idx = flatResults.length;
        flatResults.push(item.url);

        const el = document.createElement("a");
        el.href = item.url;
        el.className = "search-result-item d-flex align-items-center gap-2 px-3 py-2 text-decoration-none";
        el.dataset.idx = idx;
        el.innerHTML = `<i class="bi ${ICONS[cat]} text-muted"></i><span>${escHtml(item.label)}</span>`;

        el.addEventListener("mouseenter", () => setHighlight(idx));
        el.addEventListener("mouseleave", () => clearHighlight(idx));
        el.addEventListener("click", closeModal);

        resultsEl.appendChild(el);
      });
    });

    if (!hasAny) {
      resultsEl.innerHTML =
        '<div class="text-center text-muted py-4 small">ไม่พบผลลัพธ์</div>';
    }
  }

  function setHighlight(idx) {
    clearHighlight(highlighted);
    highlighted = idx;
    const el = resultsEl.querySelector(`[data-idx="${idx}"]`);
    if (el) el.classList.add("active");
  }

  function clearHighlight(idx) {
    const el = resultsEl.querySelector(`[data-idx="${idx}"]`);
    if (el) el.classList.remove("active");
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── Fetch ────────────────────────────────────────────────────────────────

  async function doSearch(q) {
    if (q.trim().length < 2) {
      resultsEl.innerHTML = "";
      flatResults = [];
      return;
    }
    spinner.classList.remove("d-none");
    try {
      const res = await fetch(
        `/api/search/?q=${encodeURIComponent(q)}`,
        { credentials: "same-origin" }
      );
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      renderResults(data);
    } catch (e) {
      resultsEl.innerHTML =
        '<div class="text-center text-danger py-3 small">เกิดข้อผิดพลาด ลองใหม่อีกครั้ง</div>';
    } finally {
      spinner.classList.add("d-none");
    }
  }

  // ── Keyboard navigation ──────────────────────────────────────────────────

  function handleInputKey(e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(highlighted + 1, flatResults.length - 1);
      setHighlight(next);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(highlighted - 1, 0);
      setHighlight(prev);
    } else if (e.key === "Enter" && highlighted >= 0) {
      e.preventDefault();
      window.location.href = flatResults[highlighted];
      closeModal();
    } else if (e.key === "Escape") {
      closeModal();
    }
  }

  // ── Init ─────────────────────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", function () {
    const modalEl = document.getElementById("global-search-modal");
    if (!modalEl) return;

    modal = new bootstrap.Modal(modalEl, { backdrop: true, keyboard: true });
    input = document.getElementById("global-search-input");
    resultsEl = document.getElementById("global-search-results");
    spinner = document.getElementById("global-search-spinner");

    // Input: debounced search
    input.addEventListener("input", function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => doSearch(this.value), 200);
    });

    input.addEventListener("keydown", handleInputKey);

    // Clean up on modal hidden
    modalEl.addEventListener("hidden.bs.modal", function () {
      input.value = "";
      resultsEl.innerHTML = "";
      flatResults = [];
      highlighted = -1;
    });

    // Trigger: Ctrl+K / Cmd+K globally
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        openModal();
      }
    });

    // Trigger: search icon button in topbar
    document.getElementById("global-search-btn")?.addEventListener("click", openModal);
  });
})();
