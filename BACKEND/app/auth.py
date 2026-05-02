import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl

from config import settings

_bearer = HTTPBearer(auto_error=True)


class GoogleUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    sub: str
    email: EmailStr
    email_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: HttpUrl | None = None
    locale: str | None = None
    hd: str | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> GoogleUser:
    token = credentials.credentials
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach Google to verify access token.",
        ) from error

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Google access token.",
        )

    return GoogleUser.model_validate(response.json())
