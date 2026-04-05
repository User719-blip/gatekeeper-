from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ApplicationCreate(BaseModel):
    name: str
    description: str | None = None
    model_config = ConfigDict(extra="forbid")

class Application(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    is_approved: bool = False