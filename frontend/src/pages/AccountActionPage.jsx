import { useEffect, useState } from "react";
import { Button, Brand } from "../components/UI.jsx";
import Icon from "../components/Icon.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { authApi } from "../services/authApi.js";

function AccountActionPage({ mode, navigate }) {
  const isVerification = mode === "verify-email";
  const { acceptAuthenticatedUser, clearAuthenticatedUser } = useAuth();
  const [step, setStep] = useState(isVerification ? "verify" : "request");
  const [email, setEmail] = useState(
    new URLSearchParams(window.location.search).get("email") || "",
  );
  const [code, setCode] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [resendSeconds, setResendSeconds] = useState(0);

  useEffect(() => {
    if (!resendSeconds) return undefined;
    const timer = window.setTimeout(
      () => setResendSeconds((seconds) => Math.max(0, seconds - 1)),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [resendSeconds]);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    setSubmitting(true);
    try {
      if (isVerification) {
        const response = await authApi.verifyEmail(email, code);
        acceptAuthenticatedUser(response.user);
        navigate("/app/overview");
      } else if (step === "request") {
        const response = await authApi.requestPasswordReset(email);
        setStep("reset");
        setMessage(response.message);
        setResendSeconds(60);
      } else {
        if (form.elements.password.value !== form.elements.confirm_password.value) {
          setError("The passwords do not match.");
          return;
        }
        await authApi.resetPassword(
          email,
          code,
          form.elements.password.value,
          form.elements.confirm_password.value,
        );
        clearAuthenticatedUser();
        navigate("/login");
      }
    } catch (requestError) {
      setError(requestError.message);
      if (requestError.retryAfter) setResendSeconds(requestError.retryAfter);
    } finally {
      setSubmitting(false);
    }
  }

  async function resendCode() {
    setError("");
    try {
      const response = isVerification
        ? await authApi.requestVerification(email)
        : await authApi.requestPasswordReset(email);
      setMessage(response.message);
      setResendSeconds(60);
    } catch (requestError) {
      setError(requestError.message);
      if (requestError.retryAfter) setResendSeconds(requestError.retryAfter);
    }
  }

  const needsCode = isVerification || step === "reset";
  return (
    <main className="auth-page auth-page--single">
      <div className="auth-main">
        <button className="auth-back" onClick={() => navigate("/")}>
          <Icon name="arrowLeft" size={17} /> Back to home
        </button>
        <div className="auth-card">
          <button className="auth-action-brand" onClick={() => navigate("/")}>
            <Brand />
          </button>
          <span className="auth-kicker">{isVerification ? "EMAIL VERIFICATION" : "ACCOUNT RECOVERY"}</span>
          <h1>{isVerification ? "Verify your email." : "Reset your password."}</h1>
          <p className="auth-intro">
            {isVerification
              ? "Enter the 6-digit code sent to your email. The code expires after 10 minutes."
              : "We will email a one-time code to the address on your account."}
          </p>
          <form onSubmit={submit} className="auth-form">
            <label>Email address<input name="email" type="email" autoComplete="email" maxLength={254} value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            {needsCode && <label>6-digit code<input className="otp-input" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} required /></label>}
            {!isVerification && step === "reset" && <>
              <label>New password<input name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>
              <label>Confirm new password<input name="confirm_password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>
            </>}
            {error && <p className="form-feedback form-feedback--error" role="alert">{error}</p>}
            {message && <p className="form-feedback form-feedback--success" role="status">{message}</p>}
            <Button type="submit" className="auth-submit" disabled={submitting}>
              {submitting ? "Please wait…" : isVerification ? "Verify email" : step === "request" ? "Send reset code" : "Reset password"}
              <Icon name="arrowRight" size={16} />
            </Button>
          </form>
          {needsCode && <p className="auth-switch">
            {resendSeconds
              ? `You can request another code in ${resendSeconds}s`
              : <button onClick={resendCode}>Resend code</button>}
          </p>}
          <p className="auth-switch">Ready to continue? <button onClick={() => navigate("/login")}>Sign in</button></p>
        </div>
        <span className="auth-copyright">© 2026 Don Prosy Business Manager</span>
      </div>
    </main>
  );
}

export default AccountActionPage;
