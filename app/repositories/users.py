from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date, or_
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
        db.query(
            cast(models.User.created_at, Date).label("date"),
            func.count(models.User.id).label("count"),
        )
        .filter(
            cast(models.User.created_at, Date) >= start_date,
            cast(models.User.created_at, Date) <= end_date,
        )
        .group_by(cast(models.User.created_at, Date))
        .order_by(cast(models.User.created_at, Date))
        .all()
    )


def get_users_paginated(
    db: Session,
    page: int,
    limit: int,
    search: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
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

    if start_date:
        query = query.filter(cast(models.User.created_at, Date) >= start_date)

    if end_date:
        query = query.filter(cast(models.User.created_at, Date) <= end_date)

    total = query.count()
    users = (
        query.order_by(models.User.created_at.desc(), models.User.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return users, total
