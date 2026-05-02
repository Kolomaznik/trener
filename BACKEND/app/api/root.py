from fastapi import APIRouter
from pydantic import BaseModel

from config import settings

router = APIRouter()


class RootResponse(BaseModel):
    app: str


@router.get("/", response_model=RootResponse)
def root() -> RootResponse:
    return RootResponse(app=settings.app_name)
