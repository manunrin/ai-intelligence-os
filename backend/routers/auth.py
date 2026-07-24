"""Auth router — user registration, login, refresh, and logout."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..schemas.error import ErrorResponse
from ..schemas.response import APIResponse
from ..schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from .deps import get_current_user, get_redis_client, get_user_service
from ..config import get_settings
from ..rate_limiter import limiter

logger = logging.getLogger(__name__)


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


# ── Register ──────────────────────────────────────────────────────────


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


# ── Login ─────────────────────────────────────────────────────────────


@router.post(
    "/login",
    summary="Login",
    description="Authenticate with username and password. Returns a short-lived access token (JWT) and sets an HttpOnly refresh token cookie.",
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

    from ..utils.jwt import create_access_token, create_refresh_token

    settings = get_settings()
    access_token = create_access_token(str(user.id), settings)
    refresh_token_str, _ = create_refresh_token(str(user.id), settings)

    # Persist refresh token hash in Redis
    try:
        store = get_redis_client(request)
        if store is not None:
            await store.store(str(user.id), refresh_token_str)
    except Exception:
        logger.warning("Failed to store refresh token in Redis — login succeeds but refresh will not work", exc_info=True)

    resp = JSONResponse(
        content=APIResponse(
            success=True,
            data={"access_token": access_token, "token_type": "bearer"},
            error=None,
        ).model_dump_json(),
    )
    resp.set_cookie(
        key="aio_refresh_token",
        value=refresh_token_str,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/",
    )
    return resp


# ── Me ────────────────────────────────────────────────────────────────


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


# ── Refresh ───────────────────────────────────────────────────────────


@router.post(
    "/refresh",
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access token. Supports one-use rotation.",
    operation_id="refreshAccessToken",
    response_model=APIResponse[TokenResponse],
)
async def refresh_token(request: Request):
    """Issue a new access token using a refresh token from the aio_refresh_token cookie.

    On success: returns a new access token + sets a rotated refresh token cookie.
    On failure: 401 if token is missing/invalid/expired; 503 if Redis is unavailable.
    """
    settings = get_settings()
    refresh_token_str = request.cookies.get("aio_refresh_token")

    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    store = get_redis_client(request)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token store unavailable",
        )

    user_id = await store.validate(refresh_token_str)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Issue new access token + rotated refresh token
    from ..utils.jwt import create_access_token, create_refresh_token

    new_access = create_access_token(user_id, settings)
    new_refresh_str, _ = create_refresh_token(user_id, settings)
    await store.rotate(refresh_token_str, new_refresh_str, user_id)

    resp = JSONResponse(
        content=APIResponse(
            success=True,
            data={"access_token": new_access, "token_type": "bearer"},
            error=None,
        ).model_dump_json(),
    )
    resp.set_cookie(
        key="aio_refresh_token",
        value=new_refresh_str,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain or None,
        max_age=settings.jwt_refresh_token_expire_days * 86400,
        path="/",
    )
    return resp


# ── Logout ────────────────────────────────────────────────────────────


@router.post(
    "/logout",
    summary="Logout",
    description="Invalidate the current refresh token. Access tokens expire naturally at their TTL.",
    operation_id="logoutUser",
    response_model=APIResponse,
)
async def logout(request: Request):
    """Clear the refresh token cookie and revoke it in Redis."""
    refresh_token_str = request.cookies.get("aio_refresh_token")

    if refresh_token_str:
        try:
            store = get_redis_client(request)
            if store is not None:
                await store.revoke(refresh_token_str)
        except Exception:
            logger.warning("Failed to revoke refresh token on logout", exc_info=True)

    resp = JSONResponse(
        content=APIResponse(success=True, data=None, error=None).model_dump_json(),
    )
    resp.delete_cookie(key="aio_refresh_token", path="/")
    return resp
