"""
Quick SMTP debug script — tests both credential sets to see which one works.
"""
import asyncio
import aiosmtplib
from email.message import EmailMessage


async def test_credentials(label: str, user: str, password: str):
    print(f"\n{'='*60}")
    print(f"  Testing: {label}")
    print(f"  User:     {user}")
    print(f"  Password: {password}")
    print(f"{'='*60}")

    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = user  # send to self
    msg["Subject"] = f"SMTP Test — {label}"
    msg.set_content("If you receive this, credentials are working!")

    try:
        await aiosmtplib.send(
            msg,
            hostname="mail.tekkiwebsolutions.com",
            port=465,
            username=user,
            password=password,
            use_tls=True,
            timeout=15,
        )
        print(f"  ✅ SUCCESS — {label} credentials work!\n")
        return True
    except Exception as e:
        print(f"  ❌ FAILED  — {e}\n")
        return False


async def main():
    # Credential set 1: livwell.tws (from test_smtp.py)
    ok1 = await test_credentials(
        "livwell.tws",
        "livwell.tws@tekkiwebsolutions.com",
        "uFJ-Xpn4H!sd",
    )

    # Credential set 2: emr (original .env)
    ok2 = await test_credentials(
        "emr",
        "emr@tekkiwebsolutions.com",
        "u!a)iGbE@@y",
    )

    print("\n" + "="*60)
    if ok1:
        print("  → Use livwell.tws credentials in .env")
    elif ok2:
        print("  → Use emr credentials in .env")
    else:
        print("  → NEITHER credential set works!")
        print("  → The mail server may have changed passwords.")
        print("  → Contact your mail admin to verify credentials.")
    print("="*60)


asyncio.run(main())
