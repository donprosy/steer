import { useMemo, useState } from "react";
import { DonutChart, LineChart } from "../components/Charts.jsx";
import Icon from "../components/Icon.jsx";
import { Avatar, Button, Modal, PageHeading } from "../components/UI.jsx";

const initialSales = [
  { id: "#DP-1084", name: "Olivia Chen", initials: "OC", product: "Monthly retainer", date: "Nov 7, 2026", amount: 1250, status: "Completed" },
  { id: "#DP-1083", name: "Marcus Williams", initials: "MW", product: "Brand strategy", date: "Nov 6, 2026", amount: 840, status: "Pending" },
  { id: "#DP-1082", name: "Ava Robinson", initials: "AR", product: "Design consultation", date: "Nov 5, 2026", amount: 560, status: "Completed" },
  { id: "#DP-1081", name: "Noah Patel", initials: "NP", product: "Website package", date: "Nov 4, 2026", amount: 2100, status: "Completed" },
  { id: "#DP-1080", name: "Sophia Brooks", initials: "SB", product: "Monthly retainer", date: "Nov 3, 2026", amount: 1250, status: "Refunded" },
];

const initialCustomers = [
  { name: "Olivia Chen", email: "olivia.chen@example.com", company: "Olive & Oak", spent: "$4,820", orders: 12, date: "Nov 7, 2026", initials: "OC", color: "lavender", status: "Active" },
  { name: "Marcus Williams", email: "marcus.w@example.com", company: "Williams Co.", spent: "$3,640", orders: 8, date: "Nov 6, 2026", initials: "MW", color: "blue", status: "Active" },
  { name: "Ava Robinson", email: "ava.r@example.com", company: "Studio Ava", spent: "$2,910", orders: 7, date: "Nov 5, 2026", initials: "AR", color: "peach", status: "Active" },
  { name: "Noah Patel", email: "noah.p@example.com", company: "Patel & Sons", spent: "$2,480", orders: 5, date: "Nov 4, 2026", initials: "NP", color: "mint", status: "Active" },
];

const initialProducts = [
  { name: "Signature candle", sku: "PRD-001", category: "Home & living", stock: 48, price: "$28.00", initials: "SC", color: "peach" },
  { name: "Everyday tote", sku: "PRD-002", category: "Accessories", stock: 32, price: "$36.00", initials: "ET", color: "blue" },
  { name: "Ceramic pour-over", sku: "PRD-003", category: "Home & living", stock: 8, price: "$42.00", initials: "CP", color: "lavender" },
  { name: "Linen journal", sku: "PRD-004", category: "Stationery", stock: 5, price: "$18.00", initials: "LJ", color: "mint" },
  { name: "Weekend market bag", sku: "PRD-005", category: "Accessories", stock: 24, price: "$32.00", initials: "MB", color: "yellow" },
];

const initialExpenses = [
  { name: "Wholesale inventory", category: "Inventory", date: "Nov 7, 2026", amount: 1840, initials: "IN", color: "blue" },
  { name: "Studio rent", category: "Operations", date: "Nov 5, 2026", amount: 1200, initials: "OP", color: "violet" },
  { name: "Social media campaign", category: "Marketing", date: "Nov 3, 2026", amount: 680, initials: "MK", color: "cyan" },
  { name: "Courier services", category: "Operations", date: "Nov 2, 2026", amount: 245, initials: "OP", color: "violet" },
];

const money = (amount) => `$${Number(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function downloadCsv(filename, headers, rows) {
  const quote = (value) => `"${String(value).replaceAll('"', '""')}"`;
  const csv = [headers, ...rows].map((row) => row.map(quote).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function Card({ className = "", children }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

function PanelTitle({ title, detail, action }) {
  return <div className="panel-title"><div><h2>{title}</h2>{detail && <p>{detail}</p>}</div>{action}</div>;
}

function MetricCard({ title, value, change, icon, variant = "blue", negative = false, footnote = "vs. previous month" }) {
  return <article className="metric-card"><div className="metric-card__top"><span>{title}</span><span className={`metric-icon metric-icon--${variant}`}><Icon name={icon} size={19} /></span></div><strong>{value}</strong><div className="metric-card__bottom"><span className={`metric-change${negative ? " metric-change--negative" : ""}`}><Icon name={negative ? "arrowDown" : "arrowRight"} size={14} />{change}</span><span>{footnote}</span></div></article>;
}

function PeriodSelect({ value, onChange, options = ["Last 30 days", "Last 7 days", "This year"] }) {
  return <label className="select-wrap"><Icon name="calendar" size={15} /><select aria-label="Select reporting period" value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option}>{option}</option>)}</select><Icon name="arrowDown" size={13} /></label>;
}

