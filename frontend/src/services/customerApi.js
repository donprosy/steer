const apiBase = "/api/v1/businesses";
let csrfToken;

export class CustomerApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = "CustomerApiError";
    this.status = status;
    this.code = code;
  }
}

async function readResponse(response) {
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
  const payload = await readResponse(response);
  if (!response.ok || typeof payload?.csrf_token !== "string") {
    throw new CustomerApiError(
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
  const payload = await readResponse(response);
  if (
    response.status === 400 &&
    payload?.error?.code === "csrf_failed" &&
    retryCsrf
  ) {
    csrfToken = undefined;
    await refreshCsrfToken();
    return request(path, { method, body, signal, retryCsrf: false });
  }
  if (!response.ok) {
    throw new CustomerApiError(
      payload?.error?.message || "The request could not be completed.",
      response.status,
      payload?.error?.code,
    );
  }
  return payload;
}

export const customerApi = {
  list(businessId, { page, perPage, query, signal }) {
    const search = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
      q: query,
    });
    return request(`/${encodeURIComponent(businessId)}/customers?${search}`, { signal });
  },
  create(businessId, customer) {
    return request(`/${encodeURIComponent(businessId)}/customers`, {
      method: "POST",
      body: customer,
    });
  },
  update(businessId, customerId, customer) {
    return request(
      `/${encodeURIComponent(businessId)}/customers/${encodeURIComponent(customerId)}`,
      { method: "PATCH", body: customer },
    );
  },
  remove(businessId, customerId) {
    return request(
      `/${encodeURIComponent(businessId)}/customers/${encodeURIComponent(customerId)}`,
      { method: "DELETE", body: {} },
    );
  },
};
