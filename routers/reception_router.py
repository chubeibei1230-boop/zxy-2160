from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_reception
from schemas import (
    User,
    Reservation, ReservationCreate, ReservationUpdate, ReservationStatus,
    LockerStatus,
    MessageResponse,
    AnomalyRecord, AnomalyRecordCreate, AnomalyRecordUpdate, AnomalyType, AnomalyStatus,
    ReservationFulfillmentDetail,
    ReservationWithFulfillment,
)
from database import db
from config import settings

router = APIRouter(prefix="/reception", tags=["前台"])


def _check_time_overlap(start1: datetime, end1: datetime, start2: datetime, end2: datetime) -> bool:
    return start1 < end2 and start2 < end1


def _validate_time_slot(start_time: datetime, end_time: datetime):
    active_slots = [ts for ts in db.list_time_slots() if ts.is_active]
    if not active_slots:
        return
    start_hm = start_time.strftime("%H:%M")
    end_hm = end_time.strftime("%H:%M")
    matched = False
    for slot in active_slots:
        if start_hm >= slot.start_time and end_hm <= slot.end_time:
            matched = True
            break
    if not matched:
        slot_desc = ", ".join(f"{s.start_time}-{s.end_time}" for s in active_slots)
        raise HTTPException(
            status_code=400,
            detail=f"预约时间不在可预约时段内，可用时段: {slot_desc}",
        )