function Status({ value }) {
  return <span className={`status-pill status-pill--${value.toLowerCase().replaceAll(" ", "-")}`}><i />{value}</span>;
}

function Overview({ navigate }) {
  const [period, setPeriod] = useState("Last 30 days");
  return <>
    <PageHeading eyebrow="SATURDAY, NOVEMBER 7, 2026" title="Good morning, Jamie" description="Here’s what’s happening with your business today." action={<PeriodSelect value={period} onChange={setPeriod} />} />
    <div className="metric-grid">
      <MetricCard title="Total revenue" value="$24,580" change="+12.8%" icon="wallet" variant="blue" />
      <MetricCard title="Total expenses" value="$8,420" change="-4.2%" icon="receipt" variant="orange" negative={false} />
      <MetricCard title="Net profit" value="$16,160" change="+18.4%" icon="trend" variant="green" />
      <MetricCard title="Total customers" value="248" change="+8.1%" icon="users" variant="purple" />
    </div>
    <div className="overview-charts">
      <Card className="revenue-panel"><PanelTitle title="Revenue overview" detail="A look at how your business is performing" action={<div className="chart-legend"><span><i /> Revenue</span><span><i /> Expenses</span></div>} /><LineChart mode="revenue" /><div className="chart-footnote"><span><i /> Showing sample revenue trend</span><b>+18.4% <small>in the last 6 months</small></b></div></Card>
      <Card className="expense-panel"><PanelTitle title="Expense breakdown" detail="Where the money goes" action={<button className="quiet-button" onClick={() => navigate("/app/expenses")}>View details <Icon name="arrowRight" size={14} /></button>} /><DonutChart /></Card>
    </div>
    <div className="overview-bottom">
      <Card className="transactions-panel">
        <PanelTitle title="Recent transactions" detail="Your latest business activity" action={<button className="quiet-button" onClick={() => navigate("/app/sales")}>View all <Icon name="arrowRight" size={14} /></button>} />
        <div className="transaction-list">{initialSales.slice(0, 4).map((sale) => <div className="transaction-row" key={sale.id}><Avatar initials={sale.initials} small color={sale.initials === "OC" ? "lavender" : sale.initials === "MW" ? "blue" : "mint"} /><div className="transaction-row__name"><b>{sale.name}</b><span>{sale.product}</span></div><span className="transaction-row__date">{sale.date.replace(", 2026", "")}</span><b className="transaction-row__amount">+{money(sale.amount)}</b></div>)}</div>
      </Card>
      <Card className="activity-panel">
        <PanelTitle title="A few things to notice" detail="Helpful reminders for today" action={<Icon name="more" size={18} />} />
        <div className="activity-list">
          <div className="activity-item"><span className="activity-bullet activity-bullet--orange"><Icon name="package" size={16} /></span><div><b>Stock is running low</b><p>Ceramic pour-over and Linen journal have fewer than 10 items.</p><small>Based on sample stock data · 2 hours ago</small></div></div>
          <div className="activity-item"><span className="activity-bullet activity-bullet--green"><Icon name="trend" size={16} /></span><div><b>Revenue is trending up</b><p>Sales are ahead of the previous month in this demo.</p><small>Sample business insight · Yesterday</small></div></div>
        </div>
      </Card>
    </div>
  </>;
}

