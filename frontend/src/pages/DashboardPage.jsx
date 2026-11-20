import { useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import { PageHeading } from "../components/UI.jsx";
import { businessApi } from "../services/businessApi.js";
import { customerApi } from "../services/customerApi.js";
import {
  BusinessProfilePage,
  CustomerPage,
  ExpensesPage as ExpenseManagementPage,
  InventoryPage,
  ProductPage,
  ReportsPage as BusinessReportsPage,
} from "./BusinessPages.jsx";
import AssistantPage from "./AssistantPage.jsx";

const money = (value) =>
  new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 2,
  }).format(Number(value || 0));

const parseDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-NG", { dateStyle: "medium" }).format(date);
};

const escapeHtml = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);

function decimalToScaled(value, precision) {
  const text = String(value ?? "0").trim();
  if (!/^\d+(?:\.\d*)?$/.test(text)) return 0n;
  const [whole, fraction = ""] = text.split(".");
  const scale = 10n ** BigInt(precision);
  const fractional = BigInt((fraction + "0".repeat(precision)).slice(0, precision) || "0");
  return BigInt(whole) * scale + fractional;
}

function lineTotalCents(price, quantity) {
  const product = decimalToScaled(price, 2) * decimalToScaled(quantity, 3);
  let rounded = product / 1000n;
  const remainder = product % 1000n;
  if (remainder > 500n || (remainder === 500n && rounded % 2n === 1n)) rounded += 1n;
  return rounded;
}