@router.get("/reservations", response_model=List[Reservation])
def list_reservations(
    area_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    user_name: Optional[str] = None,
    status_filter: Optional[ReservationStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_overtime: Optional[bool] = None,
    _: User = Depends(require_reception),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    return db.list_reservations(
        area_id=area_id, locker_id=locker_id, user_name=user_name,
        status=status_filter, start_date=sd, end_date=ed, is_overtime=is_overtime,
    )


@router.get("/reservations/{res_id}", response_model=Reservation)
def get_reservation(res_id: str, _: User = Depends(require_reception)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return res


@router.put("/reservations/{res_id}", response_model=Reservation)
def update_reservation(res_id: str, data: ReservationUpdate, _: User = Depends(require_reception)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status not in {ReservationStatus.RESERVED}:
        raise HTTPException(status_code=400, detail="仅已预约状态可修改")

    new_start = data.start_time if data.start_time else res.start_time
    new_end = data.end_time if data.end_time else res.end_time
    new_user_id = data.user_id_number if data.user_id_number else res.user_id_number
    new_locker = data.locker_id if data.locker_id else res.locker_id

    if new_start >= new_end:
        raise HTTPException(status_code=400, detail="预约开始时间必须早于结束时间")

    if new_start < datetime.utcnow():
        raise HTTPException(status_code=400, detail="预约开始时间不能早于当前时间")

    duration_hours = (new_end - new_start).total_seconds() / 3600
    rule = db.get_usage_rule()
    if duration_hours > rule.max_hours_per_reservation:
        raise HTTPException(
            status_code=400,
            detail=f"单次预约时长不能超过 {rule.max_hours_per_reservation} 小时"
        )

    locker = db.get_locker(new_locker)
    if not locker:
        raise HTTPException(status_code=404, detail="目标储物格不存在")
    if data.locker_id and data.locker_id != res.locker_id:
        if locker.status == LockerStatus.DISABLED:
            raise HTTPException(status_code=400, detail="目标储物格已停用，无法预约")
        if locker.status == LockerStatus.PENDING_RELEASE:
            raise HTTPException(status_code=400, detail="目标储物格待确认释放，暂不可预约")
        if locker.status != LockerStatus.AVAILABLE:
            status_label = {
                LockerStatus.RESERVED: "已被预约",
                LockerStatus.IN_USE: "使用中",
                LockerStatus.PENDING_RELEASE: "待确认释放",
                LockerStatus.DISABLED: "已停用",
            }.get(locker.status, locker.status)
            raise HTTPException(status_code=400, detail=f"目标储物格当前状态为{status_label}，无法预约")

    locker_active = db.get_active_reservations_for_locker(new_locker, exclude_res_id=res_id)
    for exist in locker_active:
        if _check_time_overlap(new_start, new_end, exist.start_time, exist.end_time):
            raise HTTPException(status_code=409, detail="该储物格在修改后的时段存在冲突预约")

    user_active = db.get_active_reservations_for_user(new_user_id, exclude_res_id=res_id)
    for exist in user_active:
        if _check_time_overlap(new_start, new_end, exist.start_time, exist.end_time):
            raise HTTPException(status_code=409, detail="该使用人在修改后的时段存在冲突预约")

    same_day_reservations = [
        r for r in user_active
        if r.start_time.date() == new_start.date()
    ]
    if len(same_day_reservations) >= rule.max_reservations_per_user_per_day:
        raise HTTPException(
            status_code=400,
            detail=f"该使用人当日预约数已达上限（{rule.max_reservations_per_user_per_day}次）"
        )

    _validate_time_slot(new_start, new_end)

    old_locker_id = res.locker_id
    updated = db.update_reservation(res_id, data)
    if data.locker_id and data.locker_id != old_locker_id:
        old_locker = db.get_locker(old_locker_id)
        if old_locker and old_locker.status == LockerStatus.RESERVED:
            still_has = db.get_active_reservations_for_locker(old_locker_id, exclude_res_id=res_id)
            if not still_has:
                db.update_locker(old_locker_id, LockerUpdate(status=LockerStatus.AVAILABLE))
        if locker.status == LockerStatus.AVAILABLE:
            db.update_locker(new_locker, LockerUpdate(status=LockerStatus.RESERVED))
    return updated


@router.delete("/reservations/{res_id}", response_model=MessageResponse)
def cancel_reservation(res_id: str, _: User = Depends(require_reception)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status not in {ReservationStatus.RESERVED}:
        raise HTTPException(status_code=400, detail="仅已预约状态可取消")
    db.cancel_reservation(res_id)
    return MessageResponse(message="预约已取消")


@router.post("/reservations/{res_id}/check-in", response_model=Reservation)
def check_in(
    res_id: str,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_reception),
):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status != ReservationStatus.RESERVED:
        raise HTTPException(status_code=400, detail="仅已预约状态可签到")
    return db.check_in_reservation(res_id, operator=current_user.username, remarks=remarks)


class ReleaseRequest(MessageResponse):
    leftover_items: Optional[str] = None
    abnormal_photo_placeholder: Optional[str] = None
    handling_suggestion: Optional[str] = None
    remarks: Optional[str] = None


@router.post("/reservations/{res_id}/release", response_model=Reservation)
def release(
    res_id: str,
    leftover_items: Optional[str] = None,
    abnormal_photo_placeholder: Optional[str] = None,
    handling_suggestion: Optional[str] = None,
    remarks: Optional[str] = None,
    current_user: User = Depends(require_reception),
):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status not in {ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME}:
        raise HTTPException(status_code=400, detail="仅已签到或超时状态可释放")
    return db.release_reservation(
        res_id,
        operator=current_user.username,
        leftover_items=leftover_items,
        abnormal_photo_placeholder=abnormal_photo_placeholder,
        handling_suggestion=handling_suggestion,
        remarks=remarks,
    )


@router.post("/reservations/{res_id}/confirm-release", response_model=Reservation)
def confirm_release(res_id: str, _: User = Depends(require_reception)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status not in {ReservationStatus.RELEASED, ReservationStatus.OVERTIME}:
        raise HTTPException(status_code=400, detail="仅已释放或超时状态可确认释放")
    if not res.release:
        raise HTTPException(status_code=400, detail="未执行释放操作，无法确认")
    locker = db.get_locker(res.locker_id)
    if locker and locker.status == LockerStatus.AVAILABLE:
        raise HTTPException(status_code=400, detail="该预约已确认释放，无需重复操作")
    result = db.confirm_release(res_id)
    if not result:
        raise HTTPException(status_code=400, detail="确认释放失败")
    return result


@router.get("/reservations/{res_id}/fulfillment", response_model=ReservationFulfillmentDetail)
def get_reservation_fulfillment(res_id: str, _: User = Depends(require_reception)):
    detail = db.get_reservation_fulfillment_detail(res_id)
    if not detail:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return detail


@router.post("/reservations/{res_id}/anomalies", response_model=AnomalyRecord, status_code=status.HTTP_201_CREATED)
def raise_anomaly_for_reservation(
    res_id: str,
    anomaly_type: AnomalyType,
    description: str,
    supplementary_notes: Optional[str] = None,
    current_user: User = Depends(require_reception),
):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if res.status not in {
        ReservationStatus.RESERVED,
        ReservationStatus.CHECKED_IN,
        ReservationStatus.OVERTIME,
        ReservationStatus.RELEASED,
    }:
        raise HTTPException(status_code=400, detail="当前预约状态不支持发起异常")
    data = AnomalyRecordCreate(
        type=anomaly_type,
        reservation_id=res.id,
        locker_id=res.locker_id,
        description=description,
        supplementary_notes=supplementary_notes,
        reporter=current_user.username,
    )
    return db.create_anomaly_record(data)


@router.get("/reservations/{res_id}/anomalies", response_model=List[AnomalyRecord])
def list_reservation_anomalies(res_id: str, _: User = Depends(require_reception)):
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    return db.get_anomalies_for_reservation(res_id)


@router.put("/anomalies/{record_id}", response_model=AnomalyRecord)
def supplement_anomaly(
    record_id: str,
    data: AnomalyRecordUpdate,
    _: User = Depends(require_reception),
):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    if record.status in {AnomalyStatus.RESOLVED, AnomalyStatus.REJECTED}:
        raise HTTPException(status_code=400, detail="该异常已处理完成，无法补充说明")
    updated = db.update_anomaly_record(record_id, data)
    if not updated:
        raise HTTPException(status_code=500, detail="更新异常记录失败")
    return updated


@router.get("/anomalies/{record_id}", response_model=AnomalyRecord)
def get_anomaly_detail(record_id: str, _: User = Depends(require_reception)):
    record = db.get_anomaly_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="异常记录不存在")
    return record


@router.get("/anomalies", response_model=List[AnomalyRecord])
def list_anomalies(
    status_filter: Optional[AnomalyStatus] = None,
    anomaly_type: Optional[AnomalyType] = None,
    area_id: Optional[str] = None,
    _: User = Depends(require_reception),
):
    return db.list_anomaly_records_enhanced(
        status=status_filter, anomaly_type=anomaly_type, area_id=area_id,
    )


@router.get("/reservations-with-fulfillment", response_model=List[ReservationWithFulfillment])
def list_reservations_with_fulfillment(
    area_id: Optional[str] = None,
    locker_id: Optional[str] = None,
    user_name: Optional[str] = None,
    status_filter: Optional[ReservationStatus] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    is_overtime: Optional[bool] = None,
    _: User = Depends(require_reception),
):
    sd = datetime.fromisoformat(start_date).date() if start_date else None
    ed = datetime.fromisoformat(end_date).date() if end_date else None
    return db.list_reservations_with_fulfillment(
        area_id=area_id, locker_id=locker_id, user_name=user_name,
        status=status_filter, start_date=sd, end_date=ed, is_overtime=is_overtime,
    )


@router.get("/anomaly-types", response_model=List[dict])
def list_anomaly_types(_: User = Depends(require_reception)):
    type_labels = {
        AnomalyType.NO_SHOW: "超时未签到",
        AnomalyType.OVERTIME: "超时未释放",
        AnomalyType.DISABLED_LOCKER_RESERVED: "停用储物格仍被占用",
        AnomalyType.RELEASE_CONFIRM_MISSING: "释放后未确认",
        AnomalyType.ABNORMAL_OCCUPANCY: "异常占用",
    }
    return [
        {"value": t.value, "label": type_labels.get(t, t.value)}
        for t in AnomalyType
    ]


@router.post("/reservations", response_model=Reservation, status_code=status.HTTP_201_CREATED)
def create_reservation(data: ReservationCreate, current_user: User = Depends(require_reception)):
    start_naive = data.start_time.replace(tzinfo=None) if data.start_time.tzinfo else data.start_time
    end_naive = data.end_time.replace(tzinfo=None) if data.end_time.tzinfo else data.end_time
    now = datetime.utcnow()
    if start_naive >= end_naive:
        raise HTTPException(status_code=400, detail="预约开始时间必须早于结束时间")
    if start_naive < now:
        raise HTTPException(status_code=400, detail="预约开始时间不能早于当前时间")

    duration_hours = (end_naive - start_naive).total_seconds() / 3600
    rule = db.get_usage_rule()
    if duration_hours > rule.max_hours_per_reservation:
        raise HTTPException(
            status_code=400,
            detail=f"单次预约时长不能超过 {rule.max_hours_per_reservation} 小时"
        )

    locker = db.get_locker(data.locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")

    check = db.check_locker_availability(data.locker_id)
    if not check:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if not check.can_reserve:
        reasons = "; ".join(check.blocking_reasons)
        raise HTTPException(status_code=400, detail=f"储物格不可预约: {reasons}")

    data.start_time = start_naive
    data.end_time = end_naive

    locker_active = db.get_active_reservations_for_locker(data.locker_id)
    for exist in locker_active:
        exist_start = exist.start_time.replace(tzinfo=None) if exist.start_time.tzinfo else exist.start_time
        exist_end = exist.end_time.replace(tzinfo=None) if exist.end_time.tzinfo else exist.end_time
        if _check_time_overlap(start_naive, end_naive, exist_start, exist_end):
            raise HTTPException(
                status_code=409,
                detail=f"该储物格在 {exist.start_time} 至 {exist.end_time} 已被预约，时间重叠"
            )

    user_active = db.get_active_reservations_for_user(data.user_id_number)
    for exist in user_active:
        exist_start = exist.start_time.replace(tzinfo=None) if exist.start_time.tzinfo else exist.start_time
        exist_end = exist.end_time.replace(tzinfo=None) if exist.end_time.tzinfo else exist.end_time
        if _check_time_overlap(start_naive, end_naive, exist_start, exist_end):
            raise HTTPException(
                status_code=409,
                detail=f"该使用人在 {exist.start_time} 至 {exist.end_time} 已有预约（储物格: {exist.locker_id}），时间重叠"
            )

    same_day_reservations = [
        r for r in user_active
        if r.start_time.date() == start_naive.date()
    ]
    if len(same_day_reservations) >= rule.max_reservations_per_user_per_day:
        raise HTTPException(
            status_code=400,
            detail=f"该使用人当日预约数已达上限（{rule.max_reservations_per_user_per_day}次）"
        )

    _validate_time_slot(data.start_time, data.end_time)

    return db.create_reservation(data, created_by=current_user.username)