function SalesPage({ navigate }) {
  const [period, setPeriod] = useState("This month");
  const [query, setQuery] = useState("");
  const [sales, setSales] = useState(initialSales);
  const [showModal, setShowModal] = useState(false);
  const [selectedSale, setSelectedSale] = useState(null);
  const filtered = sales.filter((sale) => `${sale.name} ${sale.id} ${sale.product} ${sale.status}`.toLowerCase().includes(query.toLowerCase()));
  function addSale(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    setSales([{ id: `#DP-${1090 + sales.length}`, name: form.elements.customer.value, initials: form.elements.customer.value.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase(), product: form.elements.product.value, date: "Nov 7, 2026", amount: Number(form.elements.amount.value), status: "Pending" }, ...sales]);
    setShowModal(false);
  }
  return <>
    <PageHeading eyebrow="BUSINESS ACTIVITY" title="Sales" description="Track transactions and understand what’s driving your revenue." action={<Button onClick={() => setShowModal(true)} icon="plus">Record a sale</Button>} />
    <div className="metric-grid metric-grid--three"><MetricCard title="Gross sales" value="$24,580" change="+12.8%" icon="wallet" variant="blue" /><MetricCard title="Transactions" value="186" change="+9.4%" icon="activity" variant="purple" /><MetricCard title="Average order" value="$132.15" change="+3.1%" icon="trend" variant="green" /></div>
    <Card className="table-panel"><PanelTitle title="All transactions" detail="A demonstration view of recent business sales" action={<PeriodSelect value={period} onChange={setPeriod} options={["This month", "Last month", "This year"]} />} />
      <div className="table-toolbar"><label className="table-search"><Icon name="search" size={17} /><input placeholder="Search sales..." value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="outline-small" onClick={() => setPeriod(period === "This month" ? "Last month" : "This month")}><Icon name="filter" size={16} /> Filter: {period}</button></div>
      <div className="table-scroll"><table><thead><tr><th>TRANSACTION</th><th>CUSTOMER</th><th>DATE</th><th>AMOUNT</th><th>STATUS</th><th aria-label="Actions" /></tr></thead><tbody>
        {filtered.map((sale) => <tr key={sale.id}><td><b>{sale.id}</b><span className="table-subtext">{sale.product}</span></td><td><span className="table-person"><Avatar initials={sale.initials} small color="blue" />{sale.name}</span></td><td>{sale.date}</td><td><b>{money(sale.amount)}</b></td><td><Status value={sale.status} /></td><td><button className="table-more" aria-label={`View ${sale.id}`} onClick={() => setSelectedSale(sale)}><Icon name="more" size={18} /></button></td></tr>)}
      </tbody></table>{filtered.length === 0 && <div className="empty-state">No sample sales match “{query}”.</div>}</div>
      <div className="table-pagination"><span>Showing {filtered.length} of {sales.length} demonstration transactions</span><div><button disabled aria-label="Previous page"><Icon name="arrowLeft" size={15} /></button><button className="page-number">1</button><button disabled aria-label="Next page"><Icon name="arrowRight" size={15} /></button></div></div>
    </Card>
    {showModal && <Modal title="Record a demonstration sale" onClose={() => setShowModal(false)}><p className="modal-intro">This will add a temporary sample row to this browser view. It will not be sent to a server.</p><form className="modal-form" onSubmit={addSale}><label>Customer name<input name="customer" required placeholder="e.g. Alex Morgan" /></label><label>Product or service<input name="product" required placeholder="e.g. Product consultation" /></label><label>Amount (USD)<input name="amount" type="number" min="0.01" step="0.01" required placeholder="0.00" /></label><div className="modal-actions"><Button type="button" variant="outline" onClick={() => setShowModal(false)}>Cancel</Button><Button type="submit">Add sample sale</Button></div></form></Modal>}
    {selectedSale && <Modal title="Demonstration transaction" onClose={() => setSelectedSale(null)}><div className="detail-list"><div><span>Transaction</span><b>{selectedSale.id}</b></div><div><span>Customer</span><b>{selectedSale.name}</b></div><div><span>Product or service</span><b>{selectedSale.product}</b></div><div><span>Date</span><b>{selectedSale.date}</b></div><div><span>Amount</span><b>{money(selectedSale.amount)}</b></div><div><span>Status</span><Status value={selectedSale.status} /></div></div><p className="modal-intro">Sample transaction details only; no live business record is connected.</p></Modal>}
  </>;
}

