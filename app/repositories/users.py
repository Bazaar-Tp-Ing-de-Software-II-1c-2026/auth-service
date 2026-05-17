from sqlalchemy.orm import Session
from sqlalchemy import func, or_
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
        db.query(func.date(models.User.created_at).label("date"), func.count(models.User.id).label("count"))
        .filter(models.User.created_at >= start_date, models.User.created_at <= end_date)
        .group_by(func.date(models.User.created_at))
        .order_by(func.date(models.User.created_at))
        .all()
    )


def get_users_paginated(db: Session, page: int, limit: int, search: str | None = None):
    query = db.query(models.User)

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                models.User.email.ilike(search_term),
                models.User.username.ilike(search_term),
                models.User.first_name.ilike(search_term),
                models.User.last_name.ilike(search_term),
            )
        )

    total = query.count()
    users = (
        query.order_by(models.User.created_at.desc(), models.User.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return users, total
