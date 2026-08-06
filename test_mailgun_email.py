from __future__ import annotations

import argparse
import base64
import smtplib
import ssl
from email.message import EmailMessage


MAILGUN_HOST = "smtpout.secureserver.net"
MAILGUN_PORT = 587
MAILGUN_USERNAME = "support@rojgarmela.ai"
MAILGUN_PASSWORD = "Sarbjit2026###"
MAILGUN_FROM = "Rojgar Mela <support@rojgarmela.ai>"


def parse_from_address(value: str) -> str:
    if "<" in value and ">" in value:
        return value.split("<", 1)[1].split(">", 1)[0].strip()
    return value.strip()


def build_message(to_email: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = MAILGUN_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def smtp_login_plain(server: smtplib.SMTP, username: str, password: str) -> None:
    auth_text = f"\0{username}\0{password}".encode("utf-8")
    auth_b64 = base64.b64encode(auth_text).decode("ascii")
    code, resp = server.docmd("AUTH", f"PLAIN {auth_b64}")
    if code != 235:
        raise smtplib.SMTPAuthenticationError(code, resp)


def send_test_email(to_email: str, subject: str, body: str) -> None:
    from_email = parse_from_address(MAILGUN_FROM)
    message = build_message(to_email, subject, body)

    with smtplib.SMTP(MAILGUN_HOST, MAILGUN_PORT, timeout=30) as server:
        server.ehlo()
        context = ssl.create_default_context()
        server.starttls(context=context)
        server.ehlo()
        smtp_login_plain(server, MAILGUN_USERNAME, MAILGUN_PASSWORD)
        server.send_message(message, from_addr=from_email, to_addrs=[to_email])


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a standalone Mailgun SMTP test email.")
    parser.add_argument("--to", required=True, help="Recipient email address.")
    parser.add_argument("--subject", default="Mailgun SMTP Test Email", help="Subject for the test email.")
    parser.add_argument(
        "--body",
        default="This is a standalone Mailgun SMTP test email sent from test_mailgun_email.py.",
        help="Plain text body for the test email.",
    )
    args = parser.parse_args()

    send_test_email(args.to, args.subject, args.body)
    print(f"Mailgun SMTP test email sent successfully to {args.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
