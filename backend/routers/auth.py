"""Auth router — user registration and login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..schemas.response import APIResponse
from ..schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from .deps import get_db

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
)


@router.post(
    "/register",
    summary="Register a new user",
    description="Create a new user account.",
    operation_id="registerUser",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(data: UserCreate, db=Depends(get_db)):
    from ..services.user_service import UserService

    service = UserService(db)
    try:
        user = await service.register(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return APIResponse(success=True, data=user, error=None)


@router.post(
    "/login",
    summary="Login",
    description="Authenticate with username and password, returns JWT access token.",
    operation_id="loginUser",
    response_model=APIResponse[TokenResponse],
)
async def login(data: UserLogin, db=Depends(get_db)):
    from ..services.user_service import UserService

    service = UserService(db)
    user = await service.authenticate(data)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    from ..config import get_settings
    from ..utils.jwt import create_access_token

    settings = get_settings()
    token = create_access_token(str(user.id), settings)
    return APIResponse(success=True, data={"access_token": token, "token_type": "bearer"}, error=None)


@router.get(
    "/me",
    summary="Get current user",
    description="Return profile of the authenticated user.",
    operation_id="getCurrentUser",
    response_model=APIResponse[UserResponse],
)
async def get_me(token: str, db=Depends(get_db)):
    """Protected endpoint — requires valid JWT."""
    from ..config import get_settings
    from ..utils.jwt import decode_access_token

    settings = get_settings()
    payload = decode_access_token(token, settings)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    from ..services.user_service import UserService

    service = UserService(db)
    user = await service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return APIResponse(success=True, data=user, error=None)
