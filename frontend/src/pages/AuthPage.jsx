import { useEffect, useRef, useState } from "react";
import Icon from "../components/Icon.jsx";
import { Brand, Button } from "../components/UI.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { authApi } from "../services/authApi.js";

const copy = {
  login: {
    eyebrow: "WELCOME BACK",
    title: "Good to see you.",
    intro: "Sign in to pick up where you left off.",
    action: "Sign in",
    switchText: "New to Don Prosy?",
    switchAction: "Create an account",
    switchRoute: "/register",
  },
  register: {
    eyebrow: "YOUR NEXT CHAPTER",
    title: "Let's get started.",
    intro: "Create your account and bring your business into focus.",
    action: "Create account",
    switchText: "Already have an account?",
    switchAction: "Sign in",
    switchRoute: "/login",
  },
  "forgot-password": {
    eyebrow: "ACCOUNT RECOVERY",
    title: "Let's get you back in.",
    intro: "Enter the email address you used to create your account.",
    action: "Send reset code",
    switchText: "Remembered your password?",
    switchAction: "Back to sign in",
    switchRoute: "/login",
  },
};

function passwordStrength(password) {
  if (!password) return { score: 0, label: "" };
  let score = 0;
  if (password.length >= 12) score += 1;
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  return {
    score,
    label: ["", "Weak", "Fair", "Good", "Strong"][score],
  };
}

