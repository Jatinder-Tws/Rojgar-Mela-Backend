import asyncio
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath('.'))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token, hash_password
from app.shared.models.user import User, UserRole
from app.shared.models.supervisor_profile import SupervisorProfile
from app.modules.super_admin.constants.supervisor_permissions import SUPERVISOR_PERMISSIONS
from httpx import AsyncClient, ASGITransport
from app.main import app

async def run_test():
    print("Testing Supervisor API Access Across All Modules...")
    async with AsyncSessionLocal() as db:
        # Check or create test supervisor
        email = "test.supervisor.permcheck@rojgarmela.com"
        res = await db.execute(select(User).where(User.email == email))
        user = res.scalar_one_or_none()

        all_permission_keys = [p["key"] for p in SUPERVISOR_PERMISSIONS]

        if not user:
            user = User(
                email=email,
                first_name="Perm",
                last_name="Supervisor",
                phone="9876543210",
                role=UserRole.supervisor,
                is_verified=True,
                is_super_admin=False,
                hashed_password=hash_password("Password@123"),
            )
            db.add(user)
            await db.flush()

            profile = SupervisorProfile(
                user_id=user.id,
                department="Operations",
                is_active=True,
                permissions=all_permission_keys,
            )
            db.add(profile)
            await db.commit()
            print(f"Created test supervisor user {user.id}")
        else:
            profile_res = await db.execute(select(SupervisorProfile).where(SupervisorProfile.user_id == user.id))
            profile = profile_res.scalar_one_or_none()
            if profile:
                profile.is_active = True
                profile.permissions = all_permission_keys
                await db.commit()
            print(f"Using existing test supervisor user {user.id}")

        # Generate Supervisor JWT Token
        token = create_access_token(data={
            "sub": str(user.id),
            "role": "supervisor",
            "email": user.email,
            "permissions": all_permission_keys,
        })
        headers = {"Authorization": f"Bearer {token}"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            endpoints = [
                ("GET", "/supervisor/me", 200),
                ("GET", "/super-admin/me", 200),
                ("GET", "/super-admin/analytics/dashboard", 200),
                ("GET", "/super-admin/seekers", 200),
                ("GET", "/super-admin/providers", 200),
                ("GET", "/super-admin/jobs", 200),
                ("GET", "/super-admin/matches", 200),
                ("GET", "/super-admin/applications", 200),
                ("GET", "/super-admin/career-roadmaps", 200),
                ("GET", "/super-admin/career-roadmap-options/category", 200),
                ("GET", "/job-fairs", 200),
                ("GET", "/super-admin/enquiries", 200),
                ("GET", "/super-admin/support/inquiries", 200),
                ("GET", "/super-admin/support/tickets", 200),
                ("GET", "/api/super-admin/blogs", 200),
                ("GET", "/api/super-admin/blogs/categories", 200),
                ("GET", "/super-admin/email-templates", 200),
                ("GET", "/super-admin/email-campaigns", 200),
                ("GET", "/super-admin/auth-settings", 200),
                ("GET", "/internships/", 200),
                ("GET", "/attendance/daily", 200),
            ]

            all_passed = True
            for method, path, expected_status in endpoints:
                if method == "GET":
                    resp = await client.get(path, headers=headers)
                else:
                    resp = await client.post(path, headers=headers)

                status_ok = resp.status_code == expected_status
                symbol = "✓" if status_ok else "✗"
                print(f"[{symbol}] {method} {path} -> {resp.status_code} (Expected {expected_status})")
                if not status_ok:
                    print(f"    Error detail: {resp.text[:300]}")
                    all_passed = False

            if all_passed:
                print("\nALL MODULE APIS SUCCESSFULLY AUTHENTICATED AND PASSED FOR SUPERVISOR!")
            else:
                print("\nSOME ENDPOINTS FAILED.")

if __name__ == "__main__":
    asyncio.run(run_test())
