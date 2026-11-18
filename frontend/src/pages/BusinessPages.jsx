import { useEffect, useState } from "react";
import { customerApi } from "../services/customerApi.js";
import { businessApi } from "../services/businessApi.js";
import { PageHeading } from "../components/UI.jsx";

const money = (value) => new Intl.NumberFormat("en-NG", {
  style: "currency",
  currency: "NGN",
  minimumFractionDigits: 2,
}).format(Number(value || 0));

const dateLabel = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("en-NG", { dateStyle: "medium" }).format(date);
};

function useBusinessData(load, dependencies) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    load().then((result) => {
      if (active) setData(result);
    }).catch((failure) => {
      if (active) setError(failure.message || "The information could not be loaded.");
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, [...dependencies, revision]);

  return { data, loading, error, refresh: () => setRevision((value) => value + 1) };
}

function LoadState({ loading, error, children }) {
  if (loading) return <div className="empty-state" role="status">Loading business records…</div>;
  if (error) return <div className="form-feedback form-feedback--error" role="alert">{error}</div>;
  return children;
}

function Panel({ title, description, children }) {
  return (
    <section className="panel management-panel">
      <div className="panel-title"><div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>
      {children}
    </section>
  );
}

function CustomerPage({ businessId, businessRole }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingId, setEditingId] = useState("");
  const [viewingCustomer, setViewingCustomer] = useState(null);
  const [viewingCustomerLoading, setViewingCustomerLoading] = useState(false);
  const [address, setAddress] = useState("");
  const [notes, setNotes] = useState("");
  const perPage = 25;
  const customers = useBusinessData(
    () => customerApi.list(businessId, { page, perPage, query }),
    [businessId, page, query],
  );
  const canDeleteCustomers = ["owner", "manager"].includes(businessRole);
  const customerCount = customers.data?.pagination?.total || 0;
  const totalPages = Math.max(customers.data?.pagination?.pages || 1, 1);

  useEffect(() => {
    setPage(1);
    setQuery("");
    setEditingId("");
    setViewingCustomer(null);
    setName("");
    setPhone("");
    setEmail("");
    setAddress("");
    setNotes("");
  }, [businessId]);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    setNotice("");
    try {
      if (editingId) {
        await customerApi.update(businessId, editingId, {
          full_name: name, phone, email: email || null, address: address || null, notes: notes || null,
        });
      } else {
        await customerApi.create(businessId, {
          full_name: name, phone, email: email || null, address: address || null, notes: notes || null,
        });
      }
      setName("");
      setPhone("");
      setEmail("");
      setAddress("");
      setNotes("");
      setEditingId("");
      setViewingCustomer(null);
      setNotice(editingId ? "Customer updated." : "Customer added.");
      if (!editingId) setPage(1);
      customers.refresh();
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeCustomer(customer) {
    if (!window.confirm(`Delete ${customer.full_name}?`)) return;
    setFormError("");
    setNotice("");
    try {
      await customerApi.remove(businessId, customer.id);
      if (viewingCustomer?.id === customer.id) setViewingCustomer(null);
      setNotice("Customer deleted.");
      if (page > 1 && customers.data?.customers?.length === 1) setPage(page - 1);
      else customers.refresh();
    } catch (error) {
      setFormError(error.message);
    }
  }

  async function viewCustomer(customer) {
    setViewingCustomer(null);
    setViewingCustomerLoading(true);
    setFormError("");
    try {
      const payload = await customerApi.get(businessId, customer.id);
      setViewingCustomer(payload.customer);
    } catch (error) {
      setFormError(error.message);
    } finally {
      setViewingCustomerLoading(false);
    }
  }

  return (
    <>
      <PageHeading eyebrow="CUSTOMERS" title="Customers" description="Keep customer contact details and purchase balances together." />
      <Panel
        title={editingId ? "Edit customer" : "Add a customer"}
        description={editingId ? "Update this customer's contact details." : "Customer records belong to this business workspace."}
      >
        <form className="customer-form" onSubmit={submit}>
          <div className="customer-form__fields">
            <label><span>Full name</span><input required maxLength="160" value={name} onChange={(event) => setName(event.target.value)} /></label>
            <label><span>Phone</span><input required maxLength="32" value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
            <label><span>Email <span className="field-optional">(optional)</span></span><input type="email" maxLength="254" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label><span>Address <span className="field-optional">(optional)</span></span><input maxLength="500" value={address} onChange={(event) => setAddress(event.target.value)} /></label>
            <label><span>Notes <span className="field-optional">(optional)</span></span><input maxLength="2000" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          </div>
          <div className="customer-form__actions">
              <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Add customer"}</button>
            {editingId && <button type="button" className="quiet-button" onClick={() => { setEditingId(""); setName(""); setPhone(""); setEmail(""); setAddress(""); setNotes(""); }}>Cancel edit</button>}
          </div>
        </form>
        {formError && <p className="form-feedback form-feedback--error" role="alert">{formError}</p>}
        {notice && <p className="form-feedback" role="status">{notice}</p>}
      </Panel>
      <Panel title="Customer directory" description={`${customerCount} ${customerCount === 1 ? "customer" : "customers"}`}>
        <div className="management-toolbar">
          <label><span>Search customers</span><input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Name, phone, or email" /></label>
        </div>
        <LoadState loading={customers.loading} error={customers.error}>
          {customers.data?.customers?.length ? (
            <>
              <div className="table-scroll">
                <table className="customer-table">
                  <thead><tr><th scope="col">NAME</th><th scope="col">PHONE</th><th scope="col">EMAIL</th><th scope="col">SALES</th><th scope="col">OUTSTANDING</th><th scope="col">ACTIONS</th></tr></thead>
                  <tbody>{customers.data.customers.map((customer) => (
                    <tr key={customer.id}>
                      <td>{customer.full_name}</td><td>{customer.phone}</td><td>{customer.email || "—"}</td>
                      <td>{money(customer.total_purchases)}</td><td>{money(customer.outstanding_balance)}</td>
                      <td>
                        <div className="customer-actions">
                          <button type="button" className="quiet-button" onClick={() => viewCustomer(customer)}>View</button>
                          <button type="button" className="quiet-button" onClick={() => { setViewingCustomer(null); setEditingId(customer.id); setName(customer.full_name); setPhone(customer.phone); setEmail(customer.email || ""); setAddress(customer.address || ""); setNotes(customer.notes || ""); }}>Edit</button>
                          {canDeleteCustomers && <button type="button" className="quiet-button customer-actions__delete" onClick={() => removeCustomer(customer)}>Delete</button>}
                        </div>
                      </td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              <div className="customer-list-footer">
                <span>Showing {(page - 1) * perPage + 1}–{Math.min((page - 1) * perPage + customers.data.customers.length, customerCount)} of {customerCount}</span>
                {totalPages > 1 && <nav className="customer-pagination" aria-label="Customer pages">
                  <button type="button" className="quiet-button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button>
                  <span>Page {page} of {totalPages}</span>
                  <button type="button" className="quiet-button" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>Next</button>
                </nav>}
              </div>
            </>
          ) : (
            <div className="empty-state">
              {query ? "No customers match your search. Try another name, phone, or email." : "No customers yet. Add a customer above to keep their details and balances together."}
            </div>
          )}
        </LoadState>
      </Panel>
      {viewingCustomerLoading && <div className="empty-state" role="status">Loading customer details…</div>}
      {viewingCustomer?.business_id === businessId && <Panel title={viewingCustomer.full_name} description="Customer contact details and purchase history.">
        <dl className="customer-detail-list">
          <div><dt>Phone</dt><dd>{viewingCustomer.phone}</dd></div>
          <div><dt>Email</dt><dd>{viewingCustomer.email || "—"}</dd></div>
          <div><dt>Address</dt><dd>{viewingCustomer.address || "—"}</dd></div>
          <div><dt>Notes</dt><dd>{viewingCustomer.notes || "—"}</dd></div>
          <div><dt>Total purchases</dt><dd>{money(viewingCustomer.total_purchases)}</dd></div>
          <div><dt>Amount paid</dt><dd>{money(viewingCustomer.amount_paid)}</dd></div>
          <div><dt>Refunds</dt><dd>{money(viewingCustomer.refund_total)}</dd></div>
          <div><dt>Outstanding balance</dt><dd>{money(viewingCustomer.outstanding_balance)}</dd></div>
        </dl>
        <h3 className="management-subheading">Purchase history</h3>
        <div className="table-scroll"><table><thead><tr><th>REFERENCE</th><th>DATE</th><th>STATUS</th><th>AMOUNT</th><th>OUTSTANDING</th></tr></thead>
          <tbody>{(viewingCustomer.purchase_history || []).map((sale) => <tr key={sale.id}><td>{sale.id}</td><td>{dateLabel(sale.date)}</td><td>{sale.status}</td><td>{money(sale.amount)}</td><td>{money(sale.outstanding_balance)}</td></tr>)}</tbody>
        </table></div>
        {!viewingCustomer.purchase_history?.length && <div className="empty-state">No purchases recorded for this customer.</div>}
      </Panel>}
    </>
  );
}

function ProductPage({ businessId, businessRole }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState("newest");
  const [viewingProduct, setViewingProduct] = useState(null);
  const [viewingMovements, setViewingMovements] = useState([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [type, setType] = useState("product");
  const [price, setPrice] = useState("");
  const [cost, setCost] = useState("");
  const [quantity, setQuantity] = useState("0");
  const [reorder, setReorder] = useState("0");
  const [sku, setSku] = useState("");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const records = useBusinessData(
    () => businessApi.getProducts(businessId, { page, per_page: 25, q: query, sort }),
    [businessId, page, query, sort],
  );
  const totalPages = Math.max(records.data?.pagination?.pages || 1, 1);

  useEffect(() => {
    setPage(1);
    setQuery("");
    setEditingId("");
    setName("");
    setCategory("");
    setPrice("");
    setCost("");
    setQuantity("0");
    setReorder("0");
    setSku("");
    setDescription("");
  }, [businessId]);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        name, category, type, sku: sku || null, description: description || null,
        selling_price: price, purchase_cost: cost || "0",
      };
      if (!editingId) {
        payload.quantity_on_hand = type === "product" ? quantity : "0";
        payload.reorder_level = type === "product" ? reorder : "0";
      }
      if (editingId) await businessApi.updateProduct(businessId, editingId, payload);
      else await businessApi.createProduct(businessId, payload);
      setName("");
      setCategory("");
      setPrice("");
      setCost("");
      setQuantity("0");
      setReorder("0");
      setSku("");
      setDescription("");
      setEditingId("");
      records.refresh();
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function archive(product) {
    if (!window.confirm(`Archive ${product.name}? It will no longer be available for new sales.`)) return;
    setFormError("");
    try {
      await businessApi.archiveProduct(businessId, product.id);
      records.refresh();
    } catch (error) {
      setFormError(error.message);
    }
  }

  async function viewProduct(product) {
    setViewingProduct(null);
    setViewingMovements([]);
    try {
      const payload = await businessApi.getProduct(businessId, product.id);
      setViewingProduct(payload.product);
      setViewingMovements(payload.movements || []);
    } catch (error) {
      setFormError(error.message);
    }
  }

  function edit(product) {
    setEditingId(product.id);
    setName(product.name);
    setCategory(product.category);
    setType(product.type);
    setPrice(product.selling_price);
    setCost(product.purchase_cost);
    setSku(product.sku || "");
    setDescription(product.description || "");
  }

  return (
    <>
      <PageHeading eyebrow="CATALOGUE" title="Products & services" description="Manage selling prices, costs, and stock thresholds." />
      <Panel title="Add catalogue item">
        <form className="management-form" onSubmit={submit}>
          <label><span>Name</span><input required maxLength="160" value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label><span>Category</span><input required maxLength="80" value={category} onChange={(event) => setCategory(event.target.value)} /></label>
          <label><span>Type</span><select value={type} onChange={(event) => setType(event.target.value)}><option value="product">Physical product</option><option value="service">Service</option></select></label>
          <label><span>Selling price (NGN)</span><input required type="number" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} /></label>
          <label><span>Purchase cost (NGN)</span><input type="number" min="0" step="0.01" value={cost} onChange={(event) => setCost(event.target.value)} /></label>
          <label><span>SKU (optional)</span><input maxLength="64" value={sku} onChange={(event) => setSku(event.target.value)} /></label>
          <label><span>Description (optional)</span><input maxLength="2000" value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          {!editingId && type === "product" && <>
            <label><span>Opening stock</span><input type="number" min="0" step="0.001" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
            <label><span>Reorder level</span><input type="number" min="0" step="0.001" value={reorder} onChange={(event) => setReorder(event.target.value)} /></label>
          </>}
          {businessRole !== "staff" && <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Add item"}</button>}
          {editingId && <button type="button" className="quiet-button" onClick={() => { setEditingId(""); setName(""); setCategory(""); setPrice(""); setCost(""); setSku(""); setDescription(""); }}>Cancel edit</button>}
        </form>
        {businessRole === "staff" && <p>Product changes require an owner or manager.</p>}
        {formError && <p className="form-feedback form-feedback--error" role="alert">{formError}</p>}
      </Panel>
      <Panel title="Product catalogue">
        <div className="management-toolbar">
          <label><span>Search products</span><input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Name, category, or SKU" /></label>
          <label><span>Sort</span><select value={sort} onChange={(event) => { setSort(event.target.value); setPage(1); }}><option value="newest">Newest</option><option value="name">Name A-Z</option><option value="price_low">Price: low to high</option><option value="price_high">Price: high to low</option><option value="stock_low">Stock: low to high</option></select></label>
        </div>
        <LoadState loading={records.loading} error={records.error}>
          <div className="table-scroll"><table>
            <thead><tr><th>ITEM</th><th>TYPE</th><th>CATEGORY</th><th>PRICE</th><th>COST</th><th>IN STOCK</th><th>REORDER</th><th>ACTIONS</th></tr></thead>
            <tbody>{(records.data?.products || []).map((product) => (
              <tr key={product.id}><td>{product.name}</td><td>{product.type}</td><td>{product.category}</td><td>{money(product.selling_price)}</td><td>{money(product.purchase_cost)}</td><td>{product.type === "product" ? product.quantity_on_hand : "—"}</td><td>{product.type === "product" ? product.reorder_level : "—"}</td><td><button type="button" className="quiet-button" onClick={() => viewProduct(product)}>View</button>{businessRole !== "staff" && <><button type="button" className="quiet-button" onClick={() => edit(product)}>Edit</button><button type="button" className="quiet-button" onClick={() => archive(product)}>Archive</button></>}</td></tr>
            ))}</tbody>
          </table></div>
          {!records.data?.products?.length && <div className="empty-state">No catalogue items found.</div>}
          {records.data?.products?.length > 0 && <div className="customer-list-footer">
            <span>Showing {(page - 1) * 25 + 1}–{Math.min((page - 1) * 25 + records.data.products.length, records.data.pagination?.total || 0)} of {records.data.pagination?.total || 0}</span>
            {totalPages > 1 && <nav className="customer-pagination" aria-label="Product pages">
              <button type="button" className="quiet-button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button>
              <span>Page {page} of {totalPages}</span>
              <button type="button" className="quiet-button" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>Next</button>
            </nav>}
          </div>}
        </LoadState>
      </Panel>
      {viewingProduct && <Panel title={viewingProduct.name} description={viewingProduct.description || "Product and inventory details."}>
        <dl className="customer-detail-list">
          <div><dt>Category</dt><dd>{viewingProduct.category}</dd></div>
          <div><dt>Type</dt><dd>{viewingProduct.type}</dd></div>
          <div><dt>SKU</dt><dd>{viewingProduct.sku || "—"}</dd></div>
          <div><dt>Selling price</dt><dd>{money(viewingProduct.selling_price)}</dd></div>
          <div><dt>Purchase cost</dt><dd>{money(viewingProduct.purchase_cost)}</dd></div>
          <div><dt>Stock quantity</dt><dd>{viewingProduct.type === "product" ? `${viewingProduct.quantity_on_hand} ${viewingProduct.stock_unit || "unit"}` : "Not applicable"}</dd></div>
          <div><dt>Reorder level</dt><dd>{viewingProduct.type === "product" ? viewingProduct.reorder_level : "Not applicable"}</dd></div>
          <div><dt>Stock valuation</dt><dd>{viewingProduct.type === "product" ? money(Number(viewingProduct.quantity_on_hand || 0) * Number(viewingProduct.purchase_cost || 0)) : "Not applicable"}</dd></div>
        </dl>
        {viewingProduct.type === "product" && <>
          <h3 className="management-subheading">Recent stock movements</h3>
          <div className="table-scroll"><table><thead><tr><th>DATE</th><th>CHANGE</th><th>AFTER</th><th>REASON</th><th>NOTE</th></tr></thead>
            <tbody>{viewingMovements.map((movement) => <tr key={movement.id}><td>{dateLabel(movement.created_at)}</td><td>{movement.delta_quantity}</td><td>{movement.quantity_after}</td><td>{movement.reason}</td><td>{movement.note || "—"}</td></tr>)}</tbody>
          </table></div>
          {!viewingMovements.length && <div className="empty-state">No stock movements recorded yet.</div>}
        </>}
      </Panel>}
    </>
  );
}

function InventoryPage({ businessId, businessRole }) {
  const [productId, setProductId] = useState("");
  const [productLookup, setProductLookup] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("stock_count");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const products = useBusinessData(
    () => businessApi.getProducts(businessId, { page: 1, per_page: 50, type: "product", q: productLookup }),
    [businessId, productLookup],
  );
  const inventoryRecords = useBusinessData(
    () => businessApi.getProducts(businessId, { page, per_page: 25, type: "product", q: query }),
    [businessId, page, query],
  );
  const inventoryRows = inventoryRecords.data?.products || [];
  const inventoryPagination = inventoryRecords.data?.pagination || {};
  const totalPages = Math.max(inventoryPagination.pages || 1, 1);

  useEffect(() => {
    setProductId("");
    setSelectedProduct(null);
    setProductLookup("");
    setQuery("");
    setPage(1);
  }, [businessId]);

  async function loadHistory(id) {
    setProductId(id);
    setFormError("");
    if (!id) {
      setSelectedProduct(null);
      return;
    }
    try {
      const payload = await businessApi.getProduct(businessId, id);
      setSelectedProduct(payload.product);
    } catch (error) {
      setFormError(error.message);
    }
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      await businessApi.adjustStock(businessId, productId, { delta_quantity: delta, reason, note: note || undefined });
      setDelta("");
      setNote("");
      await Promise.all([loadHistory(productId), products.refresh(), inventoryRecords.refresh()]);
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeading eyebrow="INVENTORY" title="Stock management" description="Review available quantities, reorder risks, and the movement ledger." />
      <Panel title="Stock adjustment" description="Record received or counted stock with a reason for the audit trail.">
        {businessRole === "staff" ? <p>Stock adjustments require an owner or manager.</p> : (
          <form className="management-form" onSubmit={submit}>
            <label><span>Find product</span><input type="search" value={productLookup} onChange={(event) => setProductLookup(event.target.value)} placeholder="Search by name, category, or SKU" /></label>
            <label><span>Product</span><select required value={productId} onChange={(event) => loadHistory(event.target.value)}><option value="">Select a product</option>{(products.data?.products || []).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <label><span>Quantity change (+ or −)</span><input required type="number" step="0.001" value={delta} onChange={(event) => setDelta(event.target.value)} /></label>
            <label><span>Reason</span><select value={reason} onChange={(event) => setReason(event.target.value)}><option value="stock_count">Stock count</option><option value="purchase">Stock received</option><option value="damage">Damaged stock</option><option value="correction">Correction</option></select></label>
            <label><span>Note (optional)</span><input maxLength="500" value={note} onChange={(event) => setNote(event.target.value)} /></label>
            <button type="submit" className="primary-button" disabled={saving || !productId}>{saving ? "Saving…" : "Record movement"}</button>
          </form>
        )}
        {formError && <p className="form-feedback form-feedback--error" role="alert">{formError}</p>}
      </Panel>
      <Panel title="Current stock" description={`${inventoryPagination.total || 0} physical product${inventoryPagination.total === 1 ? "" : "s"} tracked`}>
        <div className="management-toolbar"><label><span>Search inventory</span><input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Name, category, or SKU" /></label></div>
        <LoadState loading={inventoryRecords.loading} error={inventoryRecords.error}>
          <div className="table-scroll"><table><thead><tr><th>PRODUCT</th><th>QUANTITY</th><th>REORDER LEVEL</th><th>STATUS</th></tr></thead>
            <tbody>{inventoryRows.map((item) => {
              const isOut = Number(item.quantity_on_hand) <= 0;
              const isLow = Number(item.reorder_level) > 0 && Number(item.quantity_on_hand) <= Number(item.reorder_level);
              return <tr key={item.id}><td>{item.name}</td><td>{item.quantity_on_hand} {item.stock_unit}</td><td>{item.reorder_level}</td><td>{isOut ? "Out of stock" : isLow ? "Reorder" : "In stock"}</td></tr>;
            })}</tbody>
          </table></div>
          {!inventoryRows.length && <div className="empty-state">No physical products match this search.</div>}
          {inventoryRows.length > 0 && totalPages > 1 && <div className="customer-list-footer">
            <span>Page {page} of {totalPages}</span>
            <nav className="customer-pagination" aria-label="Inventory pages">
              <button type="button" className="quiet-button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button>
              <button type="button" className="quiet-button" disabled={page >= totalPages} onClick={() => setPage((current) => current + 1)}>Next</button>
            </nav>
          </div>}
        </LoadState>
      </Panel>
      {selectedProduct?.business_id === businessId && <Panel title={`Movement history · ${selectedProduct.name}`}>
        <div className="table-scroll"><table><thead><tr><th>DATE</th><th>CHANGE</th><th>AFTER</th><th>REASON</th><th>NOTE</th></tr></thead>
          <tbody>{(selectedProduct.movements || []).map((movement) => <tr key={movement.id}><td>{dateLabel(movement.created_at)}</td><td>{movement.delta_quantity}</td><td>{movement.quantity_after}</td><td>{movement.reason}</td><td>{movement.note || "—"}</td></tr>)}</tbody>
        </table></div>
      </Panel>}
    </>
  );
}

function ExpensesPage({ businessId, businessRole, range, onRangeChange }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [startDate, setStartDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState("cash");
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [editingId, setEditingId] = useState("");
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const records = useBusinessData(
    () => businessApi.getExpenses(businessId, {
      q: query, page, per_page: 25, range,
      ...(range === "custom" ? { start_date: startDate, end_date: endDate } : {}),
    }),
    [businessId, range, page, query, startDate, endDate],
  );

  useEffect(() => {
    setQuery("");
    setPage(1);
    setEditingId("");
    setCategory("");
    setDescription("");
    setAmount("");
    setNotes("");
  }, [businessId]);

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError("");
    try {
      const payload = {
        category, description, amount, payment_method: method, expense_date: expenseDate, notes,
      };
      if (editingId) await businessApi.updateExpense(businessId, editingId, payload);
      else await businessApi.createExpense(businessId, payload);
      setCategory("");
      setDescription("");
      setAmount("");
      setNotes("");
      setEditingId("");
      setPage(1);
      records.refresh();
    } catch (error) {
      setFormError(error.message);
    } finally {
      setSaving(false);
    }
  }

  async function removeExpense(expense) {
    if (!window.confirm(`Delete expense “${expense.description}”?`)) return;
    setFormError("");
    try {
      await businessApi.deleteExpense(businessId, expense.id);
      if (page > 1 && records.data?.expenses?.length === 1) setPage(page - 1);
      else records.refresh();
    } catch (error) {
      setFormError(error.message);
    }
  }

  return (
    <>
      <PageHeading eyebrow="EXPENSES" title="Expenses" description="Record and review operating costs for the active business." />
      <Panel title="Record an expense">
        <form className="management-form" onSubmit={submit}>
          <label><span>Category</span><input required maxLength="80" value={category} onChange={(event) => setCategory(event.target.value)} placeholder="e.g. Transport" /></label>
          <label><span>Description</span><input required maxLength="255" value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          <label><span>Amount (NGN)</span><input required type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
          <label><span>Payment method</span><select value={method} onChange={(event) => setMethod(event.target.value)}><option value="cash">Cash</option><option value="bank_transfer">Bank transfer</option><option value="pos">POS</option><option value="other">Other</option></select></label>
          <label><span>Date</span><input required type="date" value={expenseDate} onChange={(event) => setExpenseDate(event.target.value)} /></label>
          <label><span>Notes (optional)</span><input maxLength="2000" value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          {(businessRole !== "staff" || !editingId) && <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : "Save expense"}</button>}
          {editingId && <button type="button" className="quiet-button" onClick={() => { setEditingId(""); setCategory(""); setDescription(""); setAmount(""); setNotes(""); }}>Cancel edit</button>}
        </form>
        {businessRole === "staff" && editingId && <p>Expense changes require an owner or manager.</p>}
        {formError && <p className="form-feedback form-feedback--error" role="alert">{formError}</p>}
      </Panel>
      <Panel title="Expense history">
        <div className="management-toolbar">
          <label><span>Search expenses</span><input type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Description or category" /></label>
          <label><span>Period</span><select value={range} onChange={(event) => { onRangeChange(event.target.value); setPage(1); }}><option value="today">Today</option><option value="this_week">This week</option><option value="this_month">This month</option><option value="this_year">This year</option><option value="custom">Custom dates</option></select></label>
          {range === "custom" && <>
            <label><span>From</span><input type="date" value={startDate} onChange={(event) => { setStartDate(event.target.value); setPage(1); }} /></label>
            <label><span>To</span><input type="date" value={endDate} onChange={(event) => { setEndDate(event.target.value); setPage(1); }} /></label>
          </>}
        </div>
        <LoadState loading={records.loading} error={records.error}>
          <div className="table-scroll"><table><thead><tr><th>CATEGORY</th><th>DESCRIPTION</th><th>DATE</th><th>AMOUNT</th>{businessRole !== "staff" && <th>ACTIONS</th>}</tr></thead>
            <tbody>{(records.data?.expenses || []).map((item) => <tr key={item.id}><td>{item.category}</td><td>{item.description}</td><td>{dateLabel(item.expense_date)}</td><td>{money(item.amount)}</td>{businessRole !== "staff" && <td><button type="button" className="quiet-button" onClick={() => { setEditingId(item.id); setCategory(item.category); setDescription(item.description); setAmount(item.amount); setMethod(item.payment_method || "cash"); setExpenseDate((item.expense_date || "").slice(0, 10)); setNotes(item.notes || ""); }}>Edit</button><button type="button" className="quiet-button" onClick={() => removeExpense(item)}>Delete</button></td>}</tr>)}</tbody>
          </table></div>
          {!records.data?.expenses?.length && <div className="empty-state">No expenses recorded for this filter.</div>}
          {records.data?.expenses?.length > 0 && (records.data.pagination?.pages || 0) > 1 && <div className="customer-list-footer">
            <span>Showing {(page - 1) * 25 + 1}–{Math.min((page - 1) * 25 + records.data.expenses.length, records.data.pagination.total)} of {records.data.pagination.total}</span>
            <nav className="customer-pagination" aria-label="Expense pages">
              <button type="button" className="quiet-button" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>Previous</button>
              <span>Page {page} of {records.data.pagination.pages}</span>
              <button type="button" className="quiet-button" disabled={page >= records.data.pagination.pages} onClick={() => setPage((current) => current + 1)}>Next</button>
            </nav>
          </div>}
        </LoadState>
      </Panel>
    </>
  );
}

const reportDefinitions = {
  sales: { label: "Sales", columns: [["id", "REFERENCE"], ["customer", "CUSTOMER"], ["amount", "AMOUNT"], ["status", "STATUS"], ["date", "DATE"]] },
  expenses: { label: "Expenses", columns: [["category", "CATEGORY"], ["description", "DESCRIPTION"], ["amount", "AMOUNT"], ["date", "DATE"]] },
  inventory: { label: "Inventory", columns: [["name", "PRODUCT"], ["quantity_on_hand", "IN STOCK"], ["reorder_level", "REORDER LEVEL"], ["category", "CATEGORY"]] },
  customers: { label: "Customers", columns: [["name", "CUSTOMER"], ["phone", "PHONE"], ["total_purchases", "TOTAL SALES"], ["outstanding_balance", "OUTSTANDING"]] },
  payments: { label: "Payments", columns: [["id", "REFERENCE"], ["customer", "CUSTOMER"], ["amount", "AMOUNT"], ["method", "METHOD"], ["direction", "DIRECTION"], ["date", "DATE"]] },
  receivables: { label: "Receivables", columns: [["id", "SALE"], ["customer", "CUSTOMER"], ["amount", "OUTSTANDING"], ["status", "STATUS"], ["date", "DATE"]] },
  product_performance: { label: "Product performance", columns: [["name", "PRODUCT"], ["units_sold", "UNITS SOLD"], ["revenue", "REVENUE"]] },
  profit_loss: { label: "Profit & loss", columns: [["metric", "METRIC"], ["amount", "AMOUNT"]] },
};

function reportValue(key, value) {
  if (["amount", "total_purchases", "outstanding_balance", "revenue"].includes(key)) return money(value);
  if (key === "date") return dateLabel(value);
  return value ?? "—";
}

function ReportsPage({ businessId }) {
  const [type, setType] = useState("sales");
  const [range, setRange] = useState("this_month");
  const [startDate, setStartDate] = useState(new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10));
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));
  const definition = reportDefinitions[type];
  const params = range === "custom" ? { start_date: startDate, end_date: endDate } : {};
  const records = useBusinessData(
    () => businessApi.getReports(businessId, type, range, params),
    [businessId, type, range, startDate, endDate],
  );

  async function exportCsv() {
    try {
      setExportError("");
      const content = await businessApi.exportCsv(businessId, type, range, params);
      const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `${type}_report.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      recordsError(error.message);
    }
  }

  function printReport() {
    const printWindow = window.open("", "_blank", "width=900,height=700");
    if (!printWindow) {
      setExportError("Allow pop-ups to print a report.");
      return;
    }
    const columns = definition.columns;
    const rows = (records.data?.items || []).map((item) => `
      <tr>${columns.map(([key]) => `<td>${String(reportValue(key, item[key]) ?? "—").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]))}</td>`).join("")}</tr>
    `).join("");
    printWindow.document.write(`<!doctype html><html><head><title>${definition.label} report</title><style>@page{margin:12mm}body{font-family:Arial,sans-serif;color:#172033;padding:20px}h1{font-size:20px}table{width:100%;border-collapse:collapse}th,td{border:1px solid #dfe5ee;padding:8px;font-size:11px;text-align:left}th{background:#f3f6fa}button{display:none}@media print{button{display:none}}</style></head><body><h1>${definition.label} report</h1><p>${range.replace("_", " ")} · ${new Date().toLocaleDateString("en-NG")}</p><table><thead><tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${rows || "<tr><td colspan='" + columns.length + "'>No records</td></tr>"}</tbody></table><script>window.onload=()=>window.print()</script></body></html>`);
    printWindow.document.close();
  }

  const [exportError, setExportError] = useState("");
  function recordsError(message) {
    setExportError(message);
  }

  return (
    <>
      <PageHeading eyebrow="INSIGHTS" title="Reports" description="Explore business activity by report type and period; export or print the source records." action={<><button className="quiet-button" type="button" onClick={printReport}>Print report</button><button className="primary-button" type="button" onClick={exportCsv}>Export CSV</button></>} />
      <div className="management-toolbar">
        <label><span>Report</span><select value={type} onChange={(event) => setType(event.target.value)}>{Object.entries(reportDefinitions).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}</select></label>
        <label><span>Period</span><select value={range} onChange={(event) => setRange(event.target.value)}><option value="today">Today</option><option value="this_week">This week</option><option value="this_month">This month</option><option value="this_year">This year</option><option value="custom">Custom dates</option></select></label>
        {range === "custom" && <>
          <label><span>From</span><input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label>
          <label><span>To</span><input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} /></label>
        </>}
      </div>
      {exportError && <p className="form-feedback form-feedback--error" role="alert">{exportError}</p>}
      {records.data?.items?.length > 0 && ["sales", "expenses", "profit_loss", "product_performance", "receivables"].includes(type) && (
        <section className="panel report-chart-panel">
          <div className="panel-title"><div><h2>{definition.label} overview</h2><p>Calculated from the records shown below.</p></div></div>
          <div className="report-bars" role="img" aria-label={`Bar chart for ${definition.label}`}>
            {(records.data.items.slice(0, 8)).map((item, index) => {
              const raw = item.amount ?? item.revenue ?? item.outstanding_balance ?? item.total_purchases ?? 0;
              const values = records.data.items.map((row) => Number(row.amount ?? row.revenue ?? row.outstanding_balance ?? row.total_purchases ?? 0));
              const maximum = Math.max(1, ...values);
              return <div className="report-bars__item" key={item.id || item.name || item.metric || index}><div className="report-bars__track"><span style={{ height: `${Math.max(4, (Math.abs(Number(raw || 0)) / maximum) * 100)}%` }} /></div><small>{item.metric || item.name || item.customer || item.id || "Record"}</small></div>;
            })}
          </div>
        </section>
      )}
      <Panel title={definition.label} description={`${records.data?.items?.length || 0} records`}>
        <LoadState loading={records.loading} error={records.error}>
          <div className="table-scroll"><table><thead><tr>{definition.columns.map(([, label]) => <th key={label}>{label}</th>)}</tr></thead>
            <tbody>{(records.data?.items || []).map((item, index) => <tr key={item.id || item.name || index}>{definition.columns.map(([key]) => <td key={key}>{reportValue(key, item[key])}</td>)}</tr>)}</tbody>
          </table></div>
          {!records.data?.items?.length && <div className="empty-state">No records are available for this report and period.</div>}
        </LoadState>
      </Panel>
    </>
  );
}

function BusinessProfilePage({ businessId, businessRole, onProfileSaved, user }) {
  const profile = useBusinessData(() => businessApi.getBusiness(businessId), [businessId]);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (profile.data?.business) setForm(profile.data.business);
  }, [profile.data]);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const { name, industry, contact_email, phone, address } = form;
      const response = await businessApi.updateBusiness(businessId, {
        name, industry, contact_email, phone, address,
      });
      setForm(response.business);
      if (onProfileSaved) await onProfileSaved();
      setNotice("Business profile saved.");
    } catch (failure) {
      setError(failure.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeading eyebrow="BUSINESS PROFILE" title="Settings" description="Manage the identity and contact details for this business workspace." />
      <Panel title="Business details" description="Currency is currently fixed to NGN; multi-currency reporting is not enabled.">
        <LoadState loading={profile.loading} error={profile.error}>
          {form && <form className="management-form" onSubmit={submit}>
            <label><span>Business name</span><input required maxLength="160" value={form.name || ""} onChange={(event) => update("name", event.target.value)} disabled={businessRole !== "owner"} /></label>
            <label><span>Industry</span><input maxLength="80" value={form.industry || ""} onChange={(event) => update("industry", event.target.value)} disabled={businessRole !== "owner"} /></label>
            <label><span>Contact email</span><input type="email" maxLength="254" value={form.contact_email || ""} onChange={(event) => update("contact_email", event.target.value)} disabled={businessRole !== "owner"} /></label>
            <label><span>Phone</span><input maxLength="32" value={form.phone || ""} onChange={(event) => update("phone", event.target.value)} disabled={businessRole !== "owner"} /></label>
            <label><span>Address</span><input maxLength="500" value={form.address || ""} onChange={(event) => update("address", event.target.value)} disabled={businessRole !== "owner"} /></label>
            <label><span>Reporting currency</span><input value={form.currency || "NGN"} readOnly /></label>
            {businessRole === "owner" && <button type="submit" className="primary-button" disabled={saving}>{saving ? "Saving…" : "Save profile"}</button>}
          </form>}
        </LoadState>
        {error && <p className="form-feedback form-feedback--error" role="alert">{error}</p>}
        {notice && <p className="form-feedback" role="status">{notice}</p>}
      </Panel>
      <Panel title="Account profile" description="Identity information for this signed-in account.">
        <dl className="customer-detail-list">
          <div><dt>Name</dt><dd>{user?.name || "—"}</dd></div>
          <div><dt>Email</dt><dd>{user?.email || "—"}</dd></div>
          <div><dt>Workspace role</dt><dd>{businessRole || "—"}</dd></div>
          <div><dt>System role</dt><dd>{user?.system_role || "user"}</dd></div>
        </dl>
      </Panel>
      <Panel title="Security" description="Account recovery and password controls use the secure authentication flow.">
        <div className="settings-security-actions">
          <p>Use password recovery to reset the account password. A verified email and login OTP remain required to sign in.</p>
          <button type="button" className="quiet-button" onClick={() => window.location.assign("/forgot-password")}>Reset password</button>
        </div>
      </Panel>
      <Panel title="Workspace preferences" description="Supported workspace settings are shown here.">
        <dl className="customer-detail-list">
          <div><dt>Reporting currency</dt><dd>NGN — Nigerian Naira</dd></div>
          <div><dt>Data region</dt><dd>Managed by deployment configuration</dd></div>
          <div><dt>AI assistant</dt><dd>Reserved for Stage 5</dd></div>
          <div><dt>Payment integration</dt><dd>Reserved for Stage 6</dd></div>
        </dl>
      </Panel>
    </>
  );
}

export { CustomerPage, ExpensesPage, InventoryPage, ProductPage, ReportsPage, BusinessProfilePage };
