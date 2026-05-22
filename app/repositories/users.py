from sqlalchemy.orm import Session
from sqlalchemy import func
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
    from datetime import datetime, time
    # Convertir date a datetime para la comparación
    start_datetime = datetime.combine(start_date, time.min)
    end_datetime = datetime.combine(end_date, time.max)
    
    return (
        db.query(func.date(models.User.created_at).label("date"), func.count(models.User.id).label("count"))
        .filter(models.User.created_at >= start_datetime, models.User.created_at <= end_datetime)
        .group_by(func.date(models.User.created_at))
        .order_by(func.date(models.User.created_at))
        .all()
    )
