import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, model_validator


@dataclass(frozen=True)
class AuthSettings:
    secret: str = field(repr=False)
    issuer: str = "aegisops-local"
    audience: str = "aegisops-console"
    lifetime_seconds: int = 900

    def __post_init__(self) -> None:
        if len(self.secret.encode()) < 32:
            raise ValueError("JWT signing key must contain at least 32 bytes")
        if self.lifetime_seconds != 900:
            raise ValueError("Local viewer tokens must expire after 15 minutes")

    @classmethod
    def from_environment(cls) -> "AuthSettings":
        return cls(secret=os.environ["JWT_SECRET"])


class TokenClaims(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    sub: str = Field(pattern=r"^[A-Za-z0-9_.@-]{1,128}$")
    role: str = Field(min_length=1, max_length=64)
    iss: str
    aud: str
    iat: int = Field(ge=0)
    nbf: int = Field(ge=0)
    exp: int = Field(gt=0)

    @model_validator(mode="after")
    def bounded_lifetime(self):
        if self.nbf != self.iat or not 0 < self.exp - self.iat <= 900:
            raise ValueError("Invalid local token lifetime")
        return self


ROLE_PERMISSIONS = {"viewer": frozenset({"events:read", "investigations:read"})}
bearer = HTTPBearer(auto_error=False, scheme_name="ViewerJWT", bearerFormat="JWT",
                    description="Local 15-minute viewer token; generate with auth_cli.py.")


def issue_viewer_token(settings: AuthSettings, subject: str = "local-operator",
                       now: datetime | None = None) -> str:
    instant = now or datetime.now(timezone.utc)
    if instant.utcoffset() is None:
        raise ValueError("Token issue time must include a timezone")
    issued_at = int(instant.timestamp())
    claims = TokenClaims(sub=subject, role="viewer", iss=settings.issuer,
                         aud=settings.audience, iat=issued_at, nbf=issued_at,
                         exp=int((instant + timedelta(seconds=900)).timestamp()))
    return jwt.encode(claims.model_dump(), settings.secret, algorithm="HS256")


def authenticate(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> TokenClaims:
    if credentials is None:
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    settings: AuthSettings = request.app.state.auth_settings
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret, algorithms=["HS256"],
            issuer=settings.issuer, audience=settings.audience,
            options={"require": ["exp", "iat", "nbf", "iss", "aud", "sub", "role"],
                     "strict_aud": True},
        )
        principal = TokenClaims.model_validate(payload)
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"}) from None
    request.state.principal = principal.sub
    return principal


def require_event_reader(principal: Annotated[TokenClaims, Depends(authenticate)]) -> TokenClaims:
    if "events:read" not in ROLE_PERMISSIONS.get(principal.role, frozenset()):
        raise HTTPException(403, "Role cannot read events")
    return principal


def require_run_reader(principal: Annotated[TokenClaims, Depends(authenticate)]) -> TokenClaims:
    if "investigations:read" not in ROLE_PERMISSIONS.get(principal.role, frozenset()):
        raise HTTPException(403, "Role cannot read investigations")
    return principal
