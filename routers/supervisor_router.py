from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_supervisor
from schemas import (
    User,
    AnomalyRecord, AnomalyType, AnomalyStatus, AnomalyReview, AnomalyRecordUpdate,
    Reservation, ReservationStatus,
    MessageResponse, AnomalyStatistics,
    AnomalyRecordWithRelations, AnomalyResolveData, AnomalyTypeDistribution,
    AreaAnomalySummary,
)
from database import db

router = APIRouter(prefix="/supervisor", tags=["监督人员"])


@router.get("/anomalies", response_model=List[AnomalyRecord])
def list_anomalies(
    status_filter: Optional[AnomalyStatus] = None,
    anomaly_type: Optional[AnomalyType] = None,
    reservation_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: User = Depends(require_supervisor),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    return db.list_anomaly_records_enhanced(
        status=status_filter,
        anomaly_type=anomaly_type,
        reservation_id=reservation_id,
        locker_id=locker_id,
        start_date=sd,
        end_date=ed,
    )


@router.get("/anomalies/{record_id}", response_model=AnomalyRecord)
def get_anomaly(record_id: str, _: User = Depends(require_supervisor)):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    return record


@router.post("/anomalies/{record_id}/confirm", response_model=AnomalyRecord)
def confirm_anomaly(
    record_id: str,
    review_notes: Optional[str] = None,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    if record.status != AnomalyStatus.PENDING:
        raise HTTPException(status_code=400, detail="仅待处理状态的异常可确认")
    review = AnomalyReview(
        status=AnomalyStatus.CONFIRMED,
        reviewer=current_user.username,
        review_notes=review_notes,
    )
    return db.review_anomaly(record_id, review)


@router.post("/anomalies/{record_id}/reject", response_model=AnomalyRecord)
def reject_anomaly(
    record_id: str,
    review_notes: str,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    if record.status not in {AnomalyStatus.PENDING, AnomalyStatus.CONFIRMED}:
        raise HTTPException(status_code=400, detail="仅待处理或已确认状态的异常可驳回")
    review = AnomalyReview(
        status=AnomalyStatus.REJECTED,
        reviewer=current_user.username,
        review_notes=review_notes,
    )
    return db.review_anomaly(record_id, review)


@router.post("/anomalies/{record_id}/resolve", response_model=AnomalyRecord)
def resolve_anomaly(
    record_id: str,
    review_notes: Optional[str] = None,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    if record.status not in {AnomalyStatus.PENDING, AnomalyStatus.CONFIRMED}:
        raise HTTPException(status_code=400, detail="仅待处理或已确认状态的异常可标记已解决")
    review = AnomalyReview(
        status=AnomalyStatus.RESOLVED,
        reviewer=current_user.username,
        review_notes=review_notes,
    )
    return db.review_anomaly(record_id, review)


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


@router.put("/anomalies/{record_id}", response_model=AnomalyRecord)
def update_anomaly(
    record_id: str,
    data: AnomalyRecordUpdate,
    _: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    updated = db.update_anomaly_record(record_id, data)
    if not updated:
        raise HTTPException(status_code=500, detail="更新异常记录失败")
    return updated


@router.get("/anomalies/pending", response_model=List[AnomalyRecord])
def list_pending_anomalies(_: User = Depends(require_supervisor)):
    return db.list_anomaly_records(status=AnomalyStatus.PENDING)


@router.get("/anomalies/statistics", response_model=AnomalyStatistics)
def get_anomaly_statistics(_: User = Depends(require_supervisor)):
    return db.get_anomaly_statistics()


@router.get("/overtime-reservations", response_model=List[Reservation])
def list_overtime_reservations(_: User = Depends(require_supervisor)):
    return db.list_reservations(status=ReservationStatus.OVERTIME)


@router.get("/anomaly-types", response_model=List[dict])
def list_anomaly_types(_: User = Depends(require_supervisor)):
    type_labels = {
        AnomalyType.NO_SHOW: "未签到",
        AnomalyType.OVERTIME: "超时使用",
        AnomalyType.DISABLED_LOCKER_RESERVED: "停用储物格仍有预约",
        AnomalyType.RELEASE_CONFIRM_MISSING: "释放未确认",
        AnomalyType.ABNORMAL_OCCUPANCY: "异常占用",
    }
    return [
        {"value": t.value, "label": type_labels.get(t, t.value)}
        for t in AnomalyType
    ]


@router.get("/anomaly-statuses", response_model=List[dict])
def list_anomaly_statuses(_: User = Depends(require_supervisor)):
    status_labels = {
        AnomalyStatus.PENDING: "待处理",
        AnomalyStatus.CONFIRMED: "已确认",
        AnomalyStatus.RESOLVED: "已解决",
        AnomalyStatus.REJECTED: "已驳回",
    }
    return [
        {"value": s.value, "label": status_labels.get(s, s.value)}
        for s in AnomalyStatus
    ]


@router.get("/anomalies-with-relations", response_model=List[AnomalyRecordWithRelations])
def list_anomalies_with_relations(
    status_filter: Optional[AnomalyStatus] = None,
    anomaly_type: Optional[AnomalyType] = None,
    area_id: Optional[str] = None,
    reservation_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: User = Depends(require_supervisor),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    return db.list_anomaly_with_relations(
        status=status_filter,
        anomaly_type=anomaly_type,
        area_id=area_id,
        reservation_id=reservation_id,
        locker_id=locker_id,
        start_date=sd,
        end_date=ed,
    )


@router.post("/anomalies/{record_id}/resolve-with-notes", response_model=AnomalyRecord)
def resolve_anomaly_with_notes(
    record_id: str,
    data: AnomalyResolveData,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    resolved = db.resolve_anomaly_with_notes(record_id, data, reviewer=current_user.username)
    if not resolved:
        raise HTTPException(status_code=400, detail="仅待处理或已确认状态的异常可标记已解决")
    return resolved


@router.post("/anomalies/{record_id}/confirm-with-notes", response_model=AnomalyRecord)
def confirm_anomaly_with_notes(
    record_id: str,
    review_notes: Optional[str] = None,
    handling_notes: Optional[str] = None,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    if record.status != AnomalyStatus.PENDING:
        raise HTTPException(status_code=400, detail="仅待处理状态的异常可确认")
    review = AnomalyReview(
        status=AnomalyStatus.CONFIRMED,
        reviewer=current_user.username,
        review_notes=review_notes,
    )
    if handling_notes:
        if record.supplementary_notes:
            record.supplementary_notes = record.supplementary_notes + "\n处理建议: " + handling_notes
        else:
            record.supplementary_notes = "处理建议: " + handling_notes
    return db.review_anomaly(record_id, review)


@router.post("/anomalies/{record_id}/reject-with-notes", response_model=AnomalyRecord)
def reject_anomaly_with_notes(
    record_id: str,
    review_notes: str,
    handling_notes: Optional[str] = None,
    current_user: User = Depends(require_supervisor),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    if record.status not in {AnomalyStatus.PENDING, AnomalyStatus.CONFIRMED}:
        raise HTTPException(status_code=400, detail="仅待处理或已确认状态的异常可驳回")
    review = AnomalyReview(
        status=AnomalyStatus.REJECTED,
        reviewer=current_user.username,
        review_notes=review_notes,
    )
    if handling_notes:
        if record.supplementary_notes:
            record.supplementary_notes = record.supplementary_notes + "\n补充说明: " + handling_notes
        else:
            record.supplementary_notes = "补充说明: " + handling_notes
    return db.review_anomaly(record_id, review)


@router.get("/anomaly-type-distribution", response_model=List[AnomalyTypeDistribution])
def get_anomaly_type_distribution(
    area_id: Optional[str] = None,
    _: User = Depends(require_supervisor),
):
    return db.get_anomaly_type_distribution(area_id=area_id)


@router.get("/area-anomaly-summary", response_model=List[AreaAnomalySummary])
def get_area_anomaly_summary(_: User = Depends(require_supervisor)):
    return db.get_area_anomaly_summary()


@router.get("/statistics/enhanced", response_model=AnomalyStatistics)
def get_anomaly_statistics_enhanced(
    area_id: Optional[str] = None,
    _: User = Depends(require_supervisor),
):
    return db.get_anomaly_statistics(area_id=area_id)
