from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    role: UserRole
    technician_id: int | None = None


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserRead(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(UserBase):
    password: str | None = Field(default=None, min_length=8)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
