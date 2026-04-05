from collections.abc import Generator

def get_db() -> Generator:
    from db.database import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()