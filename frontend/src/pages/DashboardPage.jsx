import { useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import { PageHeading } from "../components/UI.jsx";
import { businessApi } from "../services/businessApi.js";

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

function OverviewPage({ data }) {
  const analytics = data || {};
  return (
    <>
      <PageHeading eyebrow="REAL BUSINESS DATA" title="Overview" description="Performance metrics from the active business workspace." />
      <div className="metric-grid">
        <MetricCard title="Total sales" value={money(analytics.total_sales || 0)} hint="Gross revenue" icon="wallet" variant="blue" />
        <MetricCard title="Total expenses" value={money(analytics.operating_expenses || 0)} hint="Business costs" icon="receipt" variant="orange" />
        <MetricCard title="Gross profit" value={money(analytics.gross_profit || 0)} hint="After COGS" icon="trend" variant="green" />
        <MetricCard title="Net profit" value={money(analytics.net_profit || 0)} hint="After expenses" icon="users" variant="purple" />
      </div>
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
          <div className="panel-title">
            <div><h2>Low-stock products</h2></div>
          </div>
          <div className="table-scroll">
            <table>
              <thead><tr><th>PRODUCT</th><th>IN STOCK</th><th>REORDER</th></tr></thead>
              <tbody>
                {(analytics.low_stock_products || []).map((item) => (
                  <tr key={item.name}>
                    <td>{item.name}</td>
                    <td>{item.quantity_on_hand}</td>
                    <td>{item.reorder_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </>
  );
}

function SalesPage({ data, loading, businessId, refresh }) {
  const rows = data?.items || [];
  const [products, setProducts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [selectedCustomer, setSelectedCustomer] = useState("");
  const [selectedProductId, setSelectedProductId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [unitPrice, setUnitPrice] = useState("");
  const [initialPayment, setInitialPayment] = useState("");

  useEffect(() => {
    if (!businessId) return;
    Promise.all([
      fetch(`/api/v1/businesses/${encodeURIComponent(businessId)}/products?per_page=50`, { credentials: "same-origin" }).then((res) => res.ok ? res.json() : { products: [] }),
      fetch(`/api/v1/businesses/${encodeURIComponent(businessId)}/customers?per_page=50`, { credentials: "same-origin" }).then((res) => res.ok ? res.json() : { customers: [] }),
    ]).then(([productPayload, customerPayload]) => {
      setProducts(productPayload.products || []);
      setCustomers(customerPayload.customers || []);
    }).catch(() => {
      setProducts([]);
      setCustomers([]);
    });
  }, [businessId]);

  const handleCreateSale = async (event) => {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    const product = products.find((item) => item.id === selectedProductId);
    if (!product) {
      setFormError("Choose a valid product to sell.");
      setSaving(false);
      return;
    }
    try {
      const payload = {
        customer_id: selectedCustomer || undefined,
        items: [{ product_id: product.id, quantity: Number(quantity), unit_price: unitPrice || product.selling_price }],
        payment_method: "cash",
        initial_payment_amount: initialPayment || undefined,
      };
      await businessApi.createSale(businessId, payload);
      setSelectedCustomer("");
      setSelectedProductId("");
      setQuantity(1);
      setUnitPrice("");
      setInitialPayment("");
      if (refresh) await refresh();
    } catch (error) {
      setFormError(error.message || "The sale could not be created.");
    } finally {
      setSaving(false);
    }
  };

  const openReceipt = async (saleId) => {
    const payload = await businessApi.getSale(businessId, saleId);
    const sale = payload.sale || {};
    const printWindow = window.open("", "_blank", "width=420,height=640");
    const rowsHtml = (sale.items || []).map((item) => `
      <tr>
        <td>${item.description}</td>
        <td>${item.quantity}</td>
        <td>${money(item.unit_price)}</td>
        <td>${money(item.line_total)}</td>
      </tr>
    `).join("");
    printWindow.document.write(`
      <html>
        <head><title>STEER Receipt</title>
          <style>
            body{font-family:Arial,sans-serif;padding:20px;color:#111;} .receipt{max-width:360px;margin:0 auto;} h1{font-size:22px;margin:0 0 12px;} table{width:100%; border-collapse:collapse;} td{padding:4px 0; border-bottom:1px solid #eee;} .summary{margin-top:10px; font-weight:bold;} button{display:none;}
          </style>
        </head>
        <body>
          <div class="receipt">
            <h1>STEER Receipt</h1>
            <p>Reference: ${sale.reference_number || sale.id}</p>
            <p>Customer: ${sale.customer_id ? (customers.find((customer) => customer.id === sale.customer_id)?.full_name || "Customer") : "Walk-in customer"}</p>
            <p>Date: ${parseDate(sale.sale_date)}</p>
            <table>
              <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Total</th></tr></thead>
              <tbody>${rowsHtml}</tbody>
            </table>
            <div class="summary">Total: ${money(sale.total_amount || 0)}</div>
            <div class="summary">Paid: ${money(sale.amount_paid || 0)}</div>
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 500);
  };

  return (
    <>
      <PageHeading eyebrow="SALES" title="Sales" description="Create sales, manage receipts, and track payment status." />
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
              <span>Product</span>
              <select value={selectedProductId} onChange={(event) => setSelectedProductId(event.target.value)}>
                <option value="">Select a product</option>
                {products.map((product) => (
                  <option key={product.id} value={product.id}>{product.name} · {money(product.selling_price || 0)}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Quantity</span>
              <input type="number" min="1" step="1" value={quantity} onChange={(event) => setQuantity(Number(event.target.value || 1))} />
            </label>
            <label>
              <span>Unit price (NGN)</span>
              <input type="number" min="0" step="0.01" value={unitPrice} onChange={(event) => setUnitPrice(event.target.value)} placeholder="Optional override" />
            </label>
            <label>
              <span>Initial payment</span>
              <input type="number" min="0" step="0.01" value={initialPayment} onChange={(event) => setInitialPayment(event.target.value)} placeholder="Optional" />
            </label>
          </div>
          {formError && <p className="form-feedback form-feedback--error" role="alert">{formError}</p>}
          <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : "Create sale"}</button>
        </form>
      </section>
      {loading ? <div className="empty-state">Loading sales…</div> : (
        <section className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead><tr><th>REFERENCE</th><th>CUSTOMER</th><th>DATE</th><th>AMOUNT</th><th>STATUS</th><th>RECEIPT</th></tr></thead>
              <tbody>
                {rows.map((sale) => (
                  <tr key={sale.id}>
                    <td>{sale.id}</td>
                    <td>{sale.customer}</td>
                    <td>{parseDate(sale.date)}</td>
                    <td>{money(sale.amount)}</td>
                    <td>{sale.status}</td>
                    <td><button type="button" onClick={() => openReceipt(sale.id)}>Print</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

function ExpensesPage({ data, loading, businessId, range, onRangeChange }) {
  const rows = data?.items || [];
  return (
    <>
      <PageHeading eyebrow="EXPENSES" title="Expenses" description="Operating expenses recorded against the active business." />
      <div className="toolbar-row" style={{ marginBottom: "1rem" }}>
        <select value={range} onChange={(event) => onRangeChange?.(event.target.value)}>
          <option value="today">Today</option>
          <option value="this_week">This week</option>
          <option value="this_month">This month</option>
        </select>
      </div>
      {loading ? <div className="empty-state">Loading expenses…</div> : (
        <section className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead><tr><th>CATEGORY</th><th>DESCRIPTION</th><th>DATE</th><th>AMOUNT</th></tr></thead>
              <tbody>
                {rows.map((item) => (
                  <tr key={item.id}>
                    <td>{item.category}</td>
                    <td>{item.description}</td>
                    <td>{parseDate(item.date)}</td>
                    <td>{money(item.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

function ReportsPage({ data, loading }) {
  const items = data?.items || [];
  return (
    <>
      <PageHeading eyebrow="REPORTS" title="Reports" description="CSV-exportable business reports and analytics." />
      {loading ? <div className="empty-state">Loading reports…</div> : (
        <section className="panel table-panel">
          <div className="table-scroll">
            <table>
              <thead><tr><th>REFERENCE</th><th>CUSTOMER</th><th>AMOUNT</th><th>STATUS</th><th>DATE</th></tr></thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id || row.reference || row.name}>
                    <td>{row.id || row.reference || row.name}</td>
                    <td>{row.customer || row.name || "—"}</td>
                    <td>{money(row.amount || 0)}</td>
                    <td>{row.status || "—"}</td>
                    <td>{parseDate(row.date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

function DashboardPage({ page, businessId }) {
  const [dashboard, setDashboard] = useState(null);
  const [salesReport, setSalesReport] = useState(null);
  const [expenseReport, setExpenseReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [salesLoading, setSalesLoading] = useState(true);
  const [expenseLoading, setExpenseLoading] = useState(true);
  const [salesRange, setSalesRange] = useState("this_month");
  const [expenseRange, setExpenseRange] = useState("this_month");

  const refreshDashboard = () => {
    if (!businessId) return;
    setLoading(true);
    businessApi.getDashboard(businessId, salesRange)
      .then((payload) => setDashboard(payload))
      .catch(() => setDashboard({}))
      .finally(() => setLoading(false));
  };

  const refreshSalesReport = () => {
    if (!businessId) return;
    setSalesLoading(true);
    businessApi.getReports(businessId, "sales", salesRange)
      .then((payload) => setSalesReport(payload))
      .catch(() => setSalesReport({ items: [] }))
      .finally(() => setSalesLoading(false));
  };

  const refreshExpenseReport = () => {
    if (!businessId) return;
    setExpenseLoading(true);
    businessApi.getReports(businessId, "expenses", expenseRange)
      .then((payload) => setExpenseReport(payload))
      .catch(() => setExpenseReport({ items: [] }))
      .finally(() => setExpenseLoading(false));
  };

  useEffect(() => {
    refreshDashboard();
  }, [businessId, salesRange]);

  useEffect(() => {
    refreshSalesReport();
  }, [businessId, salesRange]);

  useEffect(() => {
    refreshExpenseReport();
  }, [businessId, expenseRange]);

  if (!businessId) return <div className="empty-state">Choose a business workspace to continue.</div>;

  switch (page) {
    case "sales":
      return <SalesPage data={salesReport} loading={salesLoading} businessId={businessId} refresh={refreshSalesReport} />;
    case "expenses":
      return <ExpensesPage data={expenseReport} loading={expenseLoading} businessId={businessId} range={expenseRange} onRangeChange={setExpenseRange} />;
    case "reports":
      return <ReportsPage data={salesReport} loading={salesLoading} />;
    default:
      return <OverviewPage data={dashboard} />;
  }
}

export default DashboardPage;
