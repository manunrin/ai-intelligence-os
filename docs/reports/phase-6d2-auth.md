# Phase 6-D.2: Authentication & Authorization

**Date:** 2026-07-16  
**Status:** COMPLETE  
**Scope:** Backend-only (JWT auth, user registration/login, protected endpoints)

## Goal

Implement JWT-based authentication for all write endpoints created in Phase 6-D.1.

## Architecture

```
Client → Router (Depends(get_current_user)) → OAuth2PasswordBearer → JWT decode → DB lookup → User model
```

## Components Implemented

### User Model (`database/models/user.py`)
| Field | Type | Constraints |
|-------|------|-------------|
| id | UUID | PK, default uuid4 |
| username | str(64) | unique, nullable=False |
| email | str(255) | unique, nullable=False |
| hashed_password | str(255) | bcrypt hash, nullable=False |
| role | str(16) | "admin" or "user", default="user" |
| is_active | bool | default=True |
| last_login_at | datetime | nullable, updated on login |
| created_at | datetime | default _utcnow |
| updated_at | datetime | default _utcnow, onupdate=_utcnow |

### Password Hashing (`utils/auth.py`)
- Uses `bcrypt` library directly (passlib 1.7.4 incompatible with bcrypt 5.x)
- `hash_password()` — generates salted bcrypt hash
- `verify_password()` — constant-time comparison via bcrypt.checkpw

### JWT Tokens (`utils/jwt.py`)
- Algorithm: HS256 (configurable via Settings)
- Subject: user UUID (not username per requirements)
- Access token expiry: 30 minutes (configurable)
- Refresh tokens deferred to later phase

### Pydantic Schemas (`schemas/user.py`)
| Schema | Fields | Validation |
|--------|--------|------------|
| UserCreate | username, email, password | username min 3 chars, password min 8 chars |
| UserLogin | username, password | required |
| TokenResponse | access_token, token_type | token_type defaults to "bearer" |
| UserResponse | id, username, email, role, is_active, last_login_at, created_at | full profile |

### Endpoints
| Method | Path | Auth Required | Description |
|--------|------|---------------|-------------|
| POST | /api/v1/auth/register | No | Create user account |
| POST | /api/v1/auth/login | No | Get JWT access token |
| GET | /api/v1/auth/me | Yes | Current user profile |
| POST | /api/v1/articles | Yes | Create article |
| PUT | /api/v1/articles/{id} | Yes | Update article |
| DELETE | /api/v1/articles/{id} | Yes | Delete article |
| POST | /api/v1/tasks | Yes | Create task |
| PUT | /api/v1/tasks/{id} | Yes | Update task |
| DELETE | /api/v1/tasks/{id} | Yes | Delete task |
| POST | /api/v1/knowledge | Yes | Create knowledge item |
| PUT | /api/v1/knowledge/{id} | Yes | Update knowledge item |
| DELETE | /api/v1/knowledge/{id} | Yes | Delete knowledge item |
| POST | /api/v1/reports | Yes | Create report |
| POST | /api/v1/agents/{id}/run | Yes | Trigger agent run |

### RBAC Foundation
- `get_current_user()` dependency — decodes JWT, looks up user, checks active status
- `require_role(*roles)` dependency factory — checks user.role against allowed roles
- Role stored as string in DB (not Python enum) for simplicity

### Database Migration
- Alembic migration `0003_add_users_table` with indexes on username and email

## Test Results

- **241 total unit tests** (108 existing + 95 from Phase 6-D.1 + 38 new)
- New test files: `test_auth_utils.py`, `test_jwt_utils.py`, `test_user_service.py`, `test_auth.py`, `test_protected_endpoints.py`

## Known Limitations

1. No refresh token endpoint (deferred)
2. No frontend auth UI
3. Role system is basic string comparison (no granular permissions)
4. JWT secret must be set via env var (no default in production)

## Next Steps

Phase 6-D.3: Refresh tokens, frontend auth integration, password reset flow.
