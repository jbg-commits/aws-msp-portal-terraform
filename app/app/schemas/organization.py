from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class OrganizationCreate(BaseModel):
    """Engineer-only: creates an Organization and its first Client user together."""

    org_name: str = Field(min_length=1, max_length=200)
    client_email: EmailStr
    client_full_name: str = Field(min_length=1, max_length=200)


class ClientUserCreate(BaseModel):
    """Engineer-only: adds another Client user to an existing Organization."""

    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
