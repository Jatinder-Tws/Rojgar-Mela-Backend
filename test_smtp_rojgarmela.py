"""
SMTP test for support@rojgarmela.ai (GoDaddy / secureserver.net).

Run from JobSeekerBackend:
    python test_smtp_rojgarmela.py

Optional: set TEST_TO to send to another address (default: same inbox).
"""
import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = "smtpout.secureserver.net"
SMTP_USER = "support@rojgarmela.ai"
SMTP_PASSWORD = "ui27AqkiMfSq/*C"
SMTP_FROM = "Rojgar Mela <support@rojgarmela.ai>"
TEST_TO = os.environ.get("TEST_TO", "rajandhanjal.tws@gmail.com")

IMAP_HOST = "imap.secureserver.net"
IMAP_PORT = 993


def send_via_smtp(label: str, port: int, use_ssl: bool, starttls: bool) -> bool:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  Host: {SMTP_HOST}:{port}  ssl={use_ssl}  starttls={starttls}")
    print(f"{'=' * 60}")

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = TEST_TO
    msg["Subject"] = f"Rojgar Mela SMTP test — {label}"
    msg.set_content(
        f"This message was sent via {SMTP_HOST}:{port} ({label}).\n"
        "If you received it, SMTP is working."
    )

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(SMTP_HOST, port, timeout=30) as smtp:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
                smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(msg)
        print(f"  SUCCESS — email sent to {TEST_TO}\n")
        return True
    except Exception as e:
        print(f"  FAILED — {type(e).__name__}: {e}\n")
        return False


def test_imap_login() -> bool:
    print(f"\n{'=' * 60}")
    print(f"  IMAP login — {IMAP_HOST}:{IMAP_PORT}")
    print(f"{'=' * 60}")
    try:
        import imaplib

        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=ctx) as imap:
            imap.login(SMTP_USER, SMTP_PASSWORD)
            status, data = imap.select("INBOX", readonly=True)
            count = data[0].decode() if status == "OK" and data else "?"
            print(f"  SUCCESS — INBOX selectable (messages: {count})\n")
            return True
    except Exception as e:
        print(f"  FAILED — {type(e).__name__}: {e}\n")
        return False


def main() -> None:
    print(f"Account: {SMTP_USER}")
    print(f"Send test mail to: {TEST_TO}")

    ok_465 = send_via_smtp("Port 465 — SSL", port=465, use_ssl=True, starttls=False)
    ok_587 = send_via_smtp("Port 587 — STARTTLS", port=587, use_ssl=False, starttls=True)
    ok_imap = test_imap_login()

    print("=" * 60)
    print("Summary:")
    print(f"  SMTP 465 (SSL):      {'OK' if ok_465 else 'FAIL'}")
    print(f"  SMTP 587 (STARTTLS): {'OK' if ok_587 else 'FAIL'}")
    print(f"  IMAP 993:            {'OK' if ok_imap else 'FAIL'}")
    if ok_465 or ok_587:
        preferred = "465" if ok_465 else "587"
        print(f"\n  Suggested .env:")
        print(f"    SMTP_HOST={SMTP_HOST}")
        print(f"    SMTP_PORT={preferred}")
        print(f"    SMTP_USER={SMTP_USER}")
        print(f"    SMTP_PASSWORD=<your-password>")
        print(f"    SMTP_FROM={SMTP_FROM}")
        print(f"    SMTP_TLS={'false' if preferred == '465' else 'true'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
