from datetime import datetime, date
from typing import Optional, List, Dict
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
    supplementary_notes: Optional[str] = None
    reporter: Optional[str] = None


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
    supplementary_notes: Optional[str] = None
    reporter: Optional[str] = None
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


class FulfillmentStep(BaseModel):
    step: str
    label: str
    status: str
    completed_at: Optional[datetime] = None
    operator: Optional[str] = None
    remarks: Optional[str] = None
    deadline_at: Optional[datetime] = None
    remaining_seconds: Optional[int] = None
    is_warning: bool = False
    is_overdue: bool = False


class ReservationFulfillmentSummary(BaseModel):
    current_stage: str
    current_stage_label: str
    next_action: Optional[str] = None
    next_action_label: Optional[str] = None
    time_left_seconds: Optional[int] = None
    time_left_text: Optional[str] = None
    has_active_anomaly: bool = False
    active_anomaly_count: int = 0


class ReservationFulfillmentDetail(BaseModel):
    reservation: Reservation
    locker: Locker
    area: Optional[Area] = None
    fulfillment_steps: List[FulfillmentStep]
    anomalies: List[AnomalyRecord]
    fulfillment_summary: ReservationFulfillmentSummary
    can_raise_anomaly: bool
    can_release: bool
    can_confirm_release: bool
    can_check_in: bool
    can_cancel: bool
    available_actions: List[Dict] = []


class AnomalySupplement(BaseModel):
    description: str
    supplementary_notes: Optional[str] = None


class AnomalyRecordUpdate(BaseModel):
    supplementary_notes: Optional[str] = None
    description: Optional[str] = None


class AnomalyResolveData(BaseModel):
    review_notes: Optional[str] = None
    handling_notes: Optional[str] = None


class LockerAnomalyImpact(BaseModel):
    locker_id: str
    locker_number: str
    current_status: LockerStatus
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    unresolved_anomaly_count: int = 0
    unresolved_anomalies: List[AnomalyRecord] = []
    pending_disable_reason_count: int = 0
    pending_disable_reasons: List[DisableReason] = []
    active_reservation_count: int = 0
    active_reservations: List[Reservation] = []
    can_reserve: bool = True
    can_disable: bool = True
    can_restore: bool = True
    impact_reasons: List[str] = []


class LockerAvailabilityCheck(BaseModel):
    locker_id: str
    locker_number: str
    current_status: LockerStatus
    can_reserve: bool
    can_restore: bool
    can_disable: bool = True
    blocking_reasons: List[str]
    unresolved_disable_reasons: List[DisableReason]
    active_reservations: List[Reservation]
    unresolved_anomalies: List[AnomalyRecord] = []
    anomaly_impact: Optional[LockerAnomalyImpact] = None


class AnomalyStatistics(BaseModel):
    total: int
    pending: int
    confirmed: int
    resolved: int
    rejected: int
    by_type: Dict[str, int]
    by_area: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    today_new: int = 0
    resolved_today: int = 0
    avg_resolve_minutes: Optional[float] = None


class AnomalyListQuery(BaseModel):
    status: Optional[AnomalyStatus] = None
    anomaly_type: Optional[AnomalyType] = None
    area_id: Optional[str] = None
    reservation_id: Optional[str] = None
    locker_id: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class ReservationWithFulfillment(Reservation):
    locker_number: Optional[str] = None
    area_id: Optional[str] = None
    area_name: Optional[str] = None
    fulfillment_summary: Optional[ReservationFulfillmentSummary] = None
    anomaly_count: int = 0


class AnomalyRecordWithRelations(AnomalyRecord):
    reservation: Optional[Reservation] = None
    locker: Optional[Locker] = None
    area: Optional[Area] = None
    locker_number: Optional[str] = None
    area_name: Optional[str] = None
    user_name: Optional[str] = None


class AnomalyTypeDistribution(BaseModel):
    type: AnomalyType
    label: str
    count: int
    percentage: float


class AreaAnomalySummary(BaseModel):
    area_id: str
    area_name: str
    total: int = 0
    pending: int = 0
    confirmed: int = 0
    resolved: int = 0
    rejected: int = 0


