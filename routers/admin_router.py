from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin
from schemas import (
    User,
    Area, AreaCreate, AreaUpdate,
    Locker, LockerCreate, LockerUpdate, LockerStatus,
    TimeSlot, TimeSlotCreate, TimeSlotUpdate,
    UsageRule, UsageRuleUpdate,
    DisableReason, DisableReasonCreate,
    MessageResponse,
    Reservation, ReservationStatus,
    LockerAvailabilityCheck, LockerAnomalyImpact,
    AnomalyRecord,
    RiskRule, RiskRuleCreate, RiskRuleUpdate,
    ViolationType, UserCreditProfile,
)
from database import db

router = APIRouter(prefix="/admin", tags=["管理员"])


@router.post("/areas", response_model=Area, status_code=status.HTTP_201_CREATED)
def create_area(data: AreaCreate, _: User = Depends(require_admin)):
    return db.create_area(data)


@router.get("/areas", response_model=List[Area])
def list_areas(_: User = Depends(require_admin)):
    return db.list_areas()


@router.get("/areas/{area_id}", response_model=Area)
def get_area(area_id: str, _: User = Depends(require_admin)):
    area = db.get_area(area_id)
    if not area:
        raise HTTPException(status_code=404, detail="区域不存在")
    return area


@router.put("/areas/{area_id}", response_model=Area)
def update_area(area_id: str, data: AreaUpdate, _: User = Depends(require_admin)):
    area = db.update_area(area_id, data)
    if not area:
        raise HTTPException(status_code=404, detail="区域不存在")
    return area


@router.delete("/areas/{area_id}", response_model=MessageResponse)
def delete_area(area_id: str, _: User = Depends(require_admin)):
    lockers = db.list_lockers(area_id=area_id)
    if lockers:
        raise HTTPException(status_code=400, detail="该区域下仍有储物格，无法删除")
    if not db.delete_area(area_id):
        raise HTTPException(status_code=404, detail="区域不存在")
    return MessageResponse(message="区域删除成功")


@router.post("/lockers", response_model=Locker, status_code=status.HTTP_201_CREATED)
def create_locker(data: LockerCreate, _: User = Depends(require_admin)):
    area = db.get_area(data.area_id)
    if not area:
        raise HTTPException(status_code=400, detail="所属区域不存在")
    return db.create_locker(data)


@router.get("/lockers", response_model=List[Locker])
def list_lockers(
    area_id: Optional[str] = None,
    status_filter: Optional[LockerStatus] = None,
    _: User = Depends(require_admin),
):
    return db.list_lockers(area_id=area_id, status=status_filter)


@router.get("/lockers/{locker_id}", response_model=Locker)
def get_locker(locker_id: str, _: User = Depends(require_admin)):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return locker


@router.put("/lockers/{locker_id}", response_model=Locker)
def update_locker(locker_id: str, data: LockerUpdate, _: User = Depends(require_admin)):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if data.area_id:
        area = db.get_area(data.area_id)
        if not area:
            raise HTTPException(status_code=400, detail="所属区域不存在")
    if data.status and data.status != locker.status:
        check = db.check_locker_availability(locker_id)
        if data.status == LockerStatus.DISABLED:
            if not check or not check.can_disable:
                reasons = "; ".join(check.blocking_reasons) if check else "未知原因"
                raise HTTPException(
                    status_code=400,
                    detail=f"无法直接停用储物格: {reasons}。请使用停用接口（POST /admin/lockers/{{id}}/disable）并填写停用原因。",
                )
        elif data.status == LockerStatus.AVAILABLE:
            if not check or not check.can_restore or check.active_reservations or check.unresolved_anomalies:
                reasons = "; ".join(check.blocking_reasons) if check else "未知原因"
                raise HTTPException(
                    status_code=400,
                    detail=f"无法直接恢复储物格: {reasons}。请先处理未完成预约或异常记录。",
                )
        elif data.status in {LockerStatus.IN_USE, LockerStatus.RESERVED, LockerStatus.PENDING_RELEASE}:
            raise HTTPException(
                status_code=400,
                detail="不允许直接将储物格状态修改为使用中/已预约/待确认释放",
            )
    locker = db.update_locker(locker_id, data)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return locker


@router.delete("/lockers/{locker_id}", response_model=MessageResponse)
def delete_locker(locker_id: str, _: User = Depends(require_admin)):
    locker = db.get_locker(locker_id)
    if locker and locker.status not in {LockerStatus.AVAILABLE, LockerStatus.DISABLED, LockerStatus.RELEASED}:
        raise HTTPException(status_code=400, detail="储物格正在使用中，无法删除")
    if not db.delete_locker(locker_id):
        raise HTTPException(status_code=404, detail="储物格不存在")
    return MessageResponse(message="储物格删除成功")


