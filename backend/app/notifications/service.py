import uuid
import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from pydantic import BaseModel

from app.models.automation import Notification
from app.core.exceptions import ResourceNotFoundException


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    severity: str
    is_read: bool
    is_dismissed: bool
    automation_id: Optional[str] = None
    execution_id: Optional[str] = None
    created_at: datetime.datetime


class NotificationService:
    @classmethod
    async def list_notifications(
        cls,
        db: AsyncSession,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[NotificationResponse]:
        stmt = (
            select(Notification)
            .where(Notification.is_dismissed == False)
            .order_by(Notification.created_at.desc())
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        stmt = stmt.offset(offset).limit(limit)

        res = await db.execute(stmt)
        items = res.scalars().all()
        return [
            NotificationResponse(
                id=n.id,
                title=n.title,
                message=n.message,
                notification_type=n.notification_type,
                severity=n.severity,
                is_read=n.is_read,
                is_dismissed=n.is_dismissed,
                automation_id=n.automation_id,
                execution_id=n.execution_id,
                created_at=n.created_at,
            )
            for n in items
        ]

    @classmethod
    async def get_unread_count(cls, db: AsyncSession) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.is_read == False,
            Notification.is_dismissed == False,
        )
        res = await db.execute(stmt)
        return res.scalar() or 0

    @classmethod
    async def mark_as_read(cls, db: AsyncSession, notification_id: str) -> bool:
        stmt = select(Notification).where(Notification.id == notification_id)
        res = await db.execute(stmt)
        n = res.scalar_one_or_none()
        if not n:
            raise ResourceNotFoundException(f"Notification '{notification_id}' not found.")
        n.is_read = True
        await db.commit()
        return True

    @classmethod
    async def mark_all_as_read(cls, db: AsyncSession) -> int:
        stmt = (
            update(Notification)
            .where(Notification.is_read == False)
            .values(is_read=True)
        )
        res = await db.execute(stmt)
        await db.commit()
        return res.rowcount

    @classmethod
    async def dismiss(cls, db: AsyncSession, notification_id: str) -> bool:
        stmt = select(Notification).where(Notification.id == notification_id)
        res = await db.execute(stmt)
        n = res.scalar_one_or_none()
        if not n:
            raise ResourceNotFoundException(f"Notification '{notification_id}' not found.")
        n.is_dismissed = True
        await db.commit()
        return True