function formatMinorUnits(amount) {
  const cents = BigInt(amount);
  const whole = cents / 100n;
  const fraction = String(cents % 100n).padStart(2, "0");
  const sign = cents < 0n ? -1n : 1n;
  const wholeFormatter = new Intl.NumberFormat("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  const decimalSeparator = new Intl.NumberFormat("en-NG", { minimumFractionDigits: 1 })
    .formatToParts(1.1)
    .find((part) => part.type === "decimal")?.value || ".";
  return `${wholeFormatter.format(whole * sign)}${decimalSeparator}${fraction}`;
}

function TrendChart({ points = [] }) {
  const chartHeight = 170;
  const chartWidth = 600;
  const maximum = Math.max(
    1,
    ...points.flatMap((point) => [Number(point.sales || 0), Number(point.expenses || 0)]),
  );
  const coordinates = (key) => points.map((point, index) => {
    const x = points.length < 2 ? chartWidth / 2 : (index / (points.length - 1)) * chartWidth;
    const y = chartHeight - (Number(point[key] || 0) / maximum) * (chartHeight - 12) - 6;
    return `${x},${y}`;
  }).join(" ");
  const ticks = points.filter((_, index) => (
    index === 0 || index === points.length - 1 || index % Math.ceil(points.length / 5) === 0
  ));

  return (
    <div className="business-trend">
      {points.length ? <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Actual net sales and expenses over the selected period">
        {[0, 1, 2, 3].map((line) => <line key={line} x1="0" x2={chartWidth} y1={line * (chartHeight / 3)} y2={line * (chartHeight / 3)} className="business-trend__grid" />)}
        <polyline points={coordinates("sales")} className="business-trend__sales" />
        <polyline points={coordinates("expenses")} className="business-trend__expenses" />
      </svg> : <div className="empty-state">No financial activity in this period.</div>}
      <div className="business-trend__labels">
        {ticks.map((point) => <span key={point.date}>{new Intl.DateTimeFormat("en-NG", { month: "short", day: "numeric" }).format(new Date(`${point.date}T00:00:00`))}</span>)}
      </div>
      <div className="business-trend__legend"><span><i />Net sales</span><span><i />Expenses</span></div>
    </div>
  );
}

function MetricCard({ title, value, hint, icon, variant = "blue" }) {
  return (
    <article className="metric-card">
      <div className="metric-card__top">
        <span>{title}</span>
        <span className={`metric-icon metric-icon--${variant}`}><Icon name={icon} size={19} /></span>
      </div>
      <strong>{value}</strong>
      <div className="metric-card__bottom">
        <span>{hint}</span>
      </div>
    </article>
  );
}

function OverviewPage({ data, loading, error, range, onRangeChange }) {
  const analytics = data || {};
  return (
    <>
      <PageHeading
        eyebrow="REAL BUSINESS DATA"
        title="Overview"
        description="Performance metrics from the active business workspace."
        action={<label className="select-wrap"><span>Period</span><select value={range} onChange={(event) => onRangeChange(event.target.value)}><option value="today">Today</option><option value="this_week">This week</option><option value="this_month">This month</option><option value="this_year">This year</option></select></label>}
      />
      {error && <p className="form-feedback form-feedback--error" role="alert">{error}</p>}
      {loading && <p className="empty-state" role="status">Loading business performance…</p>}
      <div className="metric-grid">
        <MetricCard title="Total sales" value={money(analytics.total_sales || 0)} hint="Gross revenue" icon="wallet" variant="blue" />
        <MetricCard title="Net sales" value={money(analytics.net_sales || 0)} hint={`${money(analytics.refund_total || 0)} refunded`} icon="activity" variant="green" />
        <MetricCard title="Total expenses" value={money(analytics.operating_expenses || 0)} hint="Business costs" icon="receipt" variant="orange" />
        <MetricCard title="Gross profit" value={money(analytics.gross_profit || 0)} hint="After COGS" icon="trend" variant="green" />
        <MetricCard title="Net profit" value={money(analytics.net_profit || 0)} hint="After expenses" icon="users" variant="purple" />
        <MetricCard title="Receivables" value={money(analytics.outstanding_receivables || 0)} hint={`${analytics.sales_count || 0} sales in range`} icon="receipt" variant="orange" />
        <MetricCard title="Customers" value={analytics.customer_count || 0} hint="In this workspace" icon="users" variant="purple" />
        <MetricCard title="Products in stock" value={analytics.products_in_stock || 0} hint={`${analytics.out_of_stock_count || 0} out of stock`} icon="package" variant="blue" />
        <MetricCard title="Inventory units" value={analytics.inventory_units || "0"} hint="Current available quantity" icon="cube" variant="green" />
      </div>
      <section className="panel business-trend-panel">
        <div className="panel-title"><div><h2>Sales and expenses</h2><p>Net sales and recorded expenses in the selected period.</p></div></div>
        <TrendChart points={analytics.trend || []} />
      </section>
      <div className="overview-bottom">
        <section className="panel">
          <div className="panel-title">
            <div><h2>Recent transactions</h2></div>
          </div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>REFERENCE</th><th>CUSTOMER</th><th>DATE</th><th>AMOUNT</th><th>STATUS</th></tr></thead>
              <tbody>
                {(analytics.recent_transactions || []).map((sale) => (
                  <tr key={sale.id}>
                    <td>{sale.id}</td>
                    <td>{sale.name}</td>
                    <td>{parseDate(sale.date)}</td>
                    <td>{money(sale.amount)}</td>
                    <td>{sale.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <div className="panel-title"><div><h2>Recent expenses</h2></div></div>
          <div className="table-scroll"><table><thead><tr><th>DESCRIPTION</th><th>CATEGORY</th><th>DATE</th><th>AMOUNT</th></tr></thead>
            <tbody>{(analytics.recent_expenses || []).map((expense) => <tr key={expense.id}><td>{expense.description}</td><td>{expense.category}</td><td>{parseDate(expense.date)}</td><td>{money(expense.amount)}</td></tr>)}</tbody>
          </table></div>
          {!analytics.recent_expenses?.length && <div className="empty-state">No expenses have been recorded in this period.</div>}
        </section>
        <section className="panel">
          <div className="panel-title">
            <div><h2>Best-selling products</h2></div>
          </div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>PRODUCT</th><th>UNITS SOLD</th></tr></thead>
              <tbody>
                {(analytics.best_selling_products || []).map((item) => (
                  <tr key={item.name}><td>{item.name}</td><td>{item.units_sold}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <div className="panel-title"><div><h2>Low-stock and out-of-stock</h2></div></div>
          <div className="table-scroll">
            <table><thead><tr><th>PRODUCT</th><th>IN STOCK</th><th>REORDER</th></tr></thead>
              <tbody>{(analytics.low_stock_products || []).map((item) => <tr key={item.name}><td>{item.name}</td><td>{item.quantity_on_hand}</td><td>{item.reorder_level}</td></tr>)}</tbody>
            </table>
          </div>
          {!analytics.low_stock_products?.length && <div className="empty-state">No stock is currently at or below reorder level.</div>}
        </section>
      </div>
      <section className="panel">
        <div className="panel-title"><div><h2>Recent business activity</h2><p>Latest sales and expenses in the selected period.</p></div></div>
        <div className="activity-feed">
          {(analytics.recent_activity || []).map((activity) => (
            <div className="activity-feed__item" key={activity.id}>
              <span className={`activity-feed__icon activity-feed__icon--${activity.type}`}><Icon name={activity.type === "expense" ? "receipt" : "activity"} size={16} /></span>
              <div><b>{activity.title}</b><small>{activity.detail} · {parseDate(activity.date)}</small></div>
              <strong>{money(activity.amount)}</strong>
            </div>
          ))}
          {!analytics.recent_activity?.length && <div className="empty-state">Activity will appear after sales or expenses are recorded.</div>}
        </div>
      </section>
    </>
  );
}

function SalesPage({
  data, loading, error, businessId, businessRole, range, onRangeChange, refresh,
  query, onQueryChange, status, onStatusChange, page, onPageChange, startDate, endDate, onStartDateChange, onEndDateChange,
}) {
  const scopedData = data?.business_id === businessId ? data : null;
  const rows = scopedData?.sales || [];
  const pagination = scopedData?.pagination || {};
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [productSearch, setProductSearch] = useState("");
  const [customerSearch, setCustomerSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [items, setItems] = useState([{ product_id: "", quantity: "1", unit_price: "" }]);
  const [initialPayment, setInitialPayment] = useState("");
  const [initialPaymentMethod, setInitialPaymentMethod] = useState("cash");
  const [selectedSale, setSelectedSale] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState("");
  const [refundAmount, setRefundAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [cancelReason, setCancelReason] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [editSaleDate, setEditSaleDate] = useState("");
  const [editSaving, setEditSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionNotice, setActionNotice] = useState("");
  const [actionSaving, setActionSaving] = useState(false);

  useEffect(() => {
    setProducts([]);
    setCustomers([]);
    setSelectedCustomer("");
    setItems([{ product_id: "", quantity: "1", unit_price: "" }]);
    setSelectedSale(null);
    setProductSearch("");
    setCustomerSearch("");
    setInitialPayment("");
    setPaymentAmount("");
    setRefundAmount("");
    setActionError("");
    setActionNotice("");
  }, [businessId]);

  useEffect(() => {
    if (!businessId) return;
    let active = true;
    businessApi.getProducts(businessId, { page: 1, per_page: 50, q: productSearch })
      .then((payload) => { if (active) setProducts(payload.products || []); })
      .catch((failure) => { if (active) setFormError(failure.message || "Products could not be loaded."); });
    return () => { active = false; };
  }, [businessId, productSearch]);

  useEffect(() => {
    if (!businessId) return;
    let active = true;
    customerApi.list(businessId, { page: 1, perPage: 50, query: customerSearch })
      .then((payload) => { if (active) setCustomers(payload.customers || []); })
      .catch((failure) => { if (active) setFormError(failure.message || "Customers could not be loaded."); });
    return () => { active = false; };
  }, [businessId, customerSearch]);

  const estimatedTotalCents = items.reduce((total, item) => {
    const product = products.find((record) => record.id === item.product_id);
    if (!product) return total;
    return total + lineTotalCents(item.unit_price || product.selling_price, item.quantity);
  }, 0n);

  const updateItem = (index, field, value) => {
    setItems((current) => current.map((item, itemIndex) => (
      itemIndex === index ? { ...item, [field]: value } : item
    )));
  };

  const handleCreateSale = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    if (!items.length || items.some((item) => !products.some((product) => product.id === item.product_id))) {
      setFormError("Choose a valid product for every sale line.");
      setSaving(false);
      return;
    }
    try {
      const payload = {
        customer_id: selectedCustomer || undefined,
        items: items.map((item) => {
          const product = products.find((record) => record.id === item.product_id);
          return {
            product_id: item.product_id,
            quantity: item.quantity,
            unit_price: item.unit_price || product.selling_price,
          };
        }),
        payment_method: initialPaymentMethod,
        initial_payment_amount: initialPayment || undefined,
      };
      await businessApi.createSale(businessId, payload);
      setSelectedCustomer("");
      setItems([{ product_id: "", quantity: "1", unit_price: "" }]);
      setInitialPayment("");
      setInitialPaymentMethod("cash");
      onPageChange(1);
      if (refresh) await refresh();
    } catch (error) {
      setFormError(error.message || "The sale could not be created.");
    } finally {
      setSaving(false);
    }
  };

  const openReceipt = async (saleId) => {
    const printWindow = window.open("", "_blank", "width=420,height=640");
    if (!printWindow) {
      setFormError("Allow pop-ups to print a receipt.");
      return;
    }
    printWindow.document.write("<!doctype html><title>Preparing receipt…</title><p>Preparing receipt…</p>");
    try {
    const [payload, businessPayload] = await Promise.all([
      businessApi.getSale(businessId, saleId),
      businessApi.getBusiness(businessId),
    ]);
    const sale = payload.sale || {};
    const business = businessPayload.business || {};
    const rowsHtml = (sale.items || []).map((item) => `
      <tr>
        <td>${escapeHtml(item.description)}</td>
        <td>${escapeHtml(item.quantity)}</td>
        <td>${escapeHtml(money(item.unit_price))}</td>
        <td>${escapeHtml(money(item.line_total))}</td>
      </tr>
    `).join("");
    const paymentRowsHtml = (sale.payments || []).map((payment) => `
      <tr>
        <td>${escapeHtml(payment.direction)}</td>
        <td>${escapeHtml(payment.method)}</td>
        <td>${escapeHtml(parseDate(payment.payment_date))}</td>
        <td>${escapeHtml(money(payment.amount))}</td>
      </tr>
    `).join("");
    const customer = sale.customer_name
      || (sale.customer_id ? customers.find((record) => record.id === sale.customer_id)?.full_name : null)
      || "Walk-in customer";
    printWindow.document.open();
    printWindow.document.write(`<!doctype html>
      <html>
        <head><meta charset="utf-8"><title>${escapeHtml(business.name || "Business")} · Receipt</title>
          <style>
            *{box-sizing:border-box}body{font-family:Arial,sans-serif;padding:16px;color:#172033;font-size:12px}.receipt{max-width:74mm;margin:0 auto}.receipt__actions{display:flex;gap:8px;margin:0 auto 16px;max-width:74mm}.receipt__actions button{padding:8px;border:1px solid #b8c5d6;border-radius:4px;background:#fff;cursor:pointer}.receipt__header{text-align:center;border-bottom:1px dashed #99a4b3;padding-bottom:10px;margin-bottom:10px}.receipt__header h1{font-size:20px;margin:0 0 6px}.receipt__header p,.receipt__meta p{margin:4px 0;color:#526174}.receipt__meta{margin-bottom:10px}.receipt table{width:100%;border-collapse:collapse;font-size:10px}.receipt th{text-align:left}.receipt th,.receipt td{padding:5px 3px;border-bottom:1px solid #e8edf2}.receipt th:last-child,.receipt td:last-child{text-align:right}.receipt__totals{margin:12px 0}.receipt__totals p{display:flex;justify-content:space-between;margin:5px 0}.receipt__totals .receipt__grand{font-size:14px;font-weight:700;border-top:1px solid #bcc6d2;padding-top:7px}.receipt__footer{text-align:center;margin-top:16px;color:#5d6878}.receipt--a4{max-width:190mm}.receipt--a4 .receipt__header{text-align:left}.receipt--a4 table{font-size:12px}.receipt--a4 th,.receipt--a4 td{padding:8px}.receipt--a4 .receipt__totals{width:65mm;margin-left:auto}@page{margin:10mm}@media print{body{padding:0}.receipt__actions{display:none}.receipt--thermal{max-width:74mm}@page{size:auto;margin:4mm}.receipt--a4{max-width:190mm}@page{size:A4;margin:12mm}}
          </style>
        </head>
        <body>
          <div class="receipt receipt--thermal" id="receipt">
            <header class="receipt__header">
              <h1>${escapeHtml(business.name || "Business")}</h1>
              ${business.address ? `<p>${escapeHtml(business.address)}</p>` : ""}
              ${business.phone ? `<p>Phone: ${escapeHtml(business.phone)}</p>` : ""}
              ${business.contact_email ? `<p>${escapeHtml(business.contact_email)}</p>` : ""}
              <strong>SALES RECEIPT</strong>
            </header>
            <div class="receipt__meta">
              <p>Reference: ${escapeHtml(sale.reference_number || sale.id)}</p>
              <p>Customer: ${escapeHtml(customer)}</p>
              ${sale.customer_phone ? `<p>Phone: ${escapeHtml(sale.customer_phone)}</p>` : ""}
              <p>Date: ${escapeHtml(parseDate(sale.sale_date))}</p>
              <p>Status: ${escapeHtml(sale.status)}</p>
            </div>
            <table>
              <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Total</th></tr></thead>
              <tbody>${rowsHtml}</tbody>
            </table>
            <div class="receipt__totals">
              <p class="receipt__grand"><span>Total</span><strong>${money(sale.total_amount || 0)}</strong></p>
              <p><span>Paid</span><strong>${money(sale.amount_paid || 0)}</strong></p>
              <p><span>Outstanding</span><strong>${money(sale.outstanding_balance || 0)}</strong></p>
            </div>
            <h2>Payments</h2>
            <table><thead><tr><th>Type</th><th>Method</th><th>Date</th><th>Amount</th></tr></thead><tbody>${paymentRowsHtml || "<tr><td colspan='4'>No payments recorded</td></tr>"}</tbody></table>
            <p class="receipt__footer">Thank you for your business.</p>
          </div>
          <div class="receipt__actions">
            <button type="button" onclick="printReceipt('thermal')">Print thermal receipt</button>
            <button type="button" onclick="printReceipt('a4')">Print A4</button>
          </div>
          <script>
            function printReceipt(format) {
              const receipt = document.getElementById("receipt");
              receipt.classList.toggle("receipt--a4", format === "a4");
              receipt.classList.toggle("receipt--thermal", format === "thermal");
              window.print();
            }
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    } catch (failure) {
      printWindow.close();
      throw failure;
    }
  };

  async function loadSale(saleId) {
    setActionError("");
    setActionNotice("");
    try {
      const payload = await businessApi.getSale(businessId, saleId);
      setSelectedSale(payload.sale);
      setEditNotes(payload.sale.notes || "");
      setEditSaleDate((payload.sale.sale_date || "").slice(0, 10));
    } catch (error) {
      setActionError(error.message || "Sale details could not be loaded.");
    }
  }

  async function saveSaleDetails(event) {
    event.preventDefault();
    if (!selectedSale) return;
    setEditSaving(true);
    setActionError("");
    setActionNotice("");
    try {
      await businessApi.updateSale(businessId, selectedSale.id, {
        notes: editNotes || null,
        sale_date: editSaleDate || selectedSale.sale_date,
      });
      await Promise.all([loadSale(selectedSale.id), refresh?.()]);
      setActionNotice("Sale details updated.");
    } catch (error) {
      setActionError(error.message || "Sale details could not be updated.");
    } finally {
      setEditSaving(false);
    }
  }

  async function submitSaleAction(event, action, amount) {
    event.preventDefault();
    if (!selectedSale) return;
    setActionSaving(true);
    setActionError("");
    setActionNotice("");
    let notice;
    try {
      if (action === "payment") {
        await businessApi.recordPayment(businessId, selectedSale.id, { amount, method: paymentMethod });
        setPaymentAmount("");
        notice = "Payment recorded.";
      } else if (action === "refund") {
        await businessApi.recordRefund(businessId, selectedSale.id, { amount, method: paymentMethod });
        setRefundAmount("");
        notice = "Refund recorded.";
      } else {
        await businessApi.cancelSale(businessId, selectedSale.id, cancelReason);
        setCancelReason("");
        notice = "Sale cancelled and stock restored.";
      }
      await Promise.all([loadSale(selectedSale.id), refresh?.()]);
      setActionNotice(notice);
    } catch (error) {
      setActionError(error.message || "The sale update could not be saved.");
    } finally {
      setActionSaving(false);
    }
  }

  return (
    <>
      <PageHeading eyebrow="SALES" title="Sales" description="Create sales, manage receipts, and track payment status." />
      {error && <p className="form-feedback form-feedback--error" role="alert">{error}</p>}
      <section className="panel" style={{ marginBottom: "1rem" }}>
        <div className="panel-title"><div><h2>Record a sale</h2></div></div>
        <form onSubmit={handleCreateSale} className="stack-form">
          <div className="field-grid">
            <label>
              <span>Customer</span>
              <select value={selectedCustomer} onChange={(event) => setSelectedCustomer(event.target.value)}>
                <option value="">Walk-in customer</option>
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>{customer.full_name}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Initial payment</span>
              <input type="number" min="0" step="0.01" value={initialPayment} onChange={(event) => setInitialPayment(event.target.value)} placeholder="Optional" />
            </label>
            <label><span>Initial payment method</span><select value={initialPaymentMethod} onChange={(event) => setInitialPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="bank_transfer">Bank transfer</option><option value="pos">POS</option><option value="other">Other</option></select></label>
          </div>
          <label className="sale-product-search"><span>Find customer</span><input type="search" value={customerSearch} onChange={(event) => setCustomerSearch(event.target.value)} placeholder="Search by name, phone, or email" /></label>
          <label className="sale-product-search"><span>Find a product or service</span><input type="search" value={productSearch} onChange={(event) => setProductSearch(event.target.value)} placeholder="Search name, category, or SKU" /></label>
          {items.map((item, index) => (
            <div className="field-grid sale-item-row" key={`sale-item-${index}`}>
              <label>
                <span>Product or service</span>
                <select required value={item.product_id} onChange={(event) => updateItem(index, "product_id", event.target.value)}>
                  <option value="">Select an item</option>
                  {products.map((product) => (
                    <option key={product.id} value={product.id}>{product.name} · {money(product.selling_price || 0)}</option>
                  ))}
                </select>
              </label>
              <label><span>Quantity</span><input required type="number" min="0.001" step="0.001" value={item.quantity} onChange={(event) => updateItem(index, "quantity", event.target.value)} /></label>
              <label><span>Unit price (NGN)</span><input type="number" min="0" step="0.01" value={item.unit_price} onChange={(event) => updateItem(index, "unit_price", event.target.value)} placeholder="Catalogue price" /></label>
              {items.length > 1 && <button type="button" className="quiet-button" onClick={() => setItems((current) => current.filter((_, itemIndex) => itemIndex !== index))}>Remove line</button>}
            </div>
          ))}
          <button type="button" className="quiet-button" onClick={() => setItems((current) => [...current, { product_id: "", quantity: "1", unit_price: "" }])}>+ Add another item</button>
          <p className="sale-estimate"><span>Estimated subtotal</span><strong>{formatMinorUnits(estimatedTotalCents)}</strong><small>Line totals are rounded to the nearest cent; discounts and tax are not configured.</small></p>
          {formError && <p className="form-feedback form-feedback--error" role="alert">{formError}</p>}
          <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : "Create sale"}</button>
        </form>
      </section>
      <div className="management-toolbar">
        <label><span>Search sales</span><input type="search" value={query} onChange={(event) => onQueryChange(event.target.value)} placeholder="Reference or notes" /></label>
        <label><span>Status</span><select value={status} onChange={(event) => onStatusChange(event.target.value)}><option value="all">All statuses</option><option value="pending">Pending</option><option value="partially_paid">Partially paid</option><option value="paid">Paid</option><option value="cancelled">Cancelled</option><option value="refunded">Refunded</option></select></label>
        <label><span>Sales period</span><select value={range} onChange={(event) => onRangeChange(event.target.value)}><option value="today">Today</option><option value="this_week">This week</option><option value="this_month">This month</option><option value="this_year">This year</option><option value="custom">Custom dates</option></select></label>
        {range === "custom" && <>
          <label><span>From</span><input type="date" value={startDate} onChange={(event) => onStartDateChange(event.target.value)} /></label>
          <label><span>To</span><input type="date" value={endDate} onChange={(event) => onEndDateChange(event.target.value)} /></label>
        </>}
      </div>
      {loading ? <div className="empty-state">Loading sales…</div> : (
        <section className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead><tr><th>REFERENCE</th><th>CUSTOMER</th><th>DATE</th><th>AMOUNT</th><th>STATUS</th><th>DETAILS</th><th>RECEIPT</th></tr></thead>
              <tbody>
                {rows.map((sale) => (
                  <tr key={sale.id}>
                    <td>{sale.reference_number}</td>
                    <td>{sale.customer}</td>
                    <td>{parseDate(sale.date)}</td>
                    <td>{money(sale.amount)}</td>
                    <td>{sale.status}</td>
                    <td><button type="button" className="quiet-button" onClick={() => loadSale(sale.id)}>View</button></td>
                    <td><button type="button" className="quiet-button" onClick={() => openReceipt(sale.id).catch((failure) => setFormError(failure.message))}>Print</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!rows.length && <div className="empty-state">No sales recorded in this period.</div>}
          {rows.length > 0 && <div className="customer-list-footer">
            <span>Showing {(page - 1) * (pagination.per_page || 25) + 1}–{Math.min((page - 1) * (pagination.per_page || 25) + rows.length, pagination.total || 0)} of {pagination.total || 0}</span>
            {(pagination.pages || 0) > 1 && <nav className="customer-pagination" aria-label="Sales pages">
              <button type="button" className="quiet-button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
              <span>Page {page} of {pagination.pages}</span>
              <button type="button" className="quiet-button" disabled={page >= pagination.pages} onClick={() => onPageChange(page + 1)}>Next</button>
            </nav>}
          </div>}
        </section>
      )}
      {selectedSale?.business_id === businessId && <section className="panel management-panel">
        <div className="panel-title"><div><h2>Sale {selectedSale.reference_number}</h2><p>{selectedSale.status} · {money(selectedSale.total_amount)} total · {money(selectedSale.outstanding_balance)} outstanding</p></div></div>
        <div className="table-scroll"><table><thead><tr><th>ITEM</th><th>QTY</th><th>UNIT PRICE</th><th>TOTAL</th></tr></thead>
          <tbody>{selectedSale.items.map((item) => <tr key={item.id}><td>{item.description}</td><td>{item.quantity}</td><td>{money(item.unit_price)}</td><td>{money(item.line_total)}</td></tr>)}</tbody>
        </table></div>
        <h3 className="management-subheading">Payment history</h3>
        <div className="table-scroll"><table><thead><tr><th>REFERENCE</th><th>DIRECTION</th><th>METHOD</th><th>AMOUNT</th><th>DATE</th></tr></thead>
          <tbody>{selectedSale.payments.map((payment) => <tr key={payment.id}><td>{payment.reference}</td><td>{payment.direction}</td><td>{payment.method}</td><td>{money(payment.amount)}</td><td>{parseDate(payment.payment_date)}</td></tr>)}</tbody>
        </table></div>
        {["owner", "manager"].includes(businessRole) && !["cancelled", "refunded"].includes(selectedSale.status) && <form className="management-form sale-edit-form" onSubmit={saveSaleDetails}>
          <label><span>Sale date</span><input required type="date" value={editSaleDate} onChange={(event) => setEditSaleDate(event.target.value)} /></label>
          <label><span>Sale notes</span><input maxLength="4000" value={editNotes} onChange={(event) => setEditNotes(event.target.value)} placeholder="Optional internal note" /></label>
          <button type="submit" className="primary-button" disabled={editSaving}>{editSaving ? "Saving…" : "Update sale details"}</button>
        </form>}
        {selectedSale.status !== "cancelled" && selectedSale.status !== "refunded" && <div className="management-form sale-action-forms">
          <form onSubmit={(event) => submitSaleAction(event, "payment", paymentAmount)}>
            <label><span>Record payment</span><input required type="number" min="0.01" step="0.01" value={paymentAmount} onChange={(event) => setPaymentAmount(event.target.value)} /></label>
            <label><span>Method</span><select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="bank_transfer">Bank transfer</option><option value="pos">POS</option><option value="other">Other</option></select></label>
            <button type="submit" className="primary-button" disabled={actionSaving}>Record payment</button>
          </form>
          {["owner", "manager"].includes(businessRole) && <>
            <form onSubmit={(event) => submitSaleAction(event, "refund", refundAmount)}>
              <label><span>Record refund</span><input required type="number" min="0.01" step="0.01" value={refundAmount} onChange={(event) => setRefundAmount(event.target.value)} /></label>
              <label><span>Method</span><select value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value)}><option value="cash">Cash</option><option value="bank_transfer">Bank transfer</option><option value="pos">POS</option><option value="other">Other</option></select></label>
              <button type="submit" className="primary-button" disabled={actionSaving}>Record refund</button>
            </form>
            <form onSubmit={(event) => submitSaleAction(event, "cancel", cancelReason)}>
              <label><span>Cancellation reason</span><input maxLength="500" value={cancelReason} onChange={(event) => setCancelReason(event.target.value)} /></label>
              <button type="submit" className="primary-button" disabled={actionSaving}>Cancel sale</button>
            </form>
          </>}
        </div>}
        {actionError && <p className="form-feedback form-feedback--error" role="alert">{actionError}</p>}
        {actionNotice && <p className="form-feedback" role="status">{actionNotice}</p>}
      </section>}
    </>
  );
}

function DashboardPage({ page, businessId, businessRole, onProfileSaved, user }) {
  const [dashboard, setDashboard] = useState(null);
  const [salesReport, setSalesReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [salesLoading, setSalesLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState("");
  const [salesError, setSalesError] = useState("");
  const [salesRange, setSalesRange] = useState("this_month");
  const [expenseRange, setExpenseRange] = useState("this_month");
  const [salesQuery, setSalesQuery] = useState("");
  const [salesStatus, setSalesStatus] = useState("all");
  const [salesPage, setSalesPage] = useState(1);
  const [salesStartDate, setSalesStartDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10));
  const [salesEndDate, setSalesEndDate] = useState(new Date().toISOString().slice(0, 10));

  const refreshDashboard = () => {
    if (!businessId) return;
    setLoading(true);
    setDashboard(null);
    setDashboardError("");
    businessApi.getDashboard(businessId, salesRange)
      .then((payload) => setDashboard(payload))
      .catch((error) => {
        setDashboard(null);
        setDashboardError(error.message || "Business performance could not be loaded.");
      })
      .finally(() => setLoading(false));
  };

  const refreshSalesReport = () => {
    if (!businessId) return;
    setSalesLoading(true);
    setSalesReport(null);
    setSalesError("");
    businessApi.getSales(businessId, {
      q: salesQuery,
      status: salesStatus,
      page: salesPage,
      per_page: 25,
      range: salesRange,
      ...(salesRange === "custom" ? { start_date: salesStartDate, end_date: salesEndDate } : {}),
    })
      .then((payload) => setSalesReport(payload))
      .catch((error) => {
        setSalesReport(null);
        setSalesError(error.message || "Sales could not be loaded.");
      })
      .finally(() => setSalesLoading(false));
  };

  useEffect(() => {
    if (page === "overview") refreshDashboard();
  }, [businessId, page, salesRange]);

  useEffect(() => {
    if (page === "sales") refreshSalesReport();
  }, [businessId, page, salesRange, salesStatus, salesPage, salesQuery, salesStartDate, salesEndDate]);

  if (!businessId) return <div className="empty-state">Choose a business workspace to continue.</div>;

  switch (page) {
    case "sales":
      return <SalesPage
        data={salesReport}
        loading={salesLoading}
        error={salesError}
        businessId={businessId}
        businessRole={businessRole}
        range={salesRange}
        onRangeChange={(value) => { setSalesRange(value); setSalesPage(1); }}
        refresh={refreshSalesReport}
        query={salesQuery}
        onQueryChange={(value) => { setSalesQuery(value); setSalesPage(1); }}
        status={salesStatus}
        onStatusChange={(value) => { setSalesStatus(value); setSalesPage(1); }}
        page={salesPage}
        onPageChange={setSalesPage}
        startDate={salesStartDate}
        endDate={salesEndDate}
        onStartDateChange={(value) => { setSalesStartDate(value); setSalesPage(1); }}
        onEndDateChange={(value) => { setSalesEndDate(value); setSalesPage(1); }}
      />;
    case "expenses":
      return <ExpenseManagementPage businessId={businessId} businessRole={businessRole} range={expenseRange} onRangeChange={setExpenseRange} />;
    case "customers":
      return <CustomerPage businessId={businessId} businessRole={businessRole} />;
    case "products":
      return <ProductPage businessId={businessId} businessRole={businessRole} />;
    case "inventory":
      return <InventoryPage businessId={businessId} businessRole={businessRole} />;
    case "reports":
      return <BusinessReportsPage businessId={businessId} />;
    case "settings":
      return <BusinessProfilePage businessId={businessId} businessRole={businessRole} user={user} onProfileSaved={onProfileSaved} />;
    case "assistant":
      return <AssistantPage businessId={businessId} />;
    default:
      return <OverviewPage data={dashboard?.business_id === businessId ? dashboard : null} loading={loading} error={dashboardError} range={salesRange} onRangeChange={(value) => { setSalesRange(value); setSalesPage(1); }} />;
  }
}

export default DashboardPage;
