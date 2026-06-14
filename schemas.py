from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class UserRole(str, Enum):
    ADMIN = "admin"
    RECEPTION = "reception"
    SUPERVISOR = "supervisor"


class LockerStatus(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    IN_USE = "in_use"
    PENDING_RELEASE = "pending_release"
    RELEASED = "released"
    DISABLED = "disabled"


class ReservationStatus(str, Enum):
    RESERVED = "reserved"
    CHECKED_IN = "checked_in"
    RELEASED = "released"
    NO_SHOW = "no_show"
    OVERTIME = "overtime"
    CANCELLED = "cancelled"


class AnomalyType(str, Enum):
    NO_SHOW = "no_show"
    OVERTIME = "overtime"
    DISABLED_LOCKER_RESERVED = "disabled_locker_reserved"
    RELEASE_CONFIRM_MISSING = "release_confirm_missing"
    ABNORMAL_OCCUPANCY = "abnormal_occupancy"


class AnomalyStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class User(BaseModel):
    username: str
    role: UserRole


class UserInDB(User):
    hashed_password: str


class AreaBase(BaseModel):
    name: str
    description: Optional[str] = None


class AreaCreate(AreaBase):
    pass


class AreaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class Area(AreaBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LockerBase(BaseModel):
    locker_number: str
    area_id: str
    description: Optional[str] = None


class LockerCreate(LockerBase):
    pass


class LockerUpdate(BaseModel):
    locker_number: Optional[str] = None
    area_id: Optional[str] = None
    description: Optional[str] = None
    status: Optional[LockerStatus] = None


class Locker(LockerBase):
    id: str
    status: LockerStatus = LockerStatus.AVAILABLE
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TimeSlotBase(BaseModel):
    name: str
    start_time: str
    end_time: str
    is_active: bool = True


class TimeSlotCreate(TimeSlotBase):
    pass


class TimeSlotUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    is_active: Optional[bool] = None


class TimeSlot(TimeSlotBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UsageRuleBase(BaseModel):
    max_hours_per_reservation: int = 4
    max_reservations_per_user_per_day: int = 2
    require_id_verification: bool = True
    overtime_penalty_hours: float = 0.0


class UsageRuleCreate(UsageRuleBase):
    pass


class UsageRuleUpdate(BaseModel):
    max_hours_per_reservation: Optional[int] = None
    max_reservations_per_user_per_day: Optional[int] = None
    require_id_verification: Optional[bool] = None
    overtime_penalty_hours: Optional[float] = None


class UsageRule(UsageRuleBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DisableReasonBase(BaseModel):
    locker_id: str
    reason: str
    reporter: str


class DisableReasonCreate(DisableReasonBase):
    pass


class DisableReason(BaseModel):
    id: str
    locker_id: str
    reason: str
    reporter: str
    resolved: bool = False
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReservationBase(BaseModel):
    locker_id: str
    user_name: str
    user_id_number: str
    user_phone: str
    start_time: datetime
    end_time: datetime
    purpose: Optional[str] = None


class ReservationCreate(ReservationBase):
    pass


class ReservationUpdate(BaseModel):
    locker_id: Optional[str] = None
    user_name: Optional[str] = None
    user_id_number: Optional[str] = None
    user_phone: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    purpose: Optional[str] = None


class CheckInRecord(BaseModel):
    check_in_time: datetime
    operator: str
    remarks: Optional[str] = None


class ReleaseRecord(BaseModel):
    release_time: datetime
    operator: str
    leftover_items: Optional[str] = None
    abnormal_photo_placeholder: Optional[str] = None
    handling_suggestion: Optional[str] = None
    remarks: Optional[str] = None


class Reservation(ReservationBase):
    id: str
    status: ReservationStatus = ReservationStatus.RESERVED
    check_in: Optional[CheckInRecord] = None
    release: Optional[ReleaseRecord] = None
    is_overtime: bool = False
    overtime_minutes: int = 0
    created_at: datetime
    created_by: str
    model_config = ConfigDict(from_attributes=True)


class AnomalyRecordBase(BaseModel):
    type: AnomalyType
    reservation_id: Optional[str] = None
    locker_id: Optional[str] = None
    description: str


class AnomalyRecordCreate(AnomalyRecordBase):
    pass


class AnomalyReview(BaseModel):
    status: AnomalyStatus
    reviewer: str
    review_notes: Optional[str] = None


class AnomalyRecord(BaseModel):
    id: str
    type: AnomalyType
    reservation_id: Optional[str] = None
    locker_id: Optional[str] = None
    description: str
    status: AnomalyStatus = AnomalyStatus.PENDING
    reviewer: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class LockerOccupancyRate(BaseModel):
    date: date
    total_lockers: int
    occupied_lockers: int
    occupancy_rate: float


class OvertimeRankingItem(BaseModel):
    user_name: str
    user_id_number: str
    overtime_count: int
    total_overtime_minutes: int


class ReservationQueryParams(BaseModel):
    area_id: Optional[str] = None
    locker_id: Optional[str] = None
    user_name: Optional[str] = None
    status: Optional[ReservationStatus] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_overtime: Optional[bool] = None


class PaginatedResponse(BaseModel):
    total: int
    items: List
