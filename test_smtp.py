import asyncio
import aiosmtplib
from email.message import EmailMessage

async def test():
    print("Testing SMTP...")
    
    msg = EmailMessage()
    msg["From"] = "livwell.tws@tekkiwebsolutions.com"
    msg["To"] = "livwell.tws@tekkiwebsolutions.com"
    msg["Subject"] = "Test"
    msg.set_content("Test Message")
    
    # Try implicit first
    try:
        print("1. Trying port 465 with Implicit TLS")
        await aiosmtplib.send(
            msg,
            hostname="mail.tekkiwebsolutions.com",
            port=465,
            username="livwell.tws@tekkiwebsolutions.com",
            password="uFJ-Xpn4H!sd",
            use_tls=True,
            timeout=10
        )
        print("Success on 465!")
        return
    except Exception as e:
        print(f"Failed 465: {e}")

    # Try STARTTLS
    try:
        print("\n2. Trying port 587 with STARTTLS")
        await aiosmtplib.send(
            msg,
            hostname="mail.tekkiwebsolutions.com",
            port=587,
            username="livwell.tws@tekkiwebsolutions.com",
            password="uFJ-Xpn4H!sd",
            use_tls=False,
            start_tls=True,
            timeout=10
        )
        print("Success on 587!")
    except Exception as e:
        print(f"Failed 587: {e}")

asyncio.run(test())
