from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from config import settings

router = APIRouter()


class UserSettingsResponse(BaseModel):
    email: EmailStr


@router.get("/user/settings", response_model=UserSettingsResponse)
def user_settings() -> UserSettingsResponse:
    return UserSettingsResponse(email=settings.user_email)
