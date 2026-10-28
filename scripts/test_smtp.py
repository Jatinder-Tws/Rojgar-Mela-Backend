"""
Test SMTP connectivity and send a sample email.

Edit SMTP_CONFIG below, then run:
    python scripts/test_smtp.py you@example.com
"""
from __future__ import annotations

import argparse
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr

# ── Edit these static credentials ────────────────────────────────────────────
SMTP_CONFIG = {
    "host": "smtp.zeptomail.in",
    "port": 587,
    "user": "vizops360.ai",
    "password": "PHtE6r1YRenrjmMm+xRR5fK5HpWnZtt/9L9nJQIRs91FXqJWHU1SqN8vkWe1qBosU6VDQqSezNlotO7K5eKBJW/qNGodDmqyqK3sx/VYSPOZsbq6x00Vt1oZdEXVUI/pc9dt1yXfv9zaNA==",
    # Must be a verified domain/address in ZeptoMail Mail Agent
    "from_addr": "Rojgar Mela <info@rojgarmela.ai>",
    "tls": True,
}
# ─────────────────────────────────────────────────────────────────────────────


def _build_message(from_addr: str, to_email: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "SMTP test"
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Date"] = formatdate(localtime=True)
    domain = parseaddr(from_addr)[1].split("@")[-1] or "localhost"
    msg["Message-ID"] = make_msgid(domain=domain)

    text = "This is a test email from scripts/test_smtp.py.\nIf you received it, SMTP is working.\n"
    html = (
        "<html><body>"
        "<p>This is a test email from <code>scripts/test_smtp.py</code>.</p>"
        "<p>If you received it, SMTP is working.</p>"
        "</body></html>"
    )
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def send_test(to_email: str) -> None:
    cfg = SMTP_CONFIG
    missing = [k for k in ("host", "user", "password") if not cfg.get(k)]
    if missing:
        raise SystemExit(f"Fill SMTP_CONFIG in this script: {', '.join(missing)}")

    print("SMTP settings")
    print(f"  host     : {cfg['host']}")
    print(f"  port     : {cfg['port']}")
    print(f"  user     : {cfg['user']}")
    print(f"  from     : {cfg['from_addr']}")
    print(f"  tls      : {cfg['tls']}")
    print(f"  to       : {to_email}")
    print()

    msg = _build_message(cfg["from_addr"], to_email)
    use_implicit_tls = cfg["port"] == 465
    context = ssl.create_default_context()

    print("[1/4] Connecting…")
    if use_implicit_tls:
        server: smtplib.SMTP = smtplib.SMTP_SSL(cfg["host"], cfg["port"], timeout=30, context=context)
    else:
        server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=30)
    try:
        server.ehlo()
        print("[2/4] Connected (EHLO OK)")

        if cfg["tls"] and not use_implicit_tls:
            print("[3/4] Starting TLS…")
            server.starttls(context=context)
            server.ehlo()
            print("      STARTTLS OK")
        else:
            print("[3/4] TLS skipped (implicit SSL or tls=False)")

        print("[4/4] Authenticating and sending…")
        server.login(cfg["user"], cfg["password"])
        refused = server.sendmail(
            parseaddr(cfg["from_addr"])[1] or cfg["user"],
            [to_email],
            msg.as_string(),
        )
        if refused:
            print(f"[FAIL] Server refused recipients: {refused}")
            raise SystemExit(1)
        print("[OK] Test email accepted by SMTP server")
    finally:
        try:
            server.quit()
        except Exception:
            server.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test email via SMTP (static config)")
    parser.add_argument("to", nargs="?", default="", help="Recipient email")
    args = parser.parse_args()
    if not args.to:
        parser.error("Provide a recipient: python scripts/test_smtp.py you@example.com")
    try:
        send_test(args.to)
    except smtplib.SMTPAuthenticationError as e:
        print(f"[FAIL] Authentication failed: {e}")
        raise SystemExit(1) from e
    except smtplib.SMTPException as e:
        print(f"[FAIL] SMTP error: {e}")
        raise SystemExit(1) from e
    except OSError as e:
        print(f"[FAIL] Connection error: {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
