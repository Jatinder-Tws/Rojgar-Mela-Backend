import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from models.user import User
from services.totp_service import totp_service
from config import settings

async def test_logic(phone):
    engine = create_async_engine(settings.DATABASE_URL)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as db:
        print(f"\n--- Testing with phone: {phone} ---")
        
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        
        if not user:
            print("Creating new user...")
            user = User(
                phone=phone,
                is_verified=False,
                onboarding_complete=False,
                is_assessment_done=False
            )
            db.add(user)
            await db.flush()
            print(f"User flushed with ID: {user.id}")
        
        if not user.totp_secret:
            print("Generating TOTP secret...")
            secret = totp_service.generate_secret()
            user.totp_secret = secret
            await db.commit()
            print("Secret committed.")
            
            uri = totp_service.get_provisioning_uri(user.phone, secret)
            qr_base64 = totp_service.generate_qr_base64(uri)
            print("QR code generated (requires_setup=True).")
        else:
            print("User already has secret (requires_setup=False).")
            
    print("Test phase complete.")

async def main():
    phone = "8888888888"
    await test_logic(phone) # First time
    await test_logic(phone) # Second time

if __name__ == "__main__":
    asyncio.run(main())
