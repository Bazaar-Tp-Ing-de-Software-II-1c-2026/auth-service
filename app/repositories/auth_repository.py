from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_identifier(db: Session, identifier: str):
    return (
        db.query(models.User)
        .filter(
            or_(
                models.User.email == identifier,
                models.User.username == identifier,
            )
        )
        .first()
    )


def get_user_by_id(db: Session, user_id: int):
    return db.get(models.User, user_id)


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: models.User):
    db.add(user)
    db.flush()
    return user


def save(db: Session, entity):
    db.add(entity)
    db.commit()
    return entity


def generate_unique_username(db: Session, base: str) -> str:
    username = base
    counter = 1

    while get_user_by_username(db, username):
        username = f"{base}{counter}"
        counter += 1

    return username
