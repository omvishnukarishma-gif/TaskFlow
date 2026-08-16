"""
routers/auth.py — Authentication endpoints.

Endpoints:
  POST /auth/register        — create a new user account with a password
  POST /auth/login           — verify credentials, return a session token
  POST /auth/logout          — invalidate the current session token
  GET  /auth/me              — verify a session token and return safe user info
  POST /auth/forgot-password — request a password-reset token
  POST /auth/reset-password  — consume a reset token and set a new password

Design notes:
- Session tokens are opaque random strings (secrets.token_urlsafe(32)).
- Sessions are stored in the SQLite `sessions` table (persistent across restarts).
- No JWT — not needed for a single-process application.
- Existing /users endpoints are completely unaffected.
- password_hash is NEVER returned in any response.
- All existing /users, /projects, /tasks endpoints remain anonymous
  (no auth middleware applied to them — verification scripts continue passing).
- Reset tokens: raw token generated with secrets.token_urlsafe(32) (256-bit
  entropy). Only SHA-256(token) is stored — the raw token is never persisted.
- DEV_MODE: when the environment variable TASKFLOW_ENV is not set to
  "production", the raw reset token is printed to the server console AND
  returned in the response as "dev_token". In production the field is omitted
  entirely.  The security model (hashed storage, expiry, single-use) is
  identical in both modes — only the delivery channel differs.
"""

import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth_utils import hash_password, hash_reset_token, verify_password
from backend.dependencies import get_db
from backend.models import PasswordResetToken
from backend.models import Session as SessionModel
from backend.models import User
from backend.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Dev-mode flag
# Set TASKFLOW_ENV=production to suppress dev_token from responses.
# ---------------------------------------------------------------------------
_IS_DEV = os.environ.get("TASKFLOW_ENV", "development").lower() != "production"

