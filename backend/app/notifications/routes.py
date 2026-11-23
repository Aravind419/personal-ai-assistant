from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database.session import get_db
from app.notifications.service import NotificationService, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class UnreadCountResponse(BaseModel):
    unread_count: int


@router.get("", response_model=List[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False, description="Filter to only unread notifications"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List persistent notifications."""
    return await NotificationService.list_notifications(
        db, unread_only=unread_only, limit=limit, offset=offset
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve total count of unread notifications for badge rendering."""
    count = await NotificationService.get_unread_count(db)
    return UnreadCountResponse(unread_count=count)


@router.post("/{notification_id}/read", status_code=status.HTTP_200_OK)
async def mark_notification_read(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read."""
    await NotificationService.mark_as_read(db, notification_id)
    return {"id": notification_id, "is_read": True}


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
):
    """Mark all unread notifications as read."""
    updated = await NotificationService.mark_all_as_read(db)
    return {"marked_read": updated}


@router.delete("/{notification_id}", status_code=status.HTTP_200_OK)
async def dismiss_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Dismiss a notification."""
    await NotificationService.dismiss(db, notification_id)
    return {"id": notification_id, "dismissed": True}
