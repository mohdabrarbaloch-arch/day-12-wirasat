"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.faraid import HEIR_KEYS


# Auth


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=120)

    @field_validator("password")
    @classmethod
    def password_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password cannot be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    created_at: datetime


# Calculation


class CalculateRequest(BaseModel):
    deceased_gender: str = Field(default="male", pattern="^(male|female)$")
    estate_value: float = Field(default=0.0, ge=0.0, le=1e12)
    heirs: list[str] = Field(min_length=1, max_length=30)
    counts: dict[str, int] | None = None

    @field_validator("heirs")
    @classmethod
    def validate_heirs(cls, v: list[str]) -> list[str]:
        unknown = [h for h in v if h not in HEIR_KEYS]
        if unknown:
            raise ValueError(f"Unknown heir key(s): {', '.join(unknown)}")
        return v


class HeirOut(BaseModel):
    key: str
    label: str
    count: int
    share_numerator: int
    share_denominator: int
    share_decimal: float
    kind: str
    is_male: bool
    amount: float | None = None
    amount_display: str | None = None


class CalculationResponse(BaseModel):
    mode: str
    shares_total_n: int
    shares_total_d: int
    adjusted_total_n: int
    adjusted_total_d: int
    excluded: list[str]
    notes: list[str]
    entries: list[HeirOut]


class CalculationRecordOut(CalculationResponse):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    deceased_gender: str
    estate_value: float
    input_heirs: str
    created_at: datetime


class HeirCatalogueOut(BaseModel):
    heirs: list[dict[str, str | bool]]


class MessageOut(BaseModel):
    message: str
