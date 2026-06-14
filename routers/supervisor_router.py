from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_supervisor
from schemas import (
    User,
    AnomalyRecord, AnomalyType, AnomalyStatus, AnomalyReview,
    Reservation, ReservationStatus,
    MessageResponse,
)
from database import db

router = APIRouter(prefix="/supervisor", tags=["监督人员"])


@router.get("/anomalies", response_model=List[AnomalyRecord])
def list_anomalies(
    status_filter: Optional[AnomalyStatus] = None,
    anomaly_type: Optional[AnomalyType] = None,
    _: User = Depends(require_supervisor),
):
    return db.list_anomaly_records(status=status_filter, anomaly_type=anomaly_type)


@router.get("/anomalies/{record_id}", response_model=AnomalyRecord)
def get_anomaly(record_id: str, _: User = Depends(require_supervisor)):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    return record


@router.post("/anomalies/{record_id}/review", response_model=AnomalyRecord)
def review_anomaly(
    record_id: str,
    data: AnomalyReview,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    data.reviewer = current_user.username
    reviewed = db.review_anomaly(record_id, data)
    return reviewed


@router.get("/anomalies/pending", response_model=List[AnomalyRecord])
def list_pending_anomalies(_: User = Depends(require_supervisor)):
    return db.list_anomaly_records(status=AnomalyStatus.PENDING)


@router.get("/overtime-reservations", response_model=List[Reservation])
def list_overtime_reservations(_: User = Depends(require_supervisor)):
    return db.list_reservations(status=ReservationStatus.OVERTIME)