# Reset token TTL
_RESET_TOKEN_TTL_MINUTES = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string with timezone offset."""
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(iso_str: str) -> datetime:
    """
    Parse an ISO-8601 UTC string back to a timezone-aware datetime.

    Handles both '+00:00' suffix (Python isoformat()) and 'Z' suffix.
    Always returns a UTC-aware datetime — never naive.
    """
    s = iso_str.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        # Fallback: treat naive strings as UTC (shouldn't happen with _now_iso)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _create_session(user_id: int, db: Session) -> str:
    """Generate a new opaque session token and persist it."""
    token = secrets.token_urlsafe(32)
    sess = SessionModel(token=token, user_id=user_id, created_at=_now_iso())
    db.add(sess)
    db.commit()
    return token


def _get_session_user(token: str, db: Session) -> User | None:
    """Return the User for a valid token, or None."""
    if not token:
        return None
    sess = db.query(SessionModel).filter(SessionModel.token == token).first()
    if sess is None:
        return None
    return sess.user


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account with email + password",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new User row and immediately establish a session.

    - If the email is already in the users table WITHOUT a password_hash,
      the password is set on the existing row (first-time credential setup
      for users created via the existing /users API).
    - If the email is already in the users table WITH a password_hash,
      return 409 Conflict — account already registered.
    - If the email is not in the table, create a new User row.
    """
    existing = db.query(User).filter(User.email == payload.email).first()

    if existing is not None:
        if existing.password_hash is not None:
            # Already registered — do not overwrite credentials.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email is already registered.",
            )
        # Existing user without password — set their password.
        existing.password_hash = hash_password(payload.password)
        # Update name if supplied (keeps existing if the same).
        if payload.name:
            existing.name = payload.name
        db.commit()
        db.refresh(existing)
        user = existing
    else:
        # Brand-new user.
        user = User(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email is already registered.",
            )

    token = _create_session(user.id, db)
    return AuthResponse(
        token=token,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        message="registered",
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email + password and receive a session token",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Verify email + password.  Returns a session token on success.

    Returns 401 for invalid credentials (same error for wrong email or wrong
    password to prevent user-enumeration).
    Returns 403 if the account exists but has no password set yet (user must
    register first via /auth/register to establish credentials).
    """
    user = db.query(User).filter(User.email == payload.email).first()

    # Generic invalid-credentials response (prevent email enumeration).
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    if user is None:
        raise _invalid

    if user.password_hash is None:
        # Account exists but never registered a password.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has no password set. Please register first.",
        )

    if not verify_password(payload.password, user.password_hash):
        raise _invalid

    token = _create_session(user.id, db)
    return AuthResponse(
        token=token,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        message="logged_in",
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Invalidate the current session token",
)
def logout(
    authorization: str = Header(default="", alias="Authorization"),
    db: Session = Depends(get_db),
):
    """
    Delete the session identified by the Bearer token in the Authorization header.

    Always returns 200 — idempotent (if the token is not found, there is
    nothing to invalidate, which is not an error from the client's perspective).
    """
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]

    if token:
        sess = db.query(SessionModel).filter(SessionModel.token == token).first()
        if sess is not None:
            db.delete(sess)
            db.commit()

    return {"detail": "logged_out"}


# ---------------------------------------------------------------------------
# GET /auth/me  (optional convenience — verify a stored token is still valid)
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Verify a session token and return safe user info",
)
def me(
    authorization: str = Header(default="", alias="Authorization"),
    db: Session = Depends(get_db),
):
    """
    Return basic user info for a valid session token.
    Returns 401 if the token is missing or invalid.
    Used by the frontend to restore a session after page refresh.
    """
    token = ""
    if authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]

    user = _get_session_user(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
        )

    return {
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
    }


# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------

_FORGOT_GENERIC_RESPONSE = {
    "detail": (
        "If that email address is registered, a password-reset token has been sent. "
        "Check your email (or the server console in development mode)."
    )
}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a password-reset token",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Issue a time-limited, single-use password-reset token for the given email.

    Security guarantees:
    - Always returns the same HTTP 200 and the same response body, regardless of
      whether the email exists or has a password.  This prevents user enumeration.
    - The raw token is NEVER stored.  Only SHA-256(token) is persisted.
    - In development mode (TASKFLOW_ENV != 'production') the raw token is also
      printed to the server console AND returned as 'dev_token' in the response
      body so the flow is testable without an email provider.
    - In production mode (TASKFLOW_ENV=production) 'dev_token' is absent from
      the response entirely and the token should be delivered via email.
    - Any pre-existing unused, unexpired tokens for the same user are deleted
      before issuing a new one (prevents accumulation / replay of old tokens).
    """
    user = db.query(User).filter(User.email == payload.email).first()

    # Always return the generic response regardless of whether the user exists.
    if user is None or user.password_hash is None:
        # No account or no password set — return generic message, no token.
        return _FORGOT_GENERIC_RESPONSE

    # Delete any existing unused reset tokens for this user to prevent reuse
    # of stale tokens after a new request is made.
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used.is_(False),
    ).delete(synchronize_session=False)

    # Generate a cryptographically random raw token (256-bit entropy).
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(raw_token)

    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=_RESET_TOKEN_TTL_MINUTES)

    prt = PasswordResetToken(
        token_hash=token_hash,
        user_id=user.id,
        created_at=now.isoformat(),
        expires_at=expires.isoformat(),
        used=False,
    )
    db.add(prt)
    db.commit()

    # Dev-mode: print raw token to the server console so it can be used
    # without an email provider.  This line is the ONLY place the raw token
    # is ever written anywhere; it is not stored in the database.
    if _IS_DEV:
        print(
            f"\n[DEV] Password reset token for {user.email}:\n"
            f"  {raw_token}\n"
            f"  (expires in {_RESET_TOKEN_TTL_MINUTES} minutes)\n",
            flush=True,
        )
        return {**_FORGOT_GENERIC_RESPONSE, "dev_token": raw_token}

    # Production: return only the generic message (token delivered via email).
    return _FORGOT_GENERIC_RESPONSE


# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------

@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Consume a reset token and set a new password",
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Validate the reset token and update the user's password.

    Security guarantees:
    - Token is looked up by its SHA-256 hash — the raw token is never stored.
    - Expiry is checked by parsing expires_at as a timezone-aware UTC datetime
      and comparing against datetime.now(timezone.utc) — NOT by lexical string
      comparison.
    - A used token is permanently invalid (idempotent safety: re-submitting the
      same token after success returns the same 400 as an unknown token).
    - All existing sessions for the user are deleted after a successful reset,
      invalidating any currently logged-in devices.
    - The user is NOT automatically logged in — they must sign in manually.
    - The same generic 400 is returned for expired, used, and nonexistent tokens
      to avoid leaking token state to an attacker.
    """
    _invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token.",
    )

    token_hash = hash_reset_token(payload.token)
    prt = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).first()

    if prt is None:
        raise _invalid_token

    if prt.used:
        raise _invalid_token

    # Parse expires_at as a timezone-aware UTC datetime and compare properly.
    try:
        expires_at_dt = _parse_iso(prt.expires_at)
    except (ValueError, TypeError):
        # Malformed stored value — treat as expired.
        raise _invalid_token

    if datetime.now(timezone.utc) >= expires_at_dt:
        raise _invalid_token

    # All checks passed — update the password.
    user = prt.user
    user.password_hash = hash_password(payload.new_password)

    # Mark this token as used (permanent, single-use).
    prt.used = True

    # Invalidate ALL existing sessions for this user so any currently
    # logged-in devices are forced to re-authenticate with the new password.
    db.query(SessionModel).filter(SessionModel.user_id == user.id).delete(
        synchronize_session=False
    )

    db.commit()

    return {"detail": "Password updated successfully. Please log in with your new password."}
