const apiBase = "/api/v1/businesses";
let csrfToken;

export class BusinessApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = "BusinessApiError";
    this.status = status;
    this.code = code;
  }
}

async function readJson(response) {
  try {
    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") throw error;
    return null;
  }
}

async function refreshCsrfToken() {
  const response = await fetch("/api/v1/auth/csrf", {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const payload = await readJson(response);
  if (!response.ok || typeof payload?.csrf_token !== "string") {
    throw new BusinessApiError(
      payload?.error?.message || "Could not initialize secure business access.",
      response.status,
      payload?.error?.code,
    );
  }
  csrfToken = payload.csrf_token;
}

async function request(path, { method = "GET", body, signal, retryCsrf = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    if (!csrfToken) await refreshCsrfToken();
    headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${apiBase}${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  const payload = await readJson(response);
  if (response.status === 400 && payload?.error?.code === "csrf_failed" && retryCsrf) {
    csrfToken = undefined;
    await refreshCsrfToken();
    return request(path, { method, body, signal, retryCsrf: false });
  }
  if (!response.ok) {
    throw new BusinessApiError(
      payload?.error?.message || "The request could not be completed.",
      response.status,
      payload?.error?.code,
    );
  }
  return payload;
}

function queryString(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  return search.toString();
}

function businessPath(businessId, suffix = "") {
  return `/${encodeURIComponent(businessId)}${suffix}`;
}

export const businessApi = {
  getBusiness(businessId, options = {}) {
    return request(businessPath(businessId), options);
  },
  updateBusiness(businessId, profile) {
    return request(businessPath(businessId), { method: "PATCH", body: profile });
  },
  getDashboard(businessId, range = "this_month", params = {}) {
    const search = queryString({ range, ...params });
    return request(`${businessPath(businessId, "/dashboard")}?${search}`);
  },
  getSales(businessId, params = {}) {
    const search = queryString(params);
    return request(`${businessPath(businessId, "/sales")}${search ? `?${search}` : ""}`);
  },
  getSale(businessId, saleId) {
    return request(businessPath(businessId, `/sales/${encodeURIComponent(saleId)}`));
  },
  updateSale(businessId, saleId, payload) {
    return request(businessPath(businessId, `/sales/${encodeURIComponent(saleId)}`), {
      method: "PATCH",
      body: payload,
    });
  },
  createSale(businessId, payload) {
    return request(businessPath(businessId, "/sales"), { method: "POST", body: payload });
  },
  recordPayment(businessId, saleId, payment) {
    return request(businessPath(businessId, `/sales/${encodeURIComponent(saleId)}/payments`), {
      method: "POST",
      body: payment,
    });
  },
  recordRefund(businessId, saleId, refund) {
    return request(businessPath(businessId, `/sales/${encodeURIComponent(saleId)}/refunds`), {
      method: "POST",
      body: refund,
    });
  },
  cancelSale(businessId, saleId, reason) {
    return request(businessPath(businessId, `/sales/${encodeURIComponent(saleId)}/cancel`), {
      method: "POST",
      body: { reason },
    });
  },
  getProducts(businessId, params = {}) {
    const search = queryString(params);
    return request(`${businessPath(businessId, "/products")}${search ? `?${search}` : ""}`);
  },
  getProduct(businessId, productId) {
    return request(businessPath(businessId, `/products/${encodeURIComponent(productId)}`));
  },
  createProduct(businessId, product) {
    return request(businessPath(businessId, "/products"), { method: "POST", body: product });
  },
  updateProduct(businessId, productId, product) {
    return request(businessPath(businessId, `/products/${encodeURIComponent(productId)}`), {
      method: "PATCH",
      body: product,
    });
  },
  archiveProduct(businessId, productId) {
    return request(
      businessPath(businessId, `/products/${encodeURIComponent(productId)}/archive`),
      { method: "POST", body: {} },
    );
  },
  adjustStock(businessId, productId, adjustment) {
    return request(
      businessPath(businessId, `/products/${encodeURIComponent(productId)}/stock-adjustment`),
      { method: "POST", body: adjustment },
    );
  },
  getExpenses(businessId, params = {}) {
    const search = queryString(params);
    return request(`${businessPath(businessId, "/expenses")}${search ? `?${search}` : ""}`);
  },
  createExpense(businessId, expense) {
    return request(businessPath(businessId, "/expenses"), { method: "POST", body: expense });
  },
  updateExpense(businessId, expenseId, expense) {
    return request(businessPath(businessId, `/expenses/${encodeURIComponent(expenseId)}`), {
      method: "PATCH",
      body: expense,
    });
  },
  deleteExpense(businessId, expenseId) {
    return request(businessPath(businessId, `/expenses/${encodeURIComponent(expenseId)}`), {
      method: "DELETE",
      body: {},
    });
  },
  getReports(businessId, type = "sales", range = "this_month", params = {}) {
    const search = queryString({ type, range, ...params });
    return request(`${businessPath(businessId, "/reports")}?${search}`);
  },
  async exportCsv(businessId, type = "sales", range = "this_month", params = {}) {
    const search = queryString({ type, range, ...params });
    const response = await fetch(
      `${apiBase}/${encodeURIComponent(businessId)}/reports/export?${search}`,
      { credentials: "same-origin", headers: { Accept: "text/csv" } },
    );
    if (!response.ok) {
      const payload = await readJson(response);
      throw new BusinessApiError(
        payload?.error?.message || "CSV export failed.",
        response.status,
        payload?.error?.code,
      );
    }
    return response.text();
  },
};
