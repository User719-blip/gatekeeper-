from uuid import UUID

from sqlalchemy.orm import Session

from db.models import ApplicationORM
from schema.schema import Application, ApplicationCreate


class ApplicationStore:
    def create(self, payload: ApplicationCreate, db: Session) -> Application:
        row = ApplicationORM(
            name=payload.name,
            description=payload.description,
            is_approved=False,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        return Application(
            id=UUID(row.id),
            name=row.name,
            description=row.description,
            is_approved=row.is_approved,
        )

    def list_all(self, db: Session) -> list[Application]:
        rows = db.query(ApplicationORM).all()
        return [
            Application(
                id=UUID(row.id),
                name=row.name,
                description=row.description,
                is_approved=row.is_approved,
            )
            for row in rows
        ]

    def approve(self, application_id: UUID, db: Session) -> Application | None:
        row = db.query(ApplicationORM).filter(ApplicationORM.id == str(application_id)).first()
        if row is None:
            return None

        row.is_approved = True
        db.commit()
        db.refresh(row)

        return Application(
            id=UUID(row.id),
            name=row.name,
            description=row.description,
            is_approved=row.is_approved,
        )

    def delete(self, application_id: UUID, db: Session) -> Application | None:
        row = db.query(ApplicationORM).filter(ApplicationORM.id == str(application_id)).first()
        if row is None:
            return None

        deleted = Application(
            id=UUID(row.id),
            name=row.name,
            description=row.description,
            is_approved=row.is_approved,
        )
        db.delete(row)
        db.commit()
        return deleted