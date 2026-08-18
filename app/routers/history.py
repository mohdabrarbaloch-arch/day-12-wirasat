"""Saved calculation history for authenticated users."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Calculation, User
from app.routers.deps import get_current_user
from app.schemas.schemas import CalculationRecordOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[CalculationRecordOut])
def list_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """Return the most recent calculations for the current user."""
    limit = max(1, min(limit, 100))
    rows = db.scalars(
        select(Calculation)
        .where(Calculation.user_id == current_user.id)
        .order_by(Calculation.created_at.desc())
        .limit(limit)
    ).all()
    return [_record_out(r) for r in rows]


@router.get("/{calculation_id}", response_model=CalculationRecordOut)
def get_history_item(
    calculation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    row = db.get(Calculation, calculation_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found")
    return _record_out(row)


@router.delete("/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(
    calculation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    row = db.get(Calculation, calculation_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calculation not found")
    db.delete(row)
    db.commit()


def save_calculation(db: Session, user: User, payload, result_dict: dict) -> Calculation:
    """Persist a calculation to history (called from calc router)."""
    row = Calculation(
        user_id=user.id,
        deceased_gender=payload.deceased_gender,
        estate_value=payload.estate_value,
        input_heirs=json.dumps(payload.heirs),
        result_json=json.dumps(result_dict),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _record_out(row: Calculation) -> dict:
    """Flatten a stored Calculation row into the response schema."""
    result = json.loads(row.result_json)
    return {
        "id": row.id,
        "user_id": row.user_id,
        "deceased_gender": row.deceased_gender,
        "estate_value": row.estate_value,
        "input_heirs": row.input_heirs,
        "created_at": row.created_at.isoformat(),
        "mode": result.get("mode", "normal"),
        "shares_total_n": result.get("shares_total_n", 0),
        "shares_total_d": result.get("shares_total_d", 1),
        "adjusted_total_n": result.get("adjusted_total_n", 0),
        "adjusted_total_d": result.get("adjusted_total_d", 1),
        "excluded": result.get("excluded", []),
        "notes": result.get("notes", []),
        "entries": result.get("entries", []),
    }
