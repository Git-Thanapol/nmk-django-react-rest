/**
 * Dashboard KPI — ApexCharts + data fetching
 * All data comes from JSON endpoints; no server-side rendering in the charts.
 */

const CURRENCY_FMT = new Intl.NumberFormat("th-TH", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

function fmt(n) {
  return CURRENCY_FMT.format(n);
}

// --------------------------------------------------------------------------
// Param helpers
// --------------------------------------------------------------------------

function getParams() {
  const company = document.getElementById("company-select")?.value || "";
  const period = document.getElementById("period-select")?.value || "this_month";
  const fromDate = document.getElementById("from-date")?.value || "";
  const toDate = document.getElementById("to-date")?.value || "";
  return { company, period, fromDate, toDate };
}

function buildQuery(extra = {}) {
  const { company, period, fromDate, toDate } = getParams();
  const p = new URLSearchParams();
  if (company) p.set("company", company);
  p.set("period", period);
  if (period === "custom") {
    if (fromDate) p.set("from", fromDate);
    if (toDate) p.set("to", toDate);
  }
  Object.entries(extra).forEach(([k, v]) => p.set(k, v));
  return p.toString();
}

async function fetchJSON(url) {
  const res = await fetch(url, { credentials: "same-origin" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// --------------------------------------------------------------------------
// KPI cards
// --------------------------------------------------------------------------

async function loadKPI() {
  try {
    const data = await fetchJSON(`/dashboard/api/kpi-summary/?${buildQuery()}`);
    document.getElementById("kpi-sales").textContent = fmt(data.total_sales);
    document.getElementById("kpi-purchases").textContent = fmt(data.total_purchases);
    document.getElementById("kpi-profit").textContent = fmt(data.gross_profit);
    document.getElementById("kpi-profit-pct").textContent = `${data.profit_pct}%`;
    document.getElementById("kpi-low-stock").textContent = data.low_stock_count;
  } catch (e) {
    console.error("KPI load error", e);
  }
}

// --------------------------------------------------------------------------
// Sales trend — line chart
// --------------------------------------------------------------------------

let salesChart = null;

async function loadSalesTrend() {
  const { company, period } = getParams();
  const days = period === "this_month" ? 30 : period === "last_month" ? 30 : 30;
  try {
    const data = await fetchJSON(
      `/dashboard/api/sales-trend/?${buildQuery({ days })}`
    );
    const dates = data.map((d) => d.date);
    const totals = data.map((d) => d.total);

    if (salesChart) {
      salesChart.updateSeries([{ name: "ยอดขาย", data: totals }]);
      salesChart.updateOptions({ xaxis: { categories: dates } });
      return;
    }

    salesChart = new ApexCharts(document.getElementById("chart-sales-trend"), {
      series: [{ name: "ยอดขาย (฿)", data: totals }],
      chart: { type: "area", height: 250, toolbar: { show: false }, zoom: { enabled: false } },
      stroke: { curve: "smooth", width: 2 },
      fill: { type: "gradient", gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.05 } },
      xaxis: { categories: dates, tickAmount: 6, labels: { rotate: 0, style: { fontSize: "10px" } } },
      yaxis: { labels: { formatter: (v) => fmt(v) } },
      tooltip: { y: { formatter: (v) => `฿${fmt(v)}` } },
      colors: ["#7c3aed"],
      grid: { borderColor: "#2d2d2d" },
      theme: { mode: "dark" },
    });
    salesChart.render();
  } catch (e) {
    console.error("Sales trend error", e);
  }
}

// --------------------------------------------------------------------------
// Top SKUs — horizontal bar
// --------------------------------------------------------------------------

let skuChart = null;

async function loadTopSKUs() {
  try {
    const data = await fetchJSON(`/dashboard/api/top-skus/?${buildQuery({ limit: 10 })}`);
    const labels = data.map((d) => `${d.sku}`);
    const values = data.map((d) => d.qty);

    if (skuChart) {
      skuChart.updateSeries([{ name: "จำนวนขาย", data: values }]);
      skuChart.updateOptions({ xaxis: { categories: labels } });
      return;
    }

    skuChart = new ApexCharts(document.getElementById("chart-top-skus"), {
      series: [{ name: "จำนวนขาย", data: values }],
      chart: { type: "bar", height: 280, toolbar: { show: false } },
      plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
      xaxis: { categories: labels },
      colors: ["#06b6d4"],
      grid: { borderColor: "#2d2d2d" },
      theme: { mode: "dark" },
      tooltip: { y: { formatter: (v) => `${v} ชิ้น` } },
    });
    skuChart.render();
  } catch (e) {
    console.error("Top SKUs error", e);
  }
}

// --------------------------------------------------------------------------
// Purchase vs Sales — grouped column
// --------------------------------------------------------------------------

let pvChart = null;

async function loadPurchaseVsSales() {
  try {
    const data = await fetchJSON(
      `/dashboard/api/purchase-vs-sales/?${buildQuery({ months: 6 })}`
    );
    const months = data.map((d) => d.month);
    const sales = data.map((d) => d.sales);
    const purchases = data.map((d) => d.purchases);

    if (pvChart) {
      pvChart.updateSeries([
        { name: "ยอดขาย", data: sales },
        { name: "ยอดซื้อ", data: purchases },
      ]);
      pvChart.updateOptions({ xaxis: { categories: months } });
      return;
    }

    pvChart = new ApexCharts(document.getElementById("chart-pv"), {
      series: [
        { name: "ยอดขาย", data: sales },
        { name: "ยอดซื้อ", data: purchases },
      ],
      chart: { type: "bar", height: 250, toolbar: { show: false } },
      plotOptions: { bar: { borderRadius: 3, columnWidth: "60%" } },
      xaxis: { categories: months },
      yaxis: { labels: { formatter: (v) => fmt(v) } },
      colors: ["#10b981", "#f59e0b"],
      grid: { borderColor: "#2d2d2d" },
      theme: { mode: "dark" },
      tooltip: { y: { formatter: (v) => `฿${fmt(v)}` } },
    });
    pvChart.render();
  } catch (e) {
    console.error("PvS error", e);
  }
}

// --------------------------------------------------------------------------
// Profit gauge — radial bar
// --------------------------------------------------------------------------

let gaugeChart = null;

function updateGauge(pct) {
  if (gaugeChart) {
    gaugeChart.updateSeries([Math.max(0, Math.min(100, pct))]);
    return;
  }
  gaugeChart = new ApexCharts(document.getElementById("chart-gauge"), {
    series: [Math.max(0, Math.min(100, pct))],
    chart: { type: "radialBar", height: 200, toolbar: { show: false } },
    plotOptions: {
      radialBar: {
        startAngle: -90,
        endAngle: 90,
        hollow: { size: "60%" },
        dataLabels: {
          name: { show: true, fontSize: "12px", offsetY: -5 },
          value: { fontSize: "22px", fontWeight: 700, offsetY: -40, formatter: (v) => `${v}%` },
        },
        track: { background: "#2d2d2d" },
      },
    },
    labels: ["กำไรขั้นต้น"],
    colors: ["#10b981"],
    theme: { mode: "dark" },
  });
  gaugeChart.render();
}

// --------------------------------------------------------------------------
// Stock alerts — table
// --------------------------------------------------------------------------

async function loadStockAlerts() {
  const tbody = document.getElementById("stock-alerts-body");
  if (!tbody) return;
  tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3"><span class="spinner-border spinner-border-sm me-2"></span>กำลังโหลด...</td></tr>';
  try {
    const data = await fetchJSON(`/dashboard/api/stock-alerts/?${buildQuery({ threshold: 5 })}`);
    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="text-center text-success py-3"><i class="bi bi-check-circle me-1"></i>ไม่มีสินค้าใกล้หมด</td></tr>';
      return;
    }
    tbody.innerHTML = data
      .map(
        (r) => `<tr>
        <td class="fw-mono">${r.sku}</td>
        <td>${r.name}</td>
        <td><span class="badge bg-danger">${r.remaining}</span></td>
        <td class="text-muted small">${r.po_number}</td>
      </tr>`
      )
      .join("");
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-3">ไม่สามารถโหลดข้อมูลได้</td></tr>';
    console.error("Stock alerts error", e);
  }
}

// --------------------------------------------------------------------------
// Bootstrap: load everything and wire filter controls
// --------------------------------------------------------------------------

async function loadAll() {
  document.getElementById("refresh-btn")?.classList.add("disabled");
  await Promise.all([
    loadKPI().then((d) => {
      // grab profit pct from the resolved value via re-read DOM
      const pct = parseFloat(document.getElementById("kpi-profit-pct")?.textContent) || 0;
      updateGauge(pct);
    }),
    loadSalesTrend(),
    loadTopSKUs(),
    loadPurchaseVsSales(),
    loadStockAlerts(),
  ]);
  document.getElementById("refresh-btn")?.classList.remove("disabled");
}

document.addEventListener("DOMContentLoaded", function () {
  loadAll();

  // period selector toggles custom date inputs
  const periodSel = document.getElementById("period-select");
  const customRange = document.getElementById("custom-range");
  if (periodSel && customRange) {
    periodSel.addEventListener("change", function () {
      customRange.style.display = this.value === "custom" ? "flex" : "none";
    });
  }

  // filter form apply button
  document.getElementById("apply-filters")?.addEventListener("click", function () {
    loadAll();
  });

  // refresh button
  document.getElementById("refresh-btn")?.addEventListener("click", function () {
    loadAll();
  });
});
