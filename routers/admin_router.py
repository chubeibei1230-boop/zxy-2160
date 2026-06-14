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
    if data.area_id:
        area = db.get_area(data.area_id)
        if not area:
            raise HTTPException(status_code=400, detail="所属区域不存在")
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


@router.post("/disable-reasons", response_model=DisableReason, status_code=status.HTTP_201_CREATED)
def create_disable_reason(data: DisableReasonCreate, current_user: User = Depends(require_admin)):
    locker = db.get_locker(data.locker_id)
    if not locker:
        raise HTTPException(status_code=400, detail="储物格不存在")
    dr = db.create_disable_reason(data)
    db.update_locker(data.locker_id, LockerUpdate(status=LockerStatus.DISABLED))
    return dr


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
    unresolved = db.list_disable_reasons(locker_id=dr.locker_id, resolved=False)
    if not unresolved:
        locker = db.get_locker(dr.locker_id)
        if locker and locker.status == LockerStatus.DISABLED:
            db.update_locker(dr.locker_id, LockerUpdate(status=LockerStatus.AVAILABLE))
    return dr
