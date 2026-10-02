from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole

class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    role: UserRole
    technician_id: int | None = None

class UserCreate(UserBase):
    password: str = Field(min_length=8)


# note that we are not adding the password field to the UserRead schema,
# since we do not want to expose the hashed password in API responses.
class UserRead(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(UserBase):
    # If omitted, keep the existing password.
    password: str | None = Field(default=None, min_length=8)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"