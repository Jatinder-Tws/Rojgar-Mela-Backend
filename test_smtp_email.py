from __future__ import annotations

import argparse
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path
from typing import Dict


ENV_PATH = Path(__file__).with_name(".env")


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_from_address(value: str) -> str:
    if "<" in value and ">" in value:
        return value.split("<", 1)[1].split(">", 1)[0].strip()
    return value.strip()


def build_message(from_email: str, to_email: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def smtp_login(server: smtplib.SMTP, username: str, password: str) -> None:
    # Mailtrap can drop the connection on smtplib's default initial AUTH response.
    server.login(username, password, initial_response_ok=False)


def send_test_email(to_email: str, subject: str, body: str) -> None:
    env = load_env_file(ENV_PATH)
    host = env.get("SMTP_HOST", "").strip()
    port = int(env.get("SMTP_PORT", "0").strip() or 0)
    username = env.get("SMTP_USER", "").strip()
    password = env.get("SMTP_PASSWORD", "").strip()
    from_header = env.get("SMTP_FROM", "Rojgar Mela <noreply@rojgarmela.ai>").strip()
    smtp_tls = parse_bool(env.get("SMTP_TLS"), default=True)
    if not host or not port:
        raise RuntimeError("Missing SMTP_HOST or SMTP_PORT in .env")
    if not username or not password:
        raise RuntimeError("Missing SMTP_USER or SMTP_PASSWORD in .env")

    from_email = parse_from_address(from_header)
    message = build_message(from_header, to_email, subject, body)

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            smtp_login(server, username, password)
            server.send_message(message, from_addr=from_email, to_addrs=[to_email])
        return

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if smtp_tls:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.ehlo()
        smtp_login(server, username, password)
        server.send_message(message, from_addr=from_email, to_addrs=[to_email])


def main() -> int:
    env = load_env_file(ENV_PATH)
    default_to = parse_from_address(env.get("SMTP_FROM", ""))

    parser = argparse.ArgumentParser(description="Send a standalone SMTP test email.")
    parser.add_argument(
        "--to",
        default=default_to,
        help="Recipient email address. Defaults to the email from SMTP_FROM.",
    )
    parser.add_argument(
        "--subject",
        default="SMTP Test Email",
        help="Subject for the test email.",
    )
    parser.add_argument(
        "--body",
        default="This is a standalone SMTP test email sent from test_smtp_email.py.",
        help="Plain text body for the test email.",
    )
    args = parser.parse_args()

    if not args.to:
        raise RuntimeError("No recipient provided. Use --to or set SMTP_FROM in .env")

    send_test_email(args.to, args.subject, args.body)
    print(f"SMTP test email sent successfully to {args.to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