function AuthPage({ mode, navigate }) {
  const content = copy[mode];
  const { login, acceptAuthenticatedUser, clearAuthenticatedUser, initializationError } = useAuth();
  const emailInput = useRef(null);
  const [stage, setStage] = useState("form");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [resetPassword, setResetPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [canResendVerification, setCanResendVerification] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [resendSeconds, setResendSeconds] = useState(0);
  const strength = passwordStrength(password);

  useEffect(() => {
    if (resendSeconds <= 0) return undefined;
    const timer = window.setTimeout(
      () => setResendSeconds((seconds) => Math.max(0, seconds - 1)),
      1000,
    );
    return () => window.clearTimeout(timer);
  }, [resendSeconds]);

  function startCooldown(seconds = 60) {
    setResendSeconds(Math.max(0, seconds));
  }

  function showRequestError(requestError) {
    setError(requestError.message);
    if (requestError.retryAfter) startCooldown(requestError.retryAfter);
  }

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    setCanResendVerification(false);
    const form = event.currentTarget;
    if (!form.reportValidity()) return;

    if (mode === "register" && stage === "verify") {
      setSubmitting(true);
      try {
        const response = await authApi.verifyEmail(email, code);
        acceptAuthenticatedUser(response.user);
        navigate("/app/overview");
      } catch (requestError) {
        if (mode === "login" && requestError.code === "email_not_verified") {
          setCanResendVerification(true);
        }
        showRequestError(requestError);
      } finally {
        setSubmitting(false);
      }
      return;
    }

    if (mode === "forgot-password" && stage === "reset") {
      const newPassword = form.elements.reset_password.value;
      if (newPassword !== form.elements.confirm_password.value) {
        setError("The passwords do not match.");
        return;
      }
      setSubmitting(true);
      try {
        await authApi.resetPassword(email, code, newPassword, form.elements.confirm_password.value);
        clearAuthenticatedUser();
        navigate("/login");
      } catch (requestError) {
        showRequestError(requestError);
      } finally {
        setSubmitting(false);
      }
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(
          form.elements.email.value,
          form.elements.password.value,
          form.elements.remember_me.checked,
        );
        navigate("/app/overview");
        return;
      }

      const submittedEmail = form.elements.email.value;
      if (mode === "register") {
        if (form.elements.password.value !== form.elements.confirm_password.value) {
          setError("The passwords do not match.");
          return;
        }
        const response = await authApi.register(
          form.elements.name.value,
          submittedEmail,
          form.elements.password.value,
          form.elements.business_name.value,
          form.elements.confirm_password.value,
        );
        setEmail(response.email || submittedEmail.trim());
        setStage("verify");
        setMessage(response.message);
        startCooldown();
      } else {
        const response = await authApi.requestPasswordReset(submittedEmail);
        setEmail(submittedEmail.trim());
        setStage("reset");
        setMessage(response.message);
        startCooldown();
      }
    } catch (requestError) {
      showRequestError(requestError);
    } finally {
      setSubmitting(false);
    }
  }

  async function resendVerification() {
    setError("");
    setMessage("");
    const submittedEmail = email || emailInput.current?.value;
    if (!submittedEmail) {
      setError("Enter your email address first.");
      return;
    }
    try {
      const response = await authApi.requestVerification(submittedEmail);
      setEmail(submittedEmail.trim());
      setMessage(response.message);
      startCooldown();
    } catch (requestError) {
      showRequestError(requestError);
    }
  }

  async function resendPasswordCode() {
    setError("");
    setMessage("");
    try {
      const response = await authApi.requestPasswordReset(email);
      setMessage(response.message);
      startCooldown();
    } catch (requestError) {
      showRequestError(requestError);
    }
  }

  const verificationStage = mode === "register" && stage === "verify";
  const recoveryStage = mode === "forgot-password" && stage === "reset";
  const title = verificationStage
    ? "Check your email."
    : recoveryStage
      ? "Reset your password."
      : content.title;
  const intro = verificationStage
    ? `Enter the 6-digit code sent to ${email}. It expires in 10 minutes.`
    : recoveryStage
      ? `Enter the 6-digit code sent to ${email}, then choose a new password.`
      : content.intro;

  return (
    <main className="auth-page">
      <div className="auth-aside">
        <div className="auth-aside__inner">
          <button className="auth-brand-link" onClick={() => navigate("/")}><Brand light /></button>
          <div className="auth-quote">
            <span className="quote-mark">“</span>
            <p>When you can see your business clearly, you can move it forward with confidence.</p>
            <div><span className="quote-line" /><small>A clearer view starts here</small></div>
          </div>
          <div className="auth-aside__bottom"><Icon name="shield" size={17} /> Thoughtfully designed with your business in mind</div>
        </div>
        <div className="auth-decoration auth-decoration--one" /><div className="auth-decoration auth-decoration--two" />
      </div>
      <div className="auth-main">
        <button className="auth-back" onClick={() => navigate("/")}><Icon name="arrowLeft" size={17} /> Back to home</button>
        <div className="auth-card">
          <span className="auth-kicker">{verificationStage ? "EMAIL VERIFICATION" : recoveryStage ? "ACCOUNT RECOVERY" : content.eyebrow}</span>
          <h1>{title}</h1>
          <p className="auth-intro">{intro}</p>
          <form onSubmit={submit} className="auth-form">
            {mode === "register" && stage === "form" && <label>Full name<input name="name" type="text" placeholder="e.g. Jamie Daniels" autoComplete="name" maxLength={120} required /></label>}
            {mode === "register" && stage === "form" && <label>Business name<input name="business_name" type="text" placeholder="Your business" autoComplete="organization" maxLength={160} required /></label>}
            {stage === "form" && <label>Email address<input ref={emailInput} name="email" type="email" placeholder="you@yourbusiness.com" autoComplete="email" maxLength={254} required /></label>}
            {mode === "login" && <div className="auth-password-field">
              <span className="auth-field-label">Password</span>
              <span className="password-field"><input aria-label="Password" name="password" type={showPassword ? "text" : "password"} placeholder="Enter your password" autoComplete="current-password" maxLength={128} required /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}><Icon name={showPassword ? "eyeOff" : "eye"} size={18} /></button></span>
            </div>}
            {mode === "register" && stage === "form" && <>
              <div className="auth-password-field">
                <label className="auth-field-label" htmlFor="register-password">Password</label>
                <span className="password-field"><input id="register-password" name="password" type={showPassword ? "text" : "password"} placeholder="At least 12 characters" autoComplete="new-password" minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} required /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}><Icon name={showPassword ? "eyeOff" : "eye"} size={18} /></button></span>
                {strength.label && <span className={`password-strength password-strength--${strength.score}`} aria-live="polite">Password strength: {strength.label}</span>}
              </div>
              <label>Confirm password<input name="confirm_password" type="password" placeholder="Re-enter your password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>
            </>}
            {recoveryStage && <>
              <label>6-digit reset code<input className="otp-input" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} required /></label>
              <div className="auth-password-field">
                <label className="auth-field-label" htmlFor="reset-password">New password</label>
                <span className="password-field"><input id="reset-password" name="reset_password" type={showPassword ? "text" : "password"} placeholder="At least 12 characters" autoComplete="new-password" minLength={12} maxLength={128} value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} required /><button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)}><Icon name={showPassword ? "eyeOff" : "eye"} size={18} /></button></span>
                {resetPassword && <span className={`password-strength password-strength--${passwordStrength(resetPassword).score}`} aria-live="polite">Password strength: {passwordStrength(resetPassword).label}</span>}
              </div>
            </>}
            {recoveryStage && <label>Confirm new password<input name="confirm_password" type="password" placeholder="Re-enter your new password" autoComplete="new-password" minLength={12} maxLength={128} required /></label>}
            {verificationStage && <label>6-digit verification code<input className="otp-input" name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} required /></label>}
            {mode === "login" && <div className="form-meta"><label className="checkbox-label"><input name="remember_me" type="checkbox" /> Remember me</label><button type="button" className="inline-link" onClick={() => navigate("/forgot-password")}>Forgot password?</button></div>}
            {initializationError && <p className="form-feedback form-feedback--error" role="alert">{initializationError}</p>}
            {error && <p className="form-feedback form-feedback--error" role="alert">{error}</p>}
            {message && <p className="form-feedback form-feedback--success" role="status">{message}</p>}
            <Button type="submit" className="auth-submit" disabled={submitting}>{submitting ? "Please wait…" : verificationStage ? "Verify email" : recoveryStage ? "Reset password" : content.action}<Icon name="arrowRight" size={16} /></Button>
          </form>
          {(verificationStage || recoveryStage || (mode === "login" && canResendVerification)) && <p className="auth-switch">
            {resendSeconds > 0
              ? `You can request another code in ${resendSeconds}s`
              : <button onClick={recoveryStage ? resendPasswordCode : resendVerification}>{recoveryStage ? "Resend reset code" : "Resend verification code"}</button>}
          </p>}
          <p className="auth-switch">{content.switchText} <button onClick={() => navigate(content.switchRoute)}>{content.switchAction}</button></p>
          <p className="auth-legal">By continuing, you agree to our <a href="/#faq" onClick={(event) => { event.preventDefault(); navigate("/"); }}>Terms</a> and <a href="/#faq" onClick={(event) => { event.preventDefault(); navigate("/"); }}>Privacy Policy</a>.</p>
        </div>
        <span className="auth-copyright">© 2026 Don Prosy Business Manager</span>
      </div>
    </main>
  );
}

export default AuthPage;
