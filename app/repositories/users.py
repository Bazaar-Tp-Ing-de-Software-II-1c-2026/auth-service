from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from datetime import date

from app import models


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def save_user(db: Session, user: models.User):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def count_total_users(db: Session):
    return db.query(func.count(models.User.id)).scalar()


def get_users_timeline(db: Session, start_date: date, end_date: date):
    return (
        db.query(cast(models.User.created_at, Date).label("date"), func.count(models.User.id).label("count"))
        .filter(cast(models.User.created_at, Date) >= start_date, cast(models.User.created_at, Date) <= end_date)
        .group_by(cast(models.User.created_at, Date))
        .order_by(cast(models.User.created_at, Date))
        .all()
    )
