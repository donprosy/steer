const apiBase = "/api/v1/businesses";
let csrfToken;

export class AiApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = "AiApiError";
    this.status = status;
    this.code = code;
  }
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
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
    throw new AiApiError("Could not initialize secure AI access.", response.status, payload?.error?.code);
  }
  csrfToken = payload.csrf_token;
}

async function request(path, { method = "GET", body, retryCsrf = true } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") {
    if (!csrfToken) await refreshCsrfToken();
    headers["X-CSRFToken"] = csrfToken;
  }
  const response = await fetch(`${apiBase}/${encodeURIComponent(path.businessId)}${path.suffix}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await readJson(response);
  if (response.status === 400 && payload?.error?.code === "csrf_failed" && retryCsrf) {
    csrfToken = undefined;
    await refreshCsrfToken();
    return request(path, { method, body, retryCsrf: false });
  }
  if (!response.ok) {
    throw new AiApiError(
      payload?.error?.message || "The request could not be completed.",
      response.status,
      payload?.error?.code,
    );
  }
  return payload;
}

export const aiApi = {
  listConversations(businessId) {
    return request({ businessId, suffix: "/assistant/conversations" });
  },
  createConversation(businessId, title) {
    return request({ businessId, suffix: "/assistant/conversations" }, { method: "POST", body: { title } });
  },
  getConversation(businessId, conversationId) {
    return request({ businessId, suffix: `/assistant/conversations/${encodeURIComponent(conversationId)}` });
  },
  renameConversation(businessId, conversationId, title) {
    return request({ businessId, suffix: `/assistant/conversations/${encodeURIComponent(conversationId)}` }, {
      method: "PATCH",
      body: { title },
    });
  },
  deleteConversation(businessId, conversationId) {
    return request({ businessId, suffix: `/assistant/conversations/${encodeURIComponent(conversationId)}` }, {
      method: "DELETE",
      body: {},
    });
  },
  chat(businessId, payload) {
    return request({ businessId, suffix: "/assistant/chat" }, { method: "POST", body: payload });
  },
  getUsage(businessId) {
    return request({ businessId, suffix: "/assistant/usage" });
  },
  getInsights(businessId, period = "this_month") {
    return request({ businessId, suffix: `/assistant/insights?period=${encodeURIComponent(period)}` });
  },
  getReport(businessId, period = "this_month") {
    return request({ businessId, suffix: `/assistant/reports?period=${encodeURIComponent(period)}` });
  },
};
