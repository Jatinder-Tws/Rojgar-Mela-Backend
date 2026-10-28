import logging
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.core.config import settings
from app.shared.models.user import User, UserRole
from app.shared.models.user_credit import UserCreditAccount, CreditTransaction, CreditPurchaseOrder
from app.modules.training_portal.services.training_portal_payment_service import (
    create_razorpay_order,
    verify_razorpay_signature,
    razorpay_configured,
)

logger = logging.getLogger(__name__)

# Credit top-up packages configuration
CREDIT_PACKAGES = {
    "starter_15": {"credits": 15, "amount_rupees": 49.0, "name": "Starter Pack (15 Credits)"},
    "pro_50": {"credits": 50, "amount_rupees": 149.0, "name": "Pro Pack (50 Credits)"},
    "ultimate_150": {"credits": 150, "amount_rupees": 349.0, "name": "Ultimate Pack (150 Credits)"},
}


class AICoachCreditsService:
    @staticmethod
    def verify_seeker_role(user: User):
        """Strictly enforce that AI Coach features are available exclusively for Job Seekers."""
        user_role_str = str(getattr(user, "role", "")).lower()
        if "seeker" not in user_role_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="AI Coach is available exclusively for Job Seekers."
            )

    @classmethod
    async def get_or_create_account(cls, db: AsyncSession, user: User) -> UserCreditAccount:
        cls.verify_seeker_role(user)
        
        stmt = select(UserCreditAccount).where(UserCreditAccount.user_id == user.id)
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        
        if not account:
            account = UserCreditAccount(
                user_id=user.id,
                balance=10,
                total_earned=10,
                total_spent=0
            )
            db.add(account)
            
            # Log welcome transaction
            txn = CreditTransaction(
                user_id=user.id,
                amount=10,
                transaction_type="welcome_bonus",
                description="Initial 10 Welcome Credits for AI Coach"
            )
            db.add(txn)
            await db.commit()
            await db.refresh(account)
            
        return account

    @classmethod
    async def deduct_heartbeat_credit(
        cls, db: AsyncSession, seeker_id: str, session_id: str, rate: float = 1.5
    ) -> Tuple[bool, float]:
        stmt = select(UserCreditAccount).where(UserCreditAccount.user_id == seeker_id)
        res = await db.execute(stmt)
        account = res.scalar_one_or_none()
        
        if not account or account.balance < rate:
            return False, round(account.balance if account else 0.0, 2)
            
        account.balance -= rate
        account.total_spent += rate
        
        txn = CreditTransaction(
            user_id=seeker_id,
            amount=-rate,
            transaction_type="call_deduction",
            description=f"1 Minute AI Coach call deduction ({rate} credits)",
            reference_id=session_id
        )
        db.add(txn)
        await db.commit()
        await db.refresh(account)
        
        return True, round(account.balance, 2)

    @classmethod
    async def create_purchase_order(
        cls, db: AsyncSession, user: User, package_id: str, idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        cls.verify_seeker_role(user)
        
        if package_id not in CREDIT_PACKAGES:
            raise HTTPException(status_code=400, detail="Invalid credit package selected.")
            
        pkg = CREDIT_PACKAGES[package_id]
        amount_paise = int(pkg["amount_rupees"] * 100)

        # Idempotency check: if an order with this idempotency key already exists for the user
        if idempotency_key:
            stmt = select(CreditPurchaseOrder).where(
                CreditPurchaseOrder.idempotency_key == idempotency_key,
                CreditPurchaseOrder.user_id == user.id,
            )
            res = await db.execute(stmt)
            existing_order = res.scalar_one_or_none()
            if existing_order:
                is_mock = (
                    existing_order.provider_order_id.startswith("order_mock_")
                    if existing_order.provider_order_id
                    else True
                )
                return {
                    "order_id": existing_order.id,
                    "provider_order_id": existing_order.provider_order_id,
                    "amount_rupees": existing_order.amount_rupees,
                    "credits": existing_order.credits,
                    "package_name": CREDIT_PACKAGES.get(existing_order.package_id, {}).get("name", existing_order.package_id),
                    "razorpay_key_id": settings.RAZORPAY_KEY_ID if not is_mock else "rzp_test_mock",
                    "is_mock": is_mock,
                    "status": existing_order.status,
                }
        
        # Call Razorpay helper
        rz_order = await create_razorpay_order(
            amount_paise=amount_paise,
            receipt=f"ai_coach_{user.id[:8]}",
            notes={
                "package_id": package_id,
                "user_id": str(user.id),
                "idempotency_key": idempotency_key or "",
            }
        )
        
        order = CreditPurchaseOrder(
            user_id=user.id,
            package_id=package_id,
            credits=pkg["credits"],
            amount_rupees=pkg["amount_rupees"],
            provider_order_id=rz_order["id"],
            idempotency_key=idempotency_key,
            status="pending"
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        is_mock = bool(rz_order.get("mock", True))
        return {
            "order_id": order.id,
            "provider_order_id": rz_order["id"],
            "amount_rupees": pkg["amount_rupees"],
            "credits": pkg["credits"],
            "package_name": pkg["name"],
            "razorpay_key_id": settings.RAZORPAY_KEY_ID if not is_mock else "rzp_test_mock",
            "is_mock": is_mock,
            "status": "pending",
        }

    @classmethod
    async def verify_and_fulfill_order(
        cls,
        db: AsyncSession,
        user: User,
        provider_order_id: str,
        provider_payment_id: str,
        provider_signature: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        cls.verify_seeker_role(user)
        
        # Row-level lock to prevent concurrent verification race condition
        stmt = (
            select(CreditPurchaseOrder)
            .where(
                CreditPurchaseOrder.provider_order_id == provider_order_id,
                CreditPurchaseOrder.user_id == user.id,
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        order = res.scalar_one_or_none()
        
        if not order:
            raise HTTPException(status_code=404, detail="Credit purchase order not found.")
            
        if order.status == "paid":
            account = await cls.get_or_create_account(db, user)
            return {
                "status": "already_fulfilled",
                "credits_added": order.credits,
                "new_balance": account.balance,
            }

        # Signature check
        is_valid = verify_razorpay_signature(provider_order_id, provider_payment_id, provider_signature)
        if not is_valid and razorpay_configured():
            order.status = "failed"
            await db.commit()
            raise HTTPException(status_code=400, detail="Payment signature verification failed.")

        order.status = "paid"
        order.provider_payment_id = provider_payment_id
        if idempotency_key and not order.idempotency_key:
            order.idempotency_key = idempotency_key

        # Guard against duplicate credit transaction
        existing_txn_stmt = select(CreditTransaction).where(
            CreditTransaction.reference_id == str(order.id),
            CreditTransaction.transaction_type == "purchase"
        )
        existing_txn = (await db.execute(existing_txn_stmt)).scalar_one_or_none()
        
        account = await cls.get_or_create_account(db, user)
        if not existing_txn:
            # Credit user's account
            account.balance += order.credits
            account.total_earned += order.credits
            
            txn = CreditTransaction(
                user_id=user.id,
                amount=order.credits,
                transaction_type="purchase",
                description=f"Purchased {order.credits} Credits ({order.package_id})",
                reference_id=str(order.id)
            )
            db.add(txn)
            
        await db.commit()
        await db.refresh(account)
        
        return {
            "status": "success",
            "credits_added": order.credits,
            "new_balance": account.balance
        }
