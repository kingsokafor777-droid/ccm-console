"""Pluggable bearer-token verification and closed role policy for ccm-console."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import jwt
from fastapi import HTTPException, status
from jwt import InvalidTokenError

from .models import Principal, Role


class TokenVerifier(Protocol):
    def verify(self, token: str) -> Principal: ...


class DevelopmentHmacTokenVerifier:
    """Local/test HMAC token adapter; deployment must use an external vetted identity path."""

    def __init__(
        self,
        *,
        secret: str,
        issuer: str,
        audience: str,
        now_epoch: Callable[[], int],
    ) -> None:
        if len(secret) < 32:
            raise ValueError("development token secret must be at least 32 characters")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._now_epoch = now_epoch

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"verify_exp": False},
            )
        except InvalidTokenError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc
        expiration = claims.get("exp")
        if not isinstance(expiration, int) or expiration <= self._now_epoch():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="expired bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            role = Role(claims["role"])
            return Principal(
                tenant_id=claims["tenant_id"],
                subject_id=claims["sub"],
                role=role,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid bearer token claims",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc


def issue_development_token(
    principal: Principal,
    *,
    secret: str,
    issuer: str,
    audience: str,
    expires_at_epoch: int,
) -> str:
    """Create a local/test token. This function is not an identity-provider implementation."""

    return str(
        jwt.encode(
            {
                "tenant_id": principal.tenant_id,
                "sub": principal.subject_id,
                "role": principal.role.value,
                "iss": issuer,
                "aud": audience,
                "exp": expires_at_epoch,
            },
            secret,
            algorithm="HS256",
        )
    )


def require_role(principal: Principal, *allowed: Role) -> Principal:
    if principal.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return principal