@router.post("/time-slots", response_model=TimeSlot, status_code=status.HTTP_201_CREATED)
def create_time_slot(data: TimeSlotCreate, _: User = Depends(require_admin)):
    return db.create_time_slot(data)


@router.get("/time-slots", response_model=List[TimeSlot])
def list_time_slots(_: User = Depends(require_admin)):
    return db.list_time_slots()


@router.get("/time-slots/{ts_id}", response_model=TimeSlot)
def get_time_slot(ts_id: str, _: User = Depends(require_admin)):
    ts = db.get_time_slot(ts_id)
    if not ts:
        raise HTTPException(status_code=404, detail="时段不存在")
    return ts


@router.put("/time-slots/{ts_id}", response_model=TimeSlot)
def update_time_slot(ts_id: str, data: TimeSlotUpdate, _: User = Depends(require_admin)):
    ts = db.update_time_slot(ts_id, data)
    if not ts:
        raise HTTPException(status_code=404, detail="时段不存在")
    return ts


@router.delete("/time-slots/{ts_id}", response_model=MessageResponse)
def delete_time_slot(ts_id: str, _: User = Depends(require_admin)):
    if not db.delete_time_slot(ts_id):
        raise HTTPException(status_code=404, detail="时段不存在")
    return MessageResponse(message="时段删除成功")


@router.get("/usage-rule", response_model=UsageRule)
def get_usage_rule(_: User = Depends(require_admin)):
    return db.get_usage_rule()


@router.put("/usage-rule", response_model=UsageRule)
def update_usage_rule(data: UsageRuleUpdate, _: User = Depends(require_admin)):
    return db.update_usage_rule(data)


@router.get("/disable-reasons", response_model=List[DisableReason])
def list_disable_reasons(
    locker_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    _: User = Depends(require_admin),
):
    return db.list_disable_reasons(locker_id=locker_id, resolved=resolved)


@router.post("/disable-reasons/{dr_id}/resolve", response_model=DisableReason)
def resolve_disable_reason(dr_id: str, current_user: User = Depends(require_admin)):
    dr = db.get_disable_reason(dr_id)
    if not dr:
        raise HTTPException(status_code=404, detail="停用原因不存在")
    dr = db.resolve_disable_reason(dr_id, current_user.username)
    return dr


@router.put("/reservations/{res_id}/force-time", response_model=Reservation)
def force_reservation_time(
    res_id: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    _: User = Depends(require_admin),
):
    from datetime import datetime
    res = db.get_reservation(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="预约记录不存在")
    if start_time:
        res.start_time = datetime.fromisoformat(start_time)
    if end_time:
        res.end_time = datetime.fromisoformat(end_time)
    return res


@router.get("/lockers/{locker_id}/availability-check", response_model=LockerAvailabilityCheck)
def check_locker_availability(locker_id: str, _: User = Depends(require_admin)):
    check = db.check_locker_availability(locker_id)
    if not check:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return check


@router.get("/lockers/{locker_id}/active-reservations", response_model=List[Reservation])
def list_locker_active_reservations(locker_id: str, _: User = Depends(require_admin)):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return db.get_active_reservations_for_locker(locker_id)


@router.get("/lockers/with-status", response_model=List[Locker])
def list_lockers_with_status_check(
    area_id: Optional[str] = None,
    status_filter: Optional[LockerStatus] = None,
    _: User = Depends(require_admin),
):
    lockers = db.list_lockers(area_id=area_id, status=status_filter)
    return lockers


@router.get("/lockers/{locker_id}/anomaly-impact", response_model=LockerAnomalyImpact)
def get_locker_anomaly_impact(
    locker_id: str,
    _: User = Depends(require_admin),
):
    impact = db.get_locker_anomaly_impact(locker_id)
    if not impact:
        raise HTTPException(status_code=404, detail="储物格不存在")
    return impact


@router.get("/lockers/{locker_id}/anomalies", response_model=List[AnomalyRecord])
def list_locker_anomalies(
    locker_id: str,
    unresolved_only: bool = True,
    _: User = Depends(require_admin),
):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if unresolved_only:
        return db.get_unresolved_anomalies_for_locker(locker_id)
    return [a for a in db.anomaly_records.values() if a.locker_id == locker_id]


