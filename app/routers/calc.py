"""Faraid calculation + heir catalogue endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.faraid import (
    HEIR_KEYS,
    HEIR_LABELS,
    GENDER,
    calculate_distribution,
)
from app.models import User
from app.routers.deps import get_current_user
from app.routers.history import save_calculation
from app.schemas.schemas import (
    CalculateRequest,
    CalculationResponse,
    HeirCatalogueOut,
)

router = APIRouter(prefix="/api", tags=["calculation"])


@router.get("/heirs", response_model=HeirCatalogueOut)
def heir_catalogue() -> HeirCatalogueOut:
    """List every supported heir type for the frontend picker."""
    return HeirCatalogueOut(
        heirs=[
            {"key": k, "label": HEIR_LABELS[k], "is_male": GENDER[k]}
            for k in HEIR_KEYS
        ]
    )


@router.post("/calculate", response_model=CalculationResponse)
def calculate(
    payload: CalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CalculationResponse:
    """Compute the Faraid distribution (exact fractions, optional PKR amounts)."""
    try:
        result = calculate_distribution(
            deceased_gender=payload.deceased_gender,
            heirs=payload.heirs,
            counts=payload.counts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from None

    result_dict = result.to_dict(estate_value=payload.estate_value)
    save_calculation(db, current_user, payload, result_dict)

    return CalculationResponse(**result_dict)
