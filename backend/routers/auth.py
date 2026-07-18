"""Auth router — user registration and login."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..schemas.error import ErrorResponse
from ..schemas.response import APIResponse
from ..schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from .deps import get_current_user, get_user_service
from ..config import get_settings
from ..rate_limiter import limiter


def _login_rate_limit():
    """Return rate limit string from settings."""
    s = get_settings()
    return f"{s.rate_limit_login_requests} per {s.rate_limit_login_window_seconds} seconds"


router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized — invalid or missing token"},
        403: {"model": ErrorResponse, "description": "Forbidden — account deactivated or insufficient role"},
        404: {"model": ErrorResponse, "description": "Resource not found"},
        409: {"model": ErrorResponse, "description": "Conflict — username already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.post(
    "/register",
    summary="Register a new user",
    description="Create a new user account.",
    operation_id="registerUser",
    response_model=APIResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(_login_rate_limit())
async def register(data: UserCreate, request: Request, service: UserService = Depends(get_user_service)):
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
@limiter.limit(_login_rate_limit())
async def login(data: UserLogin, request: Request, service: UserService = Depends(get_user_service)):
    user = await service.authenticate(data)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
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
async def get_me(current_user: Any = Depends(get_current_user), service: UserService = Depends(get_user_service)):
    """Protected endpoint — requires valid JWT."""
    user = await service.get_user(current_user.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return APIResponse(success=True, data=user, error=None)
