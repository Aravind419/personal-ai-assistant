import uuid
import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.tool import ToolApproval, ToolExecution
from app.tools.schemas import PermissionLevel, ApprovalStatus
from app.tools.validator import CanonicalArgumentHasher, SecretSanitizer
from app.core.exceptions import ResourceNotFoundException, ValidationException, SecurityException
from app.core.logging import logger

DEFAULT_APPROVAL_EXPIRY_MINUTES = 30


class ApprovalManager:
    """
    Manages human-in-the-loop approvals with race-safe state transitions,
    argument hash integrity, and strict expiration enforcement.
    """

    @classmethod
    async def create_approval(
        cls,
        tool_id: str,
        tool_name: str,
        action: str,
        arguments: Dict[str, Any],
        permission_level: PermissionLevel,
        risk_level: str,
        reason: str,
        target_resource: Optional[str] = None,
        expected_consequences: Optional[str] = None,
        conversation_id: Optional[str] = None,
        requested_by: str = "personal_user",
        expiry_minutes: int = DEFAULT_APPROVAL_EXPIRY_MINUTES,
        db: Optional[AsyncSession] = None,
    ) -> ToolApproval:
        now = datetime.datetime.now(datetime.timezone.utc)
        expires_at = now + datetime.timedelta(minutes=expiry_minutes)
        args_hash = CanonicalArgumentHasher.compute_hash(arguments)
        args_json = CanonicalArgumentHasher.serialize_canonical(arguments)

        approval = ToolApproval(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            tool_id=tool_id,
            tool_name=tool_name,
            action=action,
            arguments_json=args_json,
            arguments_hash=args_hash,
            target_resource=target_resource,
            expected_consequences=expected_consequences,
            permission_level=permission_level.value,
            risk_level=risk_level,
            reason=reason,
            status=ApprovalStatus.PENDING.value,
            requested_by=requested_by,
            expires_at=expires_at,
        )

        if db:
            db.add(approval)
            await db.commit()
            await db.refresh(approval)

        return approval

    @classmethod
    async def get_approval(cls, approval_id: str, db: AsyncSession) -> ToolApproval:
        stmt = select(ToolApproval).where(ToolApproval.id == approval_id)
        result = await db.execute(stmt)
        approval = result.scalar_one_or_none()
        if not approval:
            raise ResourceNotFoundException(f"Approval request {approval_id} not found.")

        # Check for dynamic expiration
        if approval.status == ApprovalStatus.PENDING.value and approval.is_expired():
            approval.status = ApprovalStatus.EXPIRED.value
            await db.commit()
            await db.refresh(approval)

        return approval

    @classmethod
    async def list_approvals(
        cls,
        db: AsyncSession,
        status: Optional[str] = None,
        tool_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ToolApproval]:
        stmt = select(ToolApproval).order_by(ToolApproval.created_at.desc())
        if status:
            stmt = stmt.where(ToolApproval.status == status)
        if tool_id:
            stmt = stmt.where(ToolApproval.tool_id == tool_id)
        if conversation_id:
            stmt = stmt.where(ToolApproval.conversation_id == conversation_id)

        stmt = stmt.limit(limit).offset(offset)
        result = await db.execute(stmt)
        approvals = list(result.scalars().all())

        # Check expirations in returned list
        now = datetime.datetime.now(datetime.timezone.utc)
        has_expired = False
        for app in approvals:
            if app.status == ApprovalStatus.PENDING.value and app.is_expired():
                app.status = ApprovalStatus.EXPIRED.value
                has_expired = True
        if has_expired:
            await db.commit()

        return approvals

    @classmethod
    async def approve(
        cls,
        approval_id: str,
        db: AsyncSession,
        decided_by: str = "personal_user",
        decision_reason: Optional[str] = None,
        confirm_critical: bool = False,
    ) -> ToolApproval:
        """
        Race-safe atomic state transition: Only transitions if current status is PENDING and not expired.
        Validates user authorization and requires explicit confirmation for Level 3 Critical actions.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Check current row
        approval = await cls.get_approval(approval_id, db)
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValidationException(f"Cannot approve: Request is already in '{approval.status}' state.")
        if approval.is_expired():
            approval.status = ApprovalStatus.EXPIRED.value
            await db.commit()
            raise ValidationException("Cannot approve: Approval request has expired.")

        # User boundary check: only authorized user can approve
        if decided_by != approval.requested_by and approval.requested_by != "personal_user":
            raise SecurityException(f"User '{decided_by}' is not authorized to approve an action requested by '{approval.requested_by}'.")

        # Level 3 Critical action check: requires explicit confirmation
        if approval.permission_level == PermissionLevel.CRITICAL.value and not confirm_critical:
            raise ValidationException("Level 3 Critical action requires explicit confirmation (confirm_critical=true).")

        # Atomic update
        stmt = (
            update(ToolApproval)
            .where(
                ToolApproval.id == approval_id,
                ToolApproval.status == ApprovalStatus.PENDING.value,
                ToolApproval.expires_at > now,
            )
            .values(
                status=ApprovalStatus.APPROVED.value,
                decided_at=now,
                decided_by=decided_by,
                decision_reason=decision_reason,
            )
        )
        res = await db.execute(stmt)
        await db.commit()

        if res.rowcount == 0:
            raise ValidationException("Failed to approve: State conflict or request expired concurrently.")

        await db.refresh(approval)
        return approval

    @classmethod
    async def reject(
        cls,
        approval_id: str,
        db: AsyncSession,
        decided_by: str = "personal_user",
        decision_reason: Optional[str] = None,
    ) -> ToolApproval:
        now = datetime.datetime.now(datetime.timezone.utc)
        approval = await cls.get_approval(approval_id, db)
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValidationException(f"Cannot reject: Request is already in '{approval.status}' state.")

        if decided_by != approval.requested_by and approval.requested_by != "personal_user":
            raise SecurityException(f"User '{decided_by}' is not authorized to reject an action requested by '{approval.requested_by}'.")

        stmt = (
            update(ToolApproval)
            .where(ToolApproval.id == approval_id, ToolApproval.status == ApprovalStatus.PENDING.value)
            .values(
                status=ApprovalStatus.REJECTED.value,
                decided_at=now,
                decided_by=decided_by,
                decision_reason=decision_reason,
            )
        )
        res = await db.execute(stmt)
        await db.commit()
        if res.rowcount == 0:
            raise ValidationException("Failed to reject: State conflict.")

        await db.refresh(approval)
        return approval

    @classmethod
    async def cancel(
        cls,
        approval_id: str,
        db: AsyncSession,
        decided_by: str = "personal_user",
    ) -> ToolApproval:
        now = datetime.datetime.now(datetime.timezone.utc)
        approval = await cls.get_approval(approval_id, db)
        if approval.status != ApprovalStatus.PENDING.value:
            raise ValidationException(f"Cannot cancel: Request is already in '{approval.status}' state.")

        if decided_by != approval.requested_by and approval.requested_by != "personal_user":
            raise SecurityException(f"User '{decided_by}' is not authorized to cancel an action requested by '{approval.requested_by}'.")

        stmt = (
            update(ToolApproval)
            .where(ToolApproval.id == approval_id, ToolApproval.status == ApprovalStatus.PENDING.value)
            .values(
                status=ApprovalStatus.CANCELLED.value,
                decided_at=now,
                decided_by=decided_by,
                decision_reason="Cancelled by user",
            )
        )
        res = await db.execute(stmt)
        await db.commit()
        if res.rowcount == 0:
            raise ValidationException("Failed to cancel: State conflict.")

        await db.refresh(approval)
        return approval

    @classmethod
    async def validate_approval_for_arguments(
        cls,
        approval_id: str,
        arguments: Dict[str, Any],
        db: AsyncSession,
    ) -> Tuple[bool, Optional[str], Optional[ToolApproval]]:
        """
        Validates that an approval exists, is APPROVED, is not expired,
        has not already been executed, and its arguments_hash matches the exact current arguments.
        """
        stmt = select(ToolApproval).where(ToolApproval.id == approval_id)
        result = await db.execute(stmt)
        approval = result.scalar_one_or_none()
        if not approval:
            return False, f"Approval ID '{approval_id}' not found.", None

        if approval.status != ApprovalStatus.APPROVED.value:
            return False, f"Approval status is '{approval.status}', not 'approved'.", approval

        if approval.is_expired():
            return False, "Approval has expired.", approval

        if approval.is_executed:
            return False, "Approval has already been executed. Approvals cannot be reused.", approval

        # Check argument tamper resistance
        current_hash = CanonicalArgumentHasher.compute_hash(arguments)
        if current_hash != approval.arguments_hash:
            logger.warning(
                f"Approval argument hash mismatch for approval {approval_id}! "
                f"Expected {approval.arguments_hash}, got {current_hash}. "
                "Invalidating previous approval."
            )
            # Invalidate tampered approval
            approval.status = ApprovalStatus.CANCELLED.value
            approval.decision_reason = "Invalidated: Arguments were modified after approval was granted."
            await db.commit()
            return False, "Arguments were modified after approval was granted. Previous approval invalidated.", approval

        return True, None, approval

    @classmethod
    async def mark_approval_executed(
        cls,
        approval_id: str,
        execution_id: str,
        db: AsyncSession,
    ) -> None:
        """
        Atomically marks the approval as executed, ensuring it cannot be executed a second time.
        Raises ValidationException if already executed.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        stmt = (
            update(ToolApproval)
            .where(
                ToolApproval.id == approval_id,
                ToolApproval.is_executed == False,
                ToolApproval.status == ApprovalStatus.APPROVED.value,
            )
            .values(
                is_executed=True,
                executed_at=now,
                execution_id=execution_id,
            )
        )
        res = await db.execute(stmt)
        if res.rowcount == 0:
            raise ValidationException("Failed to claim approval for execution: It has already been executed or state was modified.")
        await db.commit()
