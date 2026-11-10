const apiBase = "/api/v1/businesses";

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function request(path, { method = "GET", body, signal } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`${apiBase}${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  const payload = await readJson(response);
  if (!response.ok) {
    const message = payload?.error?.message || "The request could not be completed.";
    throw new Error(message);
  }
  return payload;
}

export const businessApi = {
  async getDashboard(businessId, range = "this_month", params = {}) {
    const search = new URLSearchParams({ range, ...params });
    return request(`/${encodeURIComponent(businessId)}/dashboard?${search.toString()}`);
  },
  async getSales(businessId, params = {}) {
    const search = new URLSearchParams(params);
    return request(`/${encodeURIComponent(businessId)}/sales?${search.toString()}`);
  },
  async getSale(businessId, saleId) {
    return request(`/${encodeURIComponent(businessId)}/sales/${encodeURIComponent(saleId)}`);
  },
  async createSale(businessId, payload) {
    return request(`/${encodeURIComponent(businessId)}/sales`, { method: "POST", body: payload });
  },
  async getReports(businessId, type = "sales", range = "this_month", params = {}) {
    const search = new URLSearchParams({ type, range, ...params });
    return request(`/${encodeURIComponent(businessId)}/reports?${search.toString()}`);
  },
  async exportCsv(businessId, type = "sales", range = "this_month", params = {}) {
    const search = new URLSearchParams({ type, range, ...params });
    const response = await fetch(`${apiBase}/${encodeURIComponent(businessId)}/reports/export?${search.toString()}`, { credentials: "same-origin" });
    if (!response.ok) {
      const payload = await readJson(response);
      throw new Error(payload?.error?.message || "CSV export failed.");
    }
    return response.text();
  },
};
