from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api.dependencies import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.post("", response_model=schemas.NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: schemas.NotificationCreateRequest,
    db: Session = Depends(get_db),
):
    notification = models.Notification(
        user_id=payload.user_id,
        notification_type=payload.notification_type,
        title=payload.title,
        body=payload.body,
        data=payload.data,
        source=payload.source,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


@router.get("/me", response_model=schemas.NotificationListResponse)
def get_my_notifications(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifications = (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )

    return {
        "data": notifications,
        "total": len(notifications),
    }