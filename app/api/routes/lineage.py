from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.lineage.service import clean_batch_lineage, data_lineage
from app.storage.db import get_db_session

router = APIRouter(prefix="/api/v1/lineage", tags=["lineage"])


@router.get("/clean-batches/{clean_batch_id}")
def clean_batch(clean_batch_id: uuid.UUID, session: Session = Depends(get_db_session)) -> dict:
    result = clean_batch_lineage(session, clean_batch_id)
    if result is None:
        raise HTTPException(status_code=404, detail="clean batch not found")
    return result


@router.get("/data/{data_item}")
def data(
    data_item: str,
    security_code: str | None = Query(default=None),
    trade_date: date | None = Query(default=None),
    exchange_code: str | None = Query(default=None),
    calendar_date: date | None = Query(default=None),
    session: Session = Depends(get_db_session),
) -> dict:
    try:
        result = data_lineage(
            session,
            data_item=data_item,
            security_code=security_code,
            trade_date=trade_date,
            exchange_code=exchange_code,
            calendar_date=calendar_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="clean data not found")
    return result
