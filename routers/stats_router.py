from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_any_authenticated, require_supervisor
from schemas import (
    User,
    Reservation, ReservationStatus,
    Locker, LockerStatus, LockerUpdate,
    AnomalyRecord, AnomalyType, AnomalyStatus, AnomalyRecordCreate,
    LockerOccupancyRate, OvertimeRankingItem,
    AnomalyStatistics, ReservationFulfillmentDetail, LockerAvailabilityCheck,
    ReservationWithFulfillment, AnomalyTypeDistribution, AreaAnomalySummary,
    FulfillmentOverview, AnomalyRecordWithRelations,
)
from database import db
from config import settings

router = APIRouter(prefix="/api", tags=["查询统计与异常检测"])


def run_anomaly_detection() -> List[AnomalyRecord]:
    now = datetime.utcnow()
    new_anomalies = []

    all_reservations = db.list_reservations()

    for res in all_reservations:
        if res.status == ReservationStatus.RESERVED and not res.check_in:
            if now > res.start_time + timedelta(minutes=settings.auto_checkin_timeout_minutes):
                exists = db.list_anomaly_records(anomaly_type=AnomalyType.NO_SHOW)
                already = [a for a in exists if a.reservation_id == res.id and a.status != AnomalyStatus.RESOLVED]
                if not already:
                    res.status = ReservationStatus.NO_SHOW
                    locker = db.get_locker(res.locker_id)
                    if locker and locker.status == LockerStatus.RESERVED:
                        db.update_locker(res.locker_id, LockerUpdate(status=LockerStatus.AVAILABLE))
                    anomaly = db.create_anomaly_record(AnomalyRecordCreate(
                        type=AnomalyType.NO_SHOW,
                        reservation_id=res.id,
                        locker_id=res.locker_id,
                        description=f"预约已超过签到时限未签到，使用人: {res.user_name}",
                    ))
                    new_anomalies.append(anomaly)

        if res.status == ReservationStatus.CHECKED_IN and res.release is None:
            if now > res.end_time + timedelta(minutes=settings.overtime_grace_minutes):
                exists = db.list_anomaly_records(anomaly_type=AnomalyType.OVERTIME)
                already = [a for a in exists if a.reservation_id == res.id and a.status != AnomalyStatus.RESOLVED]
                if not already:
                    res.status = ReservationStatus.OVERTIME
                    res.is_overtime = True
                    res.overtime_minutes = int((now - res.end_time).total_seconds() // 60)
                    anomaly = db.create_anomaly_record(AnomalyRecordCreate(
                        type=AnomalyType.OVERTIME,
                        reservation_id=res.id,
                        locker_id=res.locker_id,
                        description=f"使用人 {res.user_name} 占用已超时 {res.overtime_minutes} 分钟",
                    ))
                    new_anomalies.append(anomaly)

        if res.status in (ReservationStatus.RELEASED, ReservationStatus.OVERTIME) and res.release:
            locker = db.get_locker(res.locker_id)
            if locker and locker.status == LockerStatus.PENDING_RELEASE:
                if now > res.release.release_time + timedelta(hours=1):
                    exists = db.list_anomaly_records(anomaly_type=AnomalyType.RELEASE_CONFIRM_MISSING)
                    already = [a for a in exists if a.reservation_id == res.id and a.status != AnomalyStatus.RESOLVED]
                    if not already:
                        anomaly = db.create_anomaly_record(AnomalyRecordCreate(
                            type=AnomalyType.RELEASE_CONFIRM_MISSING,
                            reservation_id=res.id,
                            locker_id=res.locker_id,
                            description=f"预约释放后超过1小时未确认释放，使用人: {res.user_name}",
                        ))
                        new_anomalies.append(anomaly)

    all_lockers = db.list_lockers()
    for locker in all_lockers:
        if locker.status == LockerStatus.DISABLED:
            active = db.get_active_reservations_for_locker(locker.id)
            if active:
                exists = db.list_anomaly_records(anomaly_type=AnomalyType.DISABLED_LOCKER_RESERVED)
                already = [a for a in exists if a.locker_id == locker.id and a.status != AnomalyStatus.RESOLVED]
                if not already:
                    anomaly = db.create_anomaly_record(AnomalyRecordCreate(
                        type=AnomalyType.DISABLED_LOCKER_RESERVED,
                        locker_id=locker.id,
                        description=f"已停用储物格 {locker.locker_number} 仍存在未完成预约 {len(active)}个",
                    ))
                    new_anomalies.append(anomaly)

    return new_anomalies


@router.post("/anomalies/run-detection", response_model=Dict[str, Any])
def trigger_detection(_: User = Depends(require_supervisor)):
    new_records = run_anomaly_detection()
    return {
        "message": "异常检测完成",
        "new_anomaly_count": len(new_records),
        "new_records": new_records,
    }


@router.get("/reservations", response_model=List[Reservation])
def query_reservations(
    area_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    user_name: Optional[str] = None,
    status_filter: Optional[ReservationStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_overtime: Optional[bool] = None,
    _: User = Depends(require_any_authenticated),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    return db.list_reservations(
        area_id=area_id, locker_id=locker_id, user_name=user_name,
        status=status_filter, start_date=sd, end_date=ed, is_overtime=is_overtime,
    )


@router.get("/lockers", response_model=List[Locker])
def query_lockers(
    area_id: Optional[str] = None,
    status_filter: Optional[LockerStatus] = None,
    _: User = Depends(require_any_authenticated),
):
    return db.list_lockers(area_id=area_id, status=status_filter)


@router.get("/stats/occupancy-rate", response_model=List[LockerOccupancyRate])
def get_occupancy_rate(
    start_date: str,
    end_date: str,
    area_id: Optional[str] = None,
    _: User = Depends(require_any_authenticated),
):
    sd = datetime.fromisoformat(start_date).date()
    ed = datetime.fromisoformat(end_date).date()
    if sd > ed:
        raise HTTPException(status_code=400, detail="开始日期不能晚于结束日期")

    result = []
    total_lockers = len(db.list_lockers(area_id=area_id))
    current = sd
    while current <= ed:
        day_reservations = db.list_reservations(
            area_id=area_id, start_date=current, end_date=current)
        occupied_locker_ids = set()
        for r in day_reservations:
            if r.status in (ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME, ReservationStatus.RELEASED):
                occupied_locker_ids.add(r.locker_id)
        occupied_count = len(occupied_locker_ids)
        rate = occupied_count / total_lockers if total_lockers > 0 else 0.0
        result.append(LockerOccupancyRate(
            date=current,
            total_lockers=total_lockers,
            occupied_lockers=occupied_count,
            occupancy_rate=round(rate, 4),
        ))
        current += timedelta(days=1)
    return result


@router.get("/stats/overtime-ranking", response_model=List[OvertimeRankingItem])
def get_overtime_ranking(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    top_n: int = Query(10, ge=1, le=100),
    _: User = Depends(require_any_authenticated),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    all_reservations = db.list_reservations(start_date=sd, end_date=ed)

    user_stats = defaultdict(lambda: {"user_name": "", "count": 0, "minutes": 0})
    for r in all_reservations:
        if r.is_overtime:
            key = r.user_id_number
            user_stats[key]["user_name"] = r.user_name
            user_stats[key]["count"] += 1
            user_stats[key]["minutes"] += r.overtime_minutes

    ranking = [
        OvertimeRankingItem(
            user_name=v["user_name"],
            user_id_number=k,
            overtime_count=v["count"],
            total_overtime_minutes=v["minutes"],
        )
        for k, v in user_stats.items()
    ]
    ranking.sort(key=lambda x: (-x.overtime_count, -x.total_overtime_minutes))
    return ranking[:top_n]


@router.get("/stats/pending-anomalies", response_model=List[AnomalyRecord])
def get_pending_anomalies(_: User = Depends(require_supervisor)):
    return db.list_anomaly_records(status=AnomalyStatus.PENDING)


@router.get("/reservations/{res_id}", response_model=Reservation)
def get_reservation_detail(res_id: str, _: User = Depends(require_any_authenticated)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return res


@router.get("/reservations/{res_id}/fulfillment", response_model=ReservationFulfillmentDetail)
def get_reservation_fulfillment_public(res_id: str, _: User = Depends(require_any_authenticated)):
    detail = db.get_reservation_fulfillment_detail(res_id)
    if not detail:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return detail


@router.get("/lockers/{locker_id}", response_model=Locker)
def get_locker_detail(locker_id: str, _: User = Depends(require_any_authenticated)):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return locker


@router.get("/lockers/{locker_id}/availability", response_model=LockerAvailabilityCheck)
def get_locker_availability_public(locker_id: str, _: User = Depends(require_any_authenticated)):
    check = db.check_locker_availability(locker_id)
    if not check:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return check


@router.get("/anomalies", response_model=List[AnomalyRecord])
def query_anomalies_public(
    status_filter: Optional[AnomalyStatus] = None,
    anomaly_type: Optional[AnomalyType] = None,
    reservation_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: User = Depends(require_any_authenticated),
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
def get_anomaly_detail_public(record_id: str, _: User = Depends(require_any_authenticated)):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    return record


@router.get("/stats/anomaly-overview", response_model=AnomalyStatistics)
def get_anomaly_statistics_public(_: User = Depends(require_any_authenticated)):
    return db.get_anomaly_statistics()


@router.get("/reservations/{res_id}/anomalies", response_model=List[AnomalyRecord])
def get_reservation_anomalies_public(res_id: str, _: User = Depends(require_any_authenticated)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return db.get_anomalies_for_reservation(res_id)


@router.get("/reservations-with-fulfillment", response_model=List[ReservationWithFulfillment])
def list_reservations_with_fulfillment_public(
    area_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    user_name: Optional[str] = None,
    status_filter: Optional[ReservationStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_overtime: Optional[bool] = None,
    _: User = Depends(require_any_authenticated),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    return db.list_reservations_with_fulfillment(
        area_id=area_id, locker_id=locker_id, user_name=user_name,
        status=status_filter, start_date=sd, end_date=ed, is_overtime=is_overtime,
    )


@router.get("/anomalies-with-relations", response_model=List[AnomalyRecordWithRelations])
def query_anomalies_with_relations_public(
    status_filter: Optional[AnomalyStatus] = None,
    anomaly_type: Optional[AnomalyType] = None,
    area_id: Optional[str] = None,
    reservation_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _: User = Depends(require_any_authenticated),
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


@router.get("/stats/anomaly-overview-enhanced", response_model=AnomalyStatistics)
def get_anomaly_statistics_enhanced_public(
    area_id: Optional[str] = None,
    _: User = Depends(require_any_authenticated),
):
    return db.get_anomaly_statistics(area_id=area_id)


@router.get("/stats/anomaly-type-distribution", response_model=List[AnomalyTypeDistribution])
def get_anomaly_type_distribution_public(
    area_id: Optional[str] = None,
    _: User = Depends(require_any_authenticated),
):
    return db.get_anomaly_type_distribution(area_id=area_id)


@router.get("/stats/area-anomaly-summary", response_model=List[AreaAnomalySummary])
def get_area_anomaly_summary_public(_: User = Depends(require_any_authenticated)):
    return db.get_area_anomaly_summary()


@router.get("/stats/fulfillment-overview", response_model=FulfillmentOverview)
def get_fulfillment_overview_public(
    area_id: Optional[str] = None,
    _: User = Depends(require_any_authenticated),
):
    return db.get_fulfillment_overview(area_id=area_id)