@router.post("/disable-reasons", response_model=DisableReason, status_code=status.HTTP_201_CREATED)
def create_disable_reason(data: DisableReasonCreate, current_user: User = Depends(require_admin)):
    locker = db.get_locker(data.locker_id)
    if not locker:
        raise HTTPException(status_code=400, detail="储物格不存在")
    if locker.status == LockerStatus.DISABLED:
        raise HTTPException(status_code=400, detail="该储物格已处于停用状态")
    check = db.check_locker_availability(data.locker_id)
    if not check:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if not check.can_disable:
        reasons = "; ".join(check.blocking_reasons)
        raise HTTPException(
            status_code=400,
            detail=f"无法停用储物格: {reasons}",
        )
    data.reporter = current_user.username
    dr = db.create_disable_reason(data)
    db.update_locker(data.locker_id, LockerUpdate(status=LockerStatus.DISABLED))
    return dr


@router.post("/lockers/{locker_id}/disable", response_model=DisableReason, status_code=status.HTTP_201_CREATED)
def disable_locker_with_check(
    locker_id: str,
    data: DisableReasonCreate,
    current_user: User = Depends(require_admin),
):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if locker.status == LockerStatus.DISABLED:
        raise HTTPException(status_code=400, detail="该储物格已处于停用状态")
    check = db.check_locker_availability(locker_id)
    if not check:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if not check.can_disable:
        reasons = "; ".join(check.blocking_reasons)
        raise HTTPException(
            status_code=400,
            detail=f"无法停用储物格: {reasons}",
        )
    data.locker_id = locker_id
    data.reporter = current_user.username
    return db.disable_locker_with_validation(locker_id, data)


@router.post("/lockers/{locker_id}/restore", response_model=Locker)
def restore_locker_with_check(locker_id: str, _: User = Depends(require_admin)):
    locker = db.get_locker(locker_id)
    if not locker:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if locker.status != LockerStatus.DISABLED:
        raise HTTPException(status_code=400, detail="该储物格未处于停用状态")
    check = db.check_locker_availability(locker_id)
    if not check:
        raise HTTPException(status_code=404, detail="储物格不存在")
    if not check.can_restore:
        reasons = "; ".join(check.blocking_reasons)
        raise HTTPException(status_code=400, detail=f"无法恢复储物格使用: {reasons}")
    restored = db.restore_locker_with_validation(locker_id)
    if not restored:
        raise HTTPException(status_code=500, detail="恢复储物格失败")
    return restored


@router.post("/risk-rules", response_model=RiskRule, status_code=status.HTTP_201_CREATED)
def create_risk_rule(data: RiskRuleCreate, _: User = Depends(require_admin)):
    return db.create_risk_rule(data)


@router.get("/risk-rules", response_model=List[RiskRule])
def list_risk_rules(
    violation_type: Optional[ViolationType] = None,
    is_active: Optional[bool] = None,
    _: User = Depends(require_admin),
):
    return db.list_risk_rules(violation_type=violation_type, is_active=is_active)


@router.get("/risk-rules/{rule_id}", response_model=RiskRule)
def get_risk_rule(rule_id: str, _: User = Depends(require_admin)):
    rule = db.get_risk_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="风险规则不存在")
    return rule


@router.put("/risk-rules/{rule_id}", response_model=RiskRule)
def update_risk_rule(rule_id: str, data: RiskRuleUpdate, _: User = Depends(require_admin)):
    rule = db.update_risk_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="风险规则不存在")
    return rule


@router.delete("/risk-rules/{rule_id}", response_model=MessageResponse)
def delete_risk_rule(rule_id: str, _: User = Depends(require_admin)):
    if not db.delete_risk_rule(rule_id):
        raise HTTPException(status_code=404, detail="风险规则不存在")
    return MessageResponse(message="风险规则删除成功")


@router.post("/user-credit/{user_id_number}/lift-restriction", response_model=UserCreditProfile)
def lift_restriction(
    user_id_number: str,
    notes: Optional[str] = None,
    current_user: User = Depends(require_admin),
):
    profile = db.manually_lift_restriction(user_id_number, current_user.username, notes)
    if not profile:
        raise HTTPException(status_code=404, detail="用户信用记录不存在或未被限制")
    return profile


@router.post("/user-credit/{user_id_number}/restrict", response_model=UserCreditProfile)
def manually_restrict_user(
    user_id_number: str,
    restriction_days: int = 30,
    notes: Optional[str] = None,
    current_user: User = Depends(require_admin),
):
    profile = db.manually_restrict_user(user_id_number, current_user.username, restriction_days, notes)
    return profile


@router.get("/user-credit/{user_id_number}", response_model=UserCreditProfile)
def get_user_credit_profile(user_id_number: str, _: User = Depends(require_admin)):
    profile = db.get_user_credit_profile(user_id_number)
    if not profile:
        raise HTTPException(status_code=404, detail="用户信用记录不存在")
    return profile