class RiskLevel(str, Enum):
    NORMAL = "normal"
    LOW_RISK = "low_risk"
    MEDIUM_RISK = "medium_risk"
    HIGH_RISK = "high_risk"
    RESTRICTED = "restricted"


class ViolationType(str, Enum):
    NO_SHOW = "no_show"
    OVERTIME = "overtime"
    ABNORMAL_OCCUPANCY = "abnormal_occupancy"
    RELEASE_UNCONFIRMED = "release_unconfirmed"


RISK_LEVEL_LABELS = {
    RiskLevel.NORMAL: "正常",
    RiskLevel.LOW_RISK: "低风险",
    RiskLevel.MEDIUM_RISK: "中风险",
    RiskLevel.HIGH_RISK: "高风险",
    RiskLevel.RESTRICTED: "已限制",
}

VIOLATION_TYPE_LABELS = {
    ViolationType.NO_SHOW: "未签到",
    ViolationType.OVERTIME: "超时使用",
    ViolationType.ABNORMAL_OCCUPANCY: "异常占用",
    ViolationType.RELEASE_UNCONFIRMED: "释放未确认",
}


class CreditRecordBase(BaseModel):
    user_id_number: str
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    violation_type: ViolationType
    reservation_id: Optional[str] = None
    anomaly_record_id: Optional[str] = None
    description: str


class CreditRecordCreate(CreditRecordBase):
    pass


class CreditRecord(CreditRecordBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RiskRuleBase(BaseModel):
    name: str
    violation_type: ViolationType
    low_risk_threshold: int = 1
    medium_risk_threshold: int = 3
    high_risk_threshold: int = 5
    restricted_threshold: int = 8
    time_window_days: int = 90
    restriction_days: int = 30
    is_active: bool = True


class RiskRuleCreate(RiskRuleBase):
    pass


class RiskRuleUpdate(BaseModel):
    name: Optional[str] = None
    low_risk_threshold: Optional[int] = None
    medium_risk_threshold: Optional[int] = None
    high_risk_threshold: Optional[int] = None
    restricted_threshold: Optional[int] = None
    time_window_days: Optional[int] = None
    restriction_days: Optional[int] = None
    is_active: Optional[bool] = None


class RiskRule(RiskRuleBase):
    id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserCreditProfile(BaseModel):
    user_id_number: str
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.NORMAL
    violation_counts: Dict[str, int] = {}
    total_violations: int = 0
    is_restricted: bool = False
    restriction_until: Optional[datetime] = None
    restriction_reason: Optional[str] = None
    manually_lifted: bool = False
    last_violation_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class UserRiskReminder(BaseModel):
    user_id_number: str
    user_name: Optional[str] = None
    user_phone: Optional[str] = None
    risk_level: RiskLevel
    risk_level_label: str
    total_violations: int
    violation_counts: Dict[str, int] = {}
    is_restricted: bool = False
    restriction_until: Optional[datetime] = None
    can_reserve: bool = True
    warning_message: Optional[str] = None
    recent_violations: List[CreditRecord] = []


class SupervisorRiskAction(BaseModel):
    action: str
    notes: Optional[str] = None
    restriction_days: Optional[int] = None


class CreditRiskDistribution(BaseModel):
    risk_level: RiskLevel
    risk_level_label: str
    count: int
    percentage: float


class ViolationRankingItem(BaseModel):
    user_name: Optional[str] = None
    user_id_number: str
    total_violations: int
    violation_counts: Dict[str, int] = {}
    risk_level: RiskLevel


class RiskTrendItem(BaseModel):
    date: date
    new_violations: int
    total_restricted: int


class CreditRiskStatistics(BaseModel):
    total_users: int = 0
    normal_count: int = 0
    low_risk_count: int = 0
    medium_risk_count: int = 0
    high_risk_count: int = 0
    restricted_count: int = 0
    distribution: List[CreditRiskDistribution] = []
    violation_ranking: List[ViolationRankingItem] = []
    risk_trend: List[RiskTrendItem] = []


class FulfillmentOverview(BaseModel):
    total_reservations: int = 0
    stage_reserved: int = 0
    stage_checked_in: int = 0
    stage_released: int = 0
    stage_completed: int = 0
    stage_cancelled: int = 0
    stage_no_show: int = 0
    stage_overtime: int = 0
    warning_count: int = 0
    overdue_count: int = 0
