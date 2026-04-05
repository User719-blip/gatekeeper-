from sqlalchemy.orm import Session

from db.models import AdminORM, RefreshTokenORM


def get_admin_by_username(db: Session, username: str) -> AdminORM | None:
    return db.query(AdminORM).filter(AdminORM.username == username).first()

def count_admins(db: Session) -> int:
    return db.query(AdminORM).count()

def create_admin(db: Session, username: str, password_hash: str, role: str = "admin") -> AdminORM:
    admin = AdminORM(
        username=username,
        password_hash=password_hash,
        role=role,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def delete_admin_by_username(db: Session, username: str) -> AdminORM | None:
    admin = get_admin_by_username(db, username)
    if admin is None:
        return None
    db.delete(admin)
    db.commit()
    return admin


def count_superadmins(db: Session) -> int:
    return db.query(AdminORM).filter(AdminORM.role == "superadmin").count()


def save_refresh_token(db: Session, username: str, token_hash: str, expires_at) -> RefreshTokenORM:
    row = RefreshTokenORM(
        admin_username=username,
        token_hash=token_hash,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_refresh_token(db: Session, token_hash: str) -> RefreshTokenORM | None:
    return db.query(RefreshTokenORM).filter(RefreshTokenORM.token_hash == token_hash).first()


def revoke_refresh_token(db: Session, token_hash: str) -> RefreshTokenORM | None:
    row = get_refresh_token(db, token_hash)
    if row is None:
        return None
    row.is_revoked = True
    db.commit()
    db.refresh(row)
    return row