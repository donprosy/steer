"""Accessible, email-client-friendly account email templates."""

from html import escape

BRAND = "Don Prosy Business Manager"


def _layout(preheader, heading, body):
    return f"""\
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
  <body style="margin:0;padding:0;background:#f4f7fb;color:#17233a;font-family:Arial,Helvetica,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f7fb;padding:32px 12px;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #e4eaf2;border-radius:12px;">
          <tr><td style="padding:26px 30px 18px;border-bottom:1px solid #edf1f6;">
            <div style="font-size:13px;font-weight:700;color:#17233a;">{BRAND}</div>
          </td></tr>
          <tr><td style="padding:28px 30px 30px;">
            <h1 style="margin:0 0 16px;font-size:23px;line-height:1.3;color:#142037;">{heading}</h1>
            {body}
          </td></tr>
          <tr><td style="padding:18px 30px;border-top:1px solid #edf1f6;color:#78859a;font-size:12px;line-height:1.6;">
            This is an automated account message from {BRAND}. Please do not reply.
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""


def render_otp_email(display_name, purpose, code):
    name = escape(" ".join(display_name.split()))
    if purpose == "email_verification":
        subject = "Verify your email address"
        heading = "Verify your email"
        preheader = "Your Don Prosy verification code expires in 10 minutes."
        instruction = "Use this code to verify your email address:"
        plain_subject = "Verify your Don Prosy Business Manager email"
    elif purpose == "password_reset":
        subject = "Your password reset code"
        heading = "Reset your password"
        preheader = "Your password reset code expires in 10 minutes."
        instruction = "Use this code to reset your Don Prosy account password:"
        plain_subject = "Reset your Don Prosy Business Manager password"
    else:
        raise ValueError("Unsupported account email purpose.")

    text = (
        f"Hello {display_name},\n\n{instruction}\n\n{code}\n\n"
        "This one-time code expires in 10 minutes. Do not share it with anyone. "
        "If you did not request it, you can ignore this message.\n\n"
        f"{BRAND}"
    )
    body = (
        f'<p style="margin:0 0 18px;color:#4f5f76;font-size:15px;line-height:1.7;">'
        f"Hello {name}, {escape(instruction)}</p>"
        f'<div style="margin:0 0 20px;padding:18px;border-radius:9px;background:#f1f6ff;'
        f'text-align:center;color:#1d4ed8;font-size:32px;font-weight:700;letter-spacing:9px;">'
        f"{escape(code)}</div>"
        '<p style="margin:0 0 12px;color:#4f5f76;font-size:14px;line-height:1.7;">'
        "This code expires in <strong>10 minutes</strong> and can only be used once.</p>"
        '<p style="margin:0;color:#78859a;font-size:13px;line-height:1.7;">'
        "For your security, never share this code. If you did not request it, you can ignore this email.</p>"
    )
    return plain_subject, text, _layout(preheader, heading, body)


def render_notification_email(display_name, notification):
    name = escape(" ".join(display_name.split()))
    templates = {
        "email_verified": (
            "Email verified successfully",
            "Your email is verified",
            "Your email address has been verified successfully. You can now sign in and securely access your business workspace.",
            "Your Don Prosy email address has been verified. You can now sign in and access your business workspace.",
        ),
        "welcome": (
            "Welcome to Don Prosy Business Manager",
            "Welcome to Don Prosy",
            "Your account is ready. Sign in to manage your business workspace and continue setting up your account.",
            "Welcome to Don Prosy Business Manager. Your account is ready. Sign in to access your business workspace.",
        ),
        "password_changed": (
            "Your password was changed",
            "Your password has been changed",
            "The password for your Don Prosy account was changed successfully. If you did not make this change, contact support immediately.",
            "The password for your Don Prosy account was changed successfully. If you did not make this change, contact support immediately.",
        ),
    }
    try:
        subject, heading, html_message, plain_message = templates[notification]
    except KeyError as error:
        raise ValueError("Unsupported account notification.") from error

    text = f"Hello {display_name},\n\n{plain_message}\n\n{BRAND}"
    body = (
        f'<p style="margin:0;color:#4f5f76;font-size:15px;line-height:1.7;">'
        f"Hello {name}, {escape(html_message)}</p>"
    )
    return subject, text, _layout(subject, heading, body)
