from pydantic import BaseModel, ConfigDict, Field

class AdminCreate(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=72)
    model_config = ConfigDict(extra="forbid")

class AdminLogin(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=72)
    model_config = ConfigDict(extra="forbid")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str
    model_config = ConfigDict(extra="forbid")
