from typing import Annotated
from fastapi import APIRouter, Depends
from server.auth import basic_auth

router = APIRouter(prefix="/flags", tags=["Flags"])


@router.get("/")
def test(username: Annotated[str, Depends(basic_auth)]):
    return {"message": f"Hello, {username}!"}