function ExpensesPage() {
  const [expenses, setExpenses] = useState(initialExpenses);
  const [query, setQuery] = useState("");
  const [period, setPeriod] = useState("This month");
  const [showModal, setShowModal] = useState(false);
  const total = expenses.reduce((sum, expense) => sum + expense.amount, 0);
  const filtered = expenses.filter((expense) => `${expense.name} ${expense.category}`.toLowerCase().includes(query.toLowerCase()));
  function addExpense(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const category = form.elements.category.value;
    setExpenses([{ name: form.elements.name.value, category, date: "Nov 7, 2026", amount: Number(form.elements.amount.value), initials: category.slice(0, 2).toUpperCase(), color: "blue" }, ...expenses]);
    setShowModal(false);
  }
  return <>
    <PageHeading eyebrow="KEEP SPENDING IN VIEW" title="Expenses" description="Understand your business costs and keep the details together." action={<Button onClick={() => setShowModal(true)} icon="plus">Add expense</Button>} />
    <div className="metric-grid metric-grid--three"><MetricCard title="Total expenses" value={money(total)} change="-4.2%" icon="wallet" variant="orange" /><MetricCard title="Expense entries" value={`${expenses.length + 36}`} change="+5.8%" icon="receipt" variant="blue" /><MetricCard title="Largest category" value="Inventory" change="42% of spend" icon="package" variant="purple" /></div>
    <div className="overview-charts expense-layout"><Card><PanelTitle title="Spending by category" detail="Illustrative breakdown for the current period" action={<PeriodSelect value={period} onChange={setPeriod} />} /><DonutChart /></Card><Card><PanelTitle title="Monthly expenses" detail="Sample spending trend" /><LineChart mode="sales" /></Card></div>
    <Card className="table-panel"><PanelTitle title="Expense history" detail="Recent demonstration expenses" /><div className="table-toolbar"><label className="table-search"><Icon name="search" size={17} /><input placeholder="Search expenses..." value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="outline-small" onClick={() => setPeriod(period === "This month" ? "Last month" : "This month")}><Icon name="filter" size={16} /> {period}</button></div>
      <div className="table-scroll"><table><thead><tr><th>EXPENSE</th><th>CATEGORY</th><th>DATE</th><th>AMOUNT</th><th aria-label="Actions" /></tr></thead><tbody>{filtered.map((expense, index) => <tr key={`${expense.name}-${index}`}><td><span className="table-person"><span className={`expense-avatar expense-avatar--${expense.color}`}><Icon name="wallet" size={16} /></span><b>{expense.name}</b></span></td><td><span className="category-chip">{expense.category}</span></td><td>{expense.date}</td><td><b>{money(expense.amount)}</b></td><td><button className="table-more" aria-label={`More options for ${expense.name}`} onClick={() => window.alert("Sample expense details are not connected to a live record.")}><Icon name="more" size={18} /></button></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="empty-state">No sample expenses found.</div>}</div>
    </Card>
    {showModal && <Modal title="Add a demonstration expense" onClose={() => setShowModal(false)}><p className="modal-intro">This sample stays in this browser view and is not saved to a business account.</p><form className="modal-form" onSubmit={addExpense}><label>Description<input name="name" required placeholder="e.g. Packaging supplies" /></label><label>Category<select name="category"><option>Operations</option><option>Inventory</option><option>Marketing</option><option>Travel</option><option>Other</option></select></label><label>Amount (USD)<input name="amount" type="number" min="0.01" step="0.01" required placeholder="0.00" /></label><div className="modal-actions"><Button type="button" variant="outline" onClick={() => setShowModal(false)}>Cancel</Button><Button type="submit">Add sample expense</Button></div></form></Modal>}
  </>;
}

function CustomersPage() {
  const [customers, setCustomers] = useState(initialCustomers);
  const [query, setQuery] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const filtered = customers.filter((customer) => `${customer.name} ${customer.email} ${customer.company}`.toLowerCase().includes(query.toLowerCase()));
  function addCustomer(event) {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const name = form.elements.name.value;
    setCustomers([{ name, email: form.elements.email.value, company: form.elements.company.value || "Independent", spent: "$0.00", orders: 0, date: "Nov 7, 2026", initials: name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase(), color: "mint", status: "Active" }, ...customers]);
    setShowModal(false);
  }
  return <>
    <PageHeading eyebrow="PEOPLE BEHIND THE BUSINESS" title="Customers" description="Keep the relationships that matter close at hand." action={<Button onClick={() => setShowModal(true)} icon="plus">Add customer</Button>} />
    <div className="metric-grid metric-grid--three"><MetricCard title="All customers" value="248" change="+8.1%" icon="users" variant="blue" /><MetricCard title="Returning customers" value="68%" change="+5.2%" icon="trend" variant="green" /><MetricCard title="New this month" value="24" change="+12.0%" icon="plus" variant="purple" /></div>
    <Card className="table-panel"><PanelTitle title="Customer directory" detail="Sample customer information for the demo workspace" action={<button className="outline-small" onClick={() => downloadCsv("don-prosy-demo-customers.csv", ["Name", "Email", "Company", "Status", "Orders", "Total spent"], filtered.map((customer) => [customer.name, customer.email, customer.company, customer.status, customer.orders, customer.spent]))}><Icon name="download" size={16} /> Export sample list</button>} /><div className="table-toolbar"><label className="table-search"><Icon name="search" size={17} /><input placeholder="Search customers..." value={query} onChange={(event) => setQuery(event.target.value)} /></label><button className="outline-small" onClick={() => setQuery("")}><Icon name="filter" size={16} /> All customers</button></div>
      <div className="table-scroll"><table><thead><tr><th>CUSTOMER</th><th>COMPANY</th><th>STATUS</th><th>ORDERS</th><th>TOTAL SPENT</th><th>LAST ACTIVE</th><th aria-label="Actions" /></tr></thead><tbody>{filtered.map((customer) => <tr key={customer.email}><td><span className="table-person"><Avatar initials={customer.initials} small color={customer.color} /><span><b>{customer.name}</b><span className="table-subtext">{customer.email}</span></span></span></td><td>{customer.company}</td><td><Status value={customer.status} /></td><td>{customer.orders}</td><td><b>{customer.spent}</b></td><td>{customer.date}</td><td><button className="table-more" aria-label={`View ${customer.name}`} onClick={() => setSelectedCustomer(customer)}><Icon name="more" size={18} /></button></td></tr>)}</tbody></table>{filtered.length === 0 && <div className="empty-state">No sample customers match “{query}”.</div>}</div><div className="table-pagination"><span>Showing {filtered.length} of {customers.length} demonstration customers</span><div><button disabled aria-label="Previous page"><Icon name="arrowLeft" size={15} /></button><button className="page-number">1</button><button disabled aria-label="Next page"><Icon name="arrowRight" size={15} /></button></div></div>
    </Card>
    {showModal && <Modal title="Add a demonstration customer" onClose={() => setShowModal(false)}><p className="modal-intro">Adds a temporary example to this customer list only.</p><form className="modal-form" onSubmit={addCustomer}><label>Customer name<input name="name" required placeholder="e.g. Alex Morgan" /></label><label>Email address<input name="email" type="email" required placeholder="alex@example.com" /></label><label>Business or company <span className="field-optional">Optional</span><input name="company" placeholder="Company name" /></label><div className="modal-actions"><Button type="button" variant="outline" onClick={() => setShowModal(false)}>Cancel</Button><Button type="submit">Add sample customer</Button></div></form></Modal>}
    {selectedCustomer && <Modal title="Demonstration customer" onClose={() => setSelectedCustomer(null)}><div className="detail-list"><div><span>Name</span><b>{selectedCustomer.name}</b></div><div><span>Email</span><b>{selectedCustomer.email}</b></div><div><span>Company</span><b>{selectedCustomer.company}</b></div><div><span>Status</span><Status value={selectedCustomer.status} /></div><div><span>Orders</span><b>{selectedCustomer.orders}</b></div><div><span>Total spent</span><b>{selectedCustomer.spent}</b></div></div><p className="modal-intro">Sample customer information only; contact details are illustrative.</p></Modal>}
  </>;
}

function ProductsPage({ inventory = false }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All categories");
  const [showModal, setShowModal] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [products, setProducts] = useState(initialProducts);
  const rows = products.filter((product) => `${product.name} ${product.sku} ${product.category}`.toLowerCase().includes(query.toLowerCase()) && (category === "All categories" || product.category === category) && (!inventory || product.stock < 10));
  const title = inventory ? "Inventory" : "Products";
  return <>
    <PageHeading eyebrow={inventory ? "STOCK AT A GLANCE" : "YOUR CATALOGUE"} title={title} description={inventory ? "Keep an eye on available stock and low-stock items." : "Manage your products and services in one organised place."} action={<Button onClick={() => setShowModal(true)} icon="plus">{inventory ? "Adjust stock" : "Add product"}</Button>} />
    <div className="metric-grid metric-grid--three"><MetricCard title={inventory ? "Units in stock" : "Active products"} value={inventory ? "1,284" : "42"} change="+6.4%" icon="package" variant="blue" /><MetricCard title="Low-stock items" value={inventory ? "3" : "3 items"} change="Needs attention" icon="activity" variant="orange" negative /><MetricCard title={inventory ? "Stock value" : "Categories"} value={inventory ? "$18,640" : "8"} change="Sample estimate" icon="wallet" variant="purple" /></div>
    {inventory && <div className="inventory-alert"><span><Icon name="activity" size={18} /></span><div><b>3 items may need a restock</b><p>Review the sample items below before planning your next order.</p></div><button onClick={() => { setQuery(""); setCategory("All categories"); document.querySelector(".table-panel").scrollIntoView({ behavior: "smooth", block: "start" }); }}>Review items <Icon name="arrowRight" size={14} /></button></div>}
    <Card className="table-panel"><PanelTitle title={inventory ? "Stock levels" : "All products"} detail="Demonstration catalogue · sample inventory values" action={<button className="outline-small" onClick={() => setCategory(category === "All categories" ? "Home & living" : "All categories")}><Icon name="filter" size={15} /> {category}</button>} /><div className="table-toolbar"><label className="table-search"><Icon name="search" size={17} /><input placeholder={`Search ${title.toLowerCase()}...`} value={query} onChange={(event) => setQuery(event.target.value)} /></label><span className="table-result-count">{rows.length} items shown</span></div>
      <div className="table-scroll"><table><thead><tr><th>PRODUCT</th><th>SKU</th><th>CATEGORY</th><th>STOCK LEVEL</th><th>PRICE</th><th>STATUS</th><th aria-label="Actions" /></tr></thead><tbody>{rows.map((product) => <tr key={product.sku}><td><span className="table-person"><Avatar initials={product.initials} small color={product.color} /><b>{product.name}</b></span></td><td>{product.sku}</td><td>{product.category}</td><td><span className="stock-value"><b>{product.stock}</b><span>units</span></span></td><td><b>{product.price}</b></td><td><Status value={product.stock <= 10 ? "Low stock" : "In stock"} /></td><td><button className="table-more" aria-label={`View ${product.name}`} onClick={() => setSelectedProduct(product)}><Icon name="more" size={18} /></button></td></tr>)}</tbody></table>{rows.length === 0 && <div className="empty-state">No sample products found.</div>}</div>
    </Card>
    {showModal && <Modal title={inventory ? "Adjust demonstration stock" : "Add a demonstration product"} onClose={() => setShowModal(false)}><p className="modal-intro">Catalogue updates are for demonstration only and are not saved to a server.</p><form className="modal-form" onSubmit={(event) => { event.preventDefault(); const form = event.currentTarget; if (inventory) { const sku = form.elements.product.value; const quantity = Number(form.elements.number.value); setProducts((current) => current.map((product) => product.sku === sku ? { ...product, stock: quantity } : product)); } else { const name = form.elements.name.value; const amount = Number(form.elements.number.value); setProducts((current) => [...current, { name, sku: `PRD-${String(current.length + 1).padStart(3, "0")}`, category: form.elements.category.value, stock: 0, price: money(amount), initials: name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase(), color: "mint" }]); } setShowModal(false); }}><label>{inventory ? "Product" : "Product name"}{inventory ? <select name="product">{products.map((product) => <option value={product.sku} key={product.sku}>{product.name} · {product.stock} in stock</option>)}</select> : <input name="name" required placeholder="e.g. Market tote" />}</label>{!inventory && <label>Category<select name="category"><option>Home & living</option><option>Accessories</option><option>Stationery</option></select></label>}<label>{inventory ? "New on-hand quantity" : "Unit price (USD)"}<input name="number" type="number" min="0" step={inventory ? "1" : "0.01"} required placeholder="0" /></label><div className="modal-actions"><Button type="button" variant="outline" onClick={() => setShowModal(false)}>Cancel</Button><Button type="submit">{inventory ? "Save stock level" : "Add sample product"}</Button></div></form></Modal>}
    {selectedProduct && <Modal title="Demonstration product" onClose={() => setSelectedProduct(null)}><div className="detail-list"><div><span>Product</span><b>{selectedProduct.name}</b></div><div><span>SKU</span><b>{selectedProduct.sku}</b></div><div><span>Category</span><b>{selectedProduct.category}</b></div><div><span>Stock on hand</span><b>{selectedProduct.stock} units</b></div><div><span>Unit price</span><b>{selectedProduct.price}</b></div></div><p className="modal-intro">Sample catalogue details only; no live product record is connected.</p></Modal>}
  </>;
}

function ReportsPage() {
  const [period, setPeriod] = useState("Last 30 days");
  const [tab, setTab] = useState("Overview");
  return <>
    <PageHeading eyebrow="THE BIGGER PICTURE" title="Reports" description="Explore sample trends and performance summaries for your business." action={<Button variant="outline" icon="download" onClick={() => downloadCsv("don-prosy-demo-report.csv", ["Metric", "Demonstration value"], [["Revenue", "$24,580"], ["Expenses", "$8,420"], ["Estimated profit", "$16,160"]])}>Export sample report</Button>} />
    <div className="report-tabs" role="tablist" aria-label="Report type">{["Overview", "Revenue", "Expenses", "Profit"].map((item) => <button role="tab" aria-selected={tab === item} className={tab === item ? "is-active" : ""} key={item} onClick={() => setTab(item)}>{item}</button>)}</div>
    <div className="metric-grid metric-grid--three"><MetricCard title={tab === "Expenses" ? "Expenses" : "Total revenue"} value={tab === "Expenses" ? "$8,420" : "$24,580"} change="+12.8%" icon="wallet" variant="blue" /><MetricCard title="Gross margin" value="65.7%" change="+2.4%" icon="trend" variant="green" /><MetricCard title="Average order value" value="$132.15" change="+3.1%" icon="activity" variant="purple" /></div>
    <Card className="report-chart-panel"><PanelTitle title={`${tab} performance`} detail="A sample view of the last six months" action={<PeriodSelect value={period} onChange={setPeriod} />} /><LineChart mode={tab === "Revenue" ? "revenue" : "sales"} /><div className="report-summary"><span><i />Sample revenue <b>$24,580</b></span><span><i className="report-summary__expense" />Sample expenses <b>$8,420</b></span><span><i className="report-summary__profit" />Estimated profit <b>$16,160</b></span></div></Card>
    <div className="overview-bottom"><Card><PanelTitle title="Performance highlights" detail="Demonstration insights" /><div className="highlight-list"><div><span className="highlight-number">01</span><p><b>Revenue is growing</b><small>Illustrative 12.8% increase compared with the previous period.</small></p><Icon name="trend" size={18} /></div><div><span className="highlight-number">02</span><p><b>Returning customers are active</b><small>Sample repeat-customer rate is 68% for this view.</small></p><Icon name="users" size={18} /></div><div><span className="highlight-number">03</span><p><b>Keep an eye on stock</b><small>Three sample products are below their reorder threshold.</small></p><Icon name="package" size={18} /></div></div></Card><Card><PanelTitle title="Expense mix" detail="Illustrative category breakdown" /><DonutChart /></Card></div>
  </>;
}

function AssistantPage() {
  const suggestions = ["What changed in my revenue?", "Which products need attention?", "Summarise this month’s expenses"];
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  function send(text = input) {
    const question = text.trim();
    if (!question) return;
    setMessages([...messages, { role: "user", text: question }, { role: "assistant", text: "This is a preview of the Don Prosy text assistant. In a future stage, it will be able to analyse authorised business records and help explain trends. No AI service or real business data is connected in this demo." }]);
    setInput("");
  }
  return <>
    <PageHeading eyebrow="A THOUGHTFUL BUSINESS PARTNER" title="AI assistant" description="A text-based helper designed to make business insights easier to explore." action={<span className="coming-soon-badge"><Icon name="sparkles" size={15} />Preview</span>} />
    <div className="assistant-disclaimer"><Icon name="info" size={18} /><span><b>Interface preview only.</b> This assistant is not connected to an AI service or live business records. Voice AI is not part of the initial release.</span></div>
    <Card className="assistant-card">
      <div className="assistant-heading"><span className="assistant-orb"><Icon name="sparkles" size={22} /></span><div><b>Your business, a little clearer.</b><span>Ask questions, explore patterns, find your next step.</span></div><span className="assistant-preview-tag">DEMO</span></div>
      <div className="chat-area">
        {messages.length === 0 ? <div className="chat-welcome"><span className="chat-spark"><Icon name="sparkles" size={24} /></span><h2>What would you like to understand?</h2><p>Choose a suggested question to preview how a business conversation might feel.</p><div className="suggestion-list">{suggestions.map((suggestion) => <button key={suggestion} onClick={() => send(suggestion)}>{suggestion}<Icon name="arrowRight" size={15} /></button>)}</div></div> : <div className="chat-messages" aria-live="polite">{messages.map((message, index) => <div className={`chat-message chat-message--${message.role}`} key={`${message.role}-${index}`}><span className="chat-message__avatar">{message.role === "assistant" ? <Icon name="sparkles" size={16} /> : "JD"}</span><div><b>{message.role === "assistant" ? "Don Prosy assistant · preview" : "You"}</b><p>{message.text}</p></div></div>)}</div>}
      </div>
      <form className="chat-input" onSubmit={(event) => { event.preventDefault(); send(); }}><input aria-label="Message the demonstration assistant" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a question about your business..." /><button disabled={!input.trim()} aria-label="Send message"><Icon name="arrowRight" size={19} /></button></form>
      <p className="chat-footnote"><Icon name="shield" size={13} /> Future responses will use only business information you are authorised to access.</p>
    </Card>
  </>;
}

function SettingsPage() {
  const [tab, setTab] = useState("Business profile");
  const [saved, setSaved] = useState(false);
  const tabs = ["Business profile", "Preferences", "Notifications", "Security", "Subscription"];
  return <>
    <PageHeading eyebrow="MAKE IT YOURS" title="Settings" description="Manage your demonstration business and account preferences." />
    <div className="settings-layout">
      <Card className="settings-nav"><div className="settings-business"><span className="business-switcher__mark">N</span><span><b>Northstar Studio</b><small>Demo workspace</small></span></div>{tabs.map((item, index) => <button key={item} className={tab === item ? "is-active" : ""} onClick={() => { setTab(item); setSaved(false); }}><Icon name={["briefcase", "settings", "bell", "lock", "tag"][index]} size={17} />{item}</button>)}</Card>
      <Card className="settings-content"><div className="settings-title"><div><h2>{tab}</h2><p>{tab === "Business profile" ? "The basic details of your demo workspace." : `Manage your ${tab.toLowerCase()} preferences for this preview.`}</p></div><span className="coming-soon-badge">DEMO SETTINGS</span></div>
        {tab === "Business profile" && <form className="settings-form" onSubmit={(event) => { event.preventDefault(); setSaved(true); }}><label>Business name<input defaultValue="Northstar Studio" /></label><label>Business type<select defaultValue="Retail"><option>Retail</option><option>Professional services</option><option>Food & beverage</option><option>Other</option></select></label><label>Business email<input type="email" defaultValue="hello@northstar.example" /></label><label>Currency<select defaultValue="USD"><option>USD — US Dollar</option><option>GBP — British Pound</option><option>EUR — Euro</option><option>GHS — Ghanaian Cedi</option><option>NGN — Nigerian Naira</option></select></label><div className="settings-save"><span>{saved ? "Demo preferences updated in this view." : "Changes are not saved to a server."}</span><Button type="submit">Save changes</Button></div></form>}
        {tab === "Preferences" && <div className="preference-list"><label><span><b>Default reporting period</b><small>Choose the first period shown in reports.</small></span><select><option>Last 30 days</option><option>Last 7 days</option><option>This year</option></select></label><label><span><b>Display currency</b><small>Sample figures in the demo workspace.</small></span><select><option>USD ($)</option><option>GBP (£)</option><option>EUR (€)</option></select></label></div>}
        {tab === "Notifications" && <div className="preference-list">{["Low stock reminders", "Weekly business summary", "Product updates"].map((item, index) => <label key={item}><span><b>{item}</b><small>Example preference. Notifications are not sent.</small></span><input type="checkbox" defaultChecked={index !== 2} /></label>)}</div>}
        {tab === "Security" && <div className="settings-info"><span className="settings-info__icon"><Icon name="shield" /></span><h3>Security controls are coming</h3><p>Account security, password management, and business access controls will be implemented in a future development stage. This demonstration does not create or authenticate accounts.</p><Button variant="outline" onClick={() => setSaved(true)}>Review security plan</Button>{saved && <small>See the project security plan for the intended protections.</small>}</div>}
        {tab === "Subscription" && <div className="subscription-preview"><span className="plan-symbol plan-symbol--1"><Icon name="layers" size={20} /></span><div><small>CURRENT DEMONSTRATION PLAN</small><h3>Starter preview</h3><p>No billing or subscription is active. Plans and prices will be confirmed before launch.</p></div><Button variant="outline" onClick={() => setSaved(true)}>View planned options</Button>{saved && <small>Starter, Growth, and Business tiers are planned.</small>}</div>}
      </Card>
    </div>
  </>;
}

function DashboardPage({ page, navigate }) {
  const normalized = useMemo(() => page.toLowerCase(), [page]);
  if (normalized === "overview") return <Overview navigate={navigate} />;
  if (normalized === "sales") return <SalesPage navigate={navigate} />;
  if (normalized === "expenses") return <ExpensesPage />;
  if (normalized === "customers") return <CustomersPage />;
  if (normalized === "products") return <ProductsPage />;
  if (normalized === "inventory") return <ProductsPage inventory />;
  if (normalized === "reports") return <ReportsPage />;
  if (normalized === "assistant") return <AssistantPage />;
  if (normalized === "settings") return <SettingsPage />;
  return <Overview navigate={navigate} />;
}

export default DashboardPage;
