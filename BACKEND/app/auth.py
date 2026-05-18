import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, HttpUrl

from config import settings

_bearer = HTTPBearer(auto_error=True)
_optional_bearer = HTTPBearer(auto_error=False)


class GoogleUser(BaseModel):
    model_config = ConfigDict(extra="allow")

    sub: str
    email: EmailStr
    name: str | None = None
    picture: HttpUrl | None = None


async def _fetch_google_userinfo(token: str) -> GoogleUser:
    """Verify a Google access token against the userinfo endpoint.

    Raises HTTPException(502) on network failure and HTTPException(401) on
    a non-200 response from Google.
    """
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


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> GoogleUser:
    return await _fetch_google_userinfo(credentials.credentials)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
) -> GoogleUser | None:
    """Resolve the bearer token if one was sent; never fails the request.

    Returns ``None`` when no token was sent or when Google rejects it — the
    endpoint then renders the anonymous view. The intentional silencing here
    is the reason this helper exists separately from ``get_current_user``.
    """
    if credentials is None:
        return None
    try:
        return await _fetch_google_userinfo(credentials.credentials)
    except HTTPException:
        return None
