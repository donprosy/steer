const authBase = "/api/v1/auth";
let csrfToken;

export class AuthApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.code = code;
    this.retryAfter = 0;
  }
}

async function readResponse(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function refreshCsrfToken() {
  const response = await fetch(`${authBase}/csrf`, {
    credentials: "same-origin",
    headers: { Accept: "application/json" },
  });
  const payload = await readResponse(response);
  if (!response.ok || typeof payload?.csrf_token !== "string") {
    throw new AuthApiError(
      payload?.error?.message || "Could not initialize secure account access.",
      response.status,
      payload?.error?.code,
    );
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

  const response = await fetch(`${authBase}${path}`, {
    method,
    credentials: "same-origin",
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await readResponse(response);

  if (
    response.status === 400 &&
    payload?.error?.code === "csrf_failed" &&
    retryCsrf
  ) {
    csrfToken = undefined;
    await refreshCsrfToken();
    return request(path, { method, body, retryCsrf: false });
  }

  if (!response.ok) {
    const error = new AuthApiError(
      payload?.error?.message || "The request could not be completed.",
      response.status,
      payload?.error?.code,
    );
    error.retryAfter = Number(payload?.error?.retry_after) || 0;
    throw error;
  }
  return payload;
}

export const authApi = {
  currentUser: () => request("/me"),
  login: (email, password, rememberMe) =>
    request("/login", {
      method: "POST",
      body: { email, password, remember_me: rememberMe },
    }),
  register: (name, email, password, businessName, confirmPassword) =>
    request("/register", {
      method: "POST",
      body: {
        name,
        email,
        password,
        confirm_password: confirmPassword,
        business_name: businessName,
      },
    }),
  requestVerification: (email) =>
    request("/verification-requests", { method: "POST", body: { email } }),
  verifyEmail: (email, code) =>
    request("/email-verifications", { method: "POST", body: { email, code } }),
  requestPasswordReset: (email) =>
    request("/password-reset-requests", { method: "POST", body: { email } }),
  resetPassword: (email, code, password, confirmPassword) =>
    request("/password-resets", {
      method: "POST",
      body: {
        email,
        code,
        password,
        confirm_password: confirmPassword,
      },
    }),
  logout: () => request("/logout", { method: "POST", body: {} }),
};
