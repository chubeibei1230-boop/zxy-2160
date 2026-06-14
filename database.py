import uuid
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from copy import deepcopy

from schemas import (
    User, UserInDB, UserRole,
    Area, AreaCreate, AreaUpdate,
    Locker, LockerCreate, LockerUpdate, LockerStatus,
    TimeSlot, TimeSlotCreate, TimeSlotUpdate,
    UsageRule, UsageRuleCreate, UsageRuleUpdate,
    DisableReason, DisableReasonCreate,
    Reservation, ReservationCreate, ReservationUpdate, ReservationStatus,
    CheckInRecord, ReleaseRecord,
    AnomalyRecord, AnomalyRecordCreate, AnomalyRecordUpdate, AnomalyReview, AnomalyType, AnomalyStatus,
    FulfillmentStep, ReservationFulfillmentDetail, LockerAvailabilityCheck, AnomalyStatistics,
    ReservationFulfillmentSummary, LockerAnomalyImpact,
    ReservationWithFulfillment, AnomalyRecordWithRelations,
    AnomalyTypeDistribution, AreaAnomalySummary, FulfillmentOverview,
    AnomalyResolveData,
    RiskLevel, ViolationType, RISK_LEVEL_LABELS, VIOLATION_TYPE_LABELS,
    CreditRecord, CreditRecordCreate,
    RiskRule, RiskRuleCreate, RiskRuleUpdate,
    UserCreditProfile, UserRiskReminder,
    CreditRiskDistribution, ViolationRankingItem, RiskTrendItem, CreditRiskStatistics,
)
from config import settings


class InMemoryDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_data()
        return cls._instance

    def _init_data(self):
        self.users: Dict[str, UserInDB] = {}
        self.areas: Dict[str, Area] = {}
        self.lockers: Dict[str, Locker] = {}
        self.time_slots: Dict[str, TimeSlot] = {}
        self.usage_rules: Dict[str, UsageRule] = {}
        self.disable_reasons: Dict[str, DisableReason] = {}
        self.reservations: Dict[str, Reservation] = {}
        self.anomaly_records: Dict[str, AnomalyRecord] = {}
        self.credit_records: Dict[str, CreditRecord] = {}
        self.user_credit_profiles: Dict[str, UserCreditProfile] = {}
        self.risk_rules: Dict[str, RiskRule] = {}
        self._init_default_users()
        self._init_default_rule()
        self._init_default_risk_rules()

    def _init_default_users(self):
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        default_users = [
            (settings.admin_username, settings.admin_password, UserRole.ADMIN),
            (settings.reception_username, settings.reception_password, UserRole.RECEPTION),
            (settings.supervisor_username, settings.supervisor_password, UserRole.SUPERVISOR),
        ]
        for username, password, role in default_users:
            user = UserInDB(
                username=username,
                role=role,
                hashed_password=pwd_context.hash(password)
            )
            self.users[username] = user

    def _init_default_rule(self):
        now = datetime.utcnow()
        rule = UsageRule(
            id=str(uuid.uuid4()),
            max_hours_per_reservation=settings.default_max_reservation_hours,
            max_reservations_per_user_per_day=2,
            require_id_verification=True,
            overtime_penalty_hours=0.0,
            created_at=now,
            updated_at=now,
        )
        self.usage_rules[rule.id] = rule

    def _init_default_risk_rules(self):
        now = datetime.utcnow()
        default_rules = [
            RiskRule(
                id=self._gen_id(),
                name="未签到风险规则",
                violation_type=ViolationType.NO_SHOW,
                low_risk_threshold=1,
                medium_risk_threshold=2,
                high_risk_threshold=3,
                restricted_threshold=4,
                time_window_days=90,
                restriction_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            RiskRule(
                id=self._gen_id(),
                name="超时使用风险规则",
                violation_type=ViolationType.OVERTIME,
                low_risk_threshold=1,
                medium_risk_threshold=3,
                high_risk_threshold=5,
                restricted_threshold=8,
                time_window_days=90,
                restriction_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            RiskRule(
                id=self._gen_id(),
                name="异常占用风险规则",
                violation_type=ViolationType.ABNORMAL_OCCUPANCY,
                low_risk_threshold=1,
                medium_risk_threshold=2,
                high_risk_threshold=3,
                restricted_threshold=4,
                time_window_days=90,
                restriction_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
            RiskRule(
                id=self._gen_id(),
                name="释放未确认风险规则",
                violation_type=ViolationType.RELEASE_UNCONFIRMED,
                low_risk_threshold=1,
                medium_risk_threshold=3,
                high_risk_threshold=5,
                restricted_threshold=8,
                time_window_days=90,
                restriction_days=30,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        ]
        for rule in default_rules:
            self.risk_rules[rule.id] = rule

    @staticmethod
    def _gen_id() -> str:
        return str(uuid.uuid4())

    def get_user(self, username: str) -> Optional[UserInDB]:
        return self.users.get(username)

    def create_area(self, data: AreaCreate) -> Area:
        area = Area(
            id=self._gen_id(),
            name=data.name,
            description=data.description,
            created_at=datetime.utcnow(),
        )
        self.areas[area.id] = area
        return area

    def get_area(self, area_id: str) -> Optional[Area]:
        return self.areas.get(area_id)

    def list_areas(self) -> List[Area]:
        return list(self.areas.values())

    def update_area(self, area_id: str, data: AreaUpdate) -> Optional[Area]:
        area = self.areas.get(area_id)
        if not area:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(area, key, value)
        return area

    def delete_area(self, area_id: str) -> bool:
        if area_id in self.areas:
            del self.areas[area_id]
            return True
        return False

    def create_locker(self, data: LockerCreate) -> Locker:
        locker = Locker(
            id=self._gen_id(),
            locker_number=data.locker_number,
            area_id=data.area_id,
            description=data.description,
            status=LockerStatus.AVAILABLE,
            created_at=datetime.utcnow(),
        )
        self.lockers[locker.id] = locker
        return locker

    def get_locker(self, locker_id: str) -> Optional[Locker]:
        return self.lockers.get(locker_id)

    def list_lockers(self, area_id: Optional[str] = None, status: Optional[LockerStatus] = None) -> List[Locker]:
        result = list(self.lockers.values())
        if area_id:
            result = [l for l in result if l.area_id == area_id]
        if status:
            result = [l for l in result if l.status == status]
        return result

    def update_locker(self, locker_id: str, data: LockerUpdate) -> Optional[Locker]:
        locker = self.lockers.get(locker_id)
        if not locker:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(locker, key, value)
        return locker

    def delete_locker(self, locker_id: str) -> bool:
        if locker_id in self.lockers:
            del self.lockers[locker_id]
            return True
        return False

    def create_time_slot(self, data: TimeSlotCreate) -> TimeSlot:
        ts = TimeSlot(
            id=self._gen_id(),
            name=data.name,
            start_time=data.start_time,
            end_time=data.end_time,
            is_active=data.is_active,
            created_at=datetime.utcnow(),
        )
        self.time_slots[ts.id] = ts
        return ts

    def get_time_slot(self, ts_id: str) -> Optional[TimeSlot]:
        return self.time_slots.get(ts_id)

    def list_time_slots(self) -> List[TimeSlot]:
        return list(self.time_slots.values())

    def update_time_slot(self, ts_id: str, data: TimeSlotUpdate) -> Optional[TimeSlot]:
        ts = self.time_slots.get(ts_id)
        if not ts:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(ts, key, value)
        return ts

    def delete_time_slot(self, ts_id: str) -> bool:
        if ts_id in self.time_slots:
            del self.time_slots[ts_id]
            return True
        return False

    def get_usage_rule(self) -> UsageRule:
        return list(self.usage_rules.values())[0]

    def update_usage_rule(self, data: UsageRuleUpdate) -> UsageRule:
        rule = self.get_usage_rule()
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)
        rule.updated_at = datetime.utcnow()
        return rule

    def create_disable_reason(self, data: DisableReasonCreate) -> DisableReason:
        dr = DisableReason(
            id=self._gen_id(),
            locker_id=data.locker_id,
            reason=data.reason,
            reporter=data.reporter,
            created_at=datetime.utcnow(),
        )
        self.disable_reasons[dr.id] = dr
        return dr

    def get_disable_reason(self, dr_id: str) -> Optional[DisableReason]:
        return self.disable_reasons.get(dr_id)

    def list_disable_reasons(self, locker_id: Optional[str] = None, resolved: Optional[bool] = None) -> List[DisableReason]:
        result = list(self.disable_reasons.values())
        if locker_id:
            result = [d for d in result if d.locker_id == locker_id]
        if resolved is not None:
            result = [d for d in result if d.resolved == resolved]
        return result

    def resolve_disable_reason(self, dr_id: str, resolved_by: str) -> Optional[DisableReason]:
        dr = self.disable_reasons.get(dr_id)
        if not dr:
            return None
        dr.resolved = True
        dr.resolved_by = resolved_by
        dr.resolved_at = datetime.utcnow()
        unresolved = self.list_disable_reasons(locker_id=dr.locker_id, resolved=False)
        if not unresolved:
            active_reservations = self.get_active_reservations_for_locker(dr.locker_id)
            if not active_reservations:
                locker = self.get_locker(dr.locker_id)
                if locker and locker.status == LockerStatus.DISABLED:
                    self.update_locker(dr.locker_id, LockerUpdate(status=LockerStatus.AVAILABLE))
        return dr

    def create_reservation(self, data: ReservationCreate, created_by: str) -> Optional[Reservation]:
        locker = self.lockers.get(data.locker_id)
        if not locker:
            return None
        if locker.status != LockerStatus.AVAILABLE:
            return None
        res = Reservation(
            id=self._gen_id(),
            **data.model_dump(),
            status=ReservationStatus.RESERVED,
            created_at=datetime.utcnow(),
            created_by=created_by,
        )
        self.reservations[res.id] = res
        locker.status = LockerStatus.RESERVED
        return res

    def get_reservation(self, res_id: str) -> Optional[Reservation]:
        return self.reservations.get(res_id)

    def list_reservations(
        self,
        area_id: Optional[str] = None,
        locker_id: Optional[str] = None,
        user_name: Optional[str] = None,
        status: Optional[ReservationStatus] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_overtime: Optional[bool] = None,
    ) -> List[Reservation]:
        result = list(self.reservations.values())
        if area_id:
            result = [r for r in result if self.lockers.get(r.locker_id) and self.lockers[r.locker_id].area_id == area_id]
        if locker_id:
            result = [r for r in result if r.locker_id == locker_id]
        if user_name:
            result = [r for r in result if r.user_name == user_name]
        if status:
            result = [r for r in result if r.status == status]
        if start_date:
            result = [r for r in result if r.start_time.date() >= start_date]
        if end_date:
            result = [r for r in result if r.start_time.date() <= end_date]
        if is_overtime is not None:
            result = [r for r in result if r.is_overtime == is_overtime]
        return result

    def update_reservation(self, res_id: str, data: ReservationUpdate) -> Optional[Reservation]:
        res = self.reservations.get(res_id)
        if not res:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(res, key, value)
        return res

    def delete_reservation(self, res_id: str) -> bool:
        if res_id in self.reservations:
            del self.reservations[res_id]
            return True
        return False

    def check_in_reservation(self, res_id: str, operator: str, remarks: Optional[str] = None) -> Optional[Reservation]:
        res = self.reservations.get(res_id)
        if not res:
            return None
        res.check_in = CheckInRecord(
            check_in_time=datetime.utcnow(),
            operator=operator,
            remarks=remarks,
        )
        res.status = ReservationStatus.CHECKED_IN
        locker = self.lockers.get(res.locker_id)
        if locker:
            locker.status = LockerStatus.IN_USE
        return res

    def release_reservation(
        self,
        res_id: str,
        operator: str,
        leftover_items: Optional[str] = None,
        abnormal_photo_placeholder: Optional[str] = None,
        handling_suggestion: Optional[str] = None,
        remarks: Optional[str] = None,
    ) -> Optional[Reservation]:
        res = self.reservations.get(res_id)
        if not res:
            return None
        if res.release:
            return None
        if res.status not in {ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME}:
            return None
        release_time = datetime.utcnow()
        res.release = ReleaseRecord(
            release_time=release_time,
            operator=operator,
            leftover_items=leftover_items,
            abnormal_photo_placeholder=abnormal_photo_placeholder,
            handling_suggestion=handling_suggestion,
            remarks=remarks,
        )
        if release_time > res.end_time:
            overtime_delta = release_time - res.end_time
            res.overtime_minutes = int(overtime_delta.total_seconds() / 60)
            res.is_overtime = True
            if res.overtime_minutes > settings.overtime_grace_minutes:
                res.status = ReservationStatus.OVERTIME
                anomaly = self.create_anomaly_record(AnomalyRecordCreate(
                    type=AnomalyType.OVERTIME,
                    reservation_id=res.id,
                    locker_id=res.locker_id,
                    description=f"使用人 {res.user_name} 超时 {res.overtime_minutes} 分钟释放",
                ))
                self.record_violation_from_anomaly(anomaly)
            else:
                res.status = ReservationStatus.RELEASED
        else:
            res.status = ReservationStatus.RELEASED

        locker = self.lockers.get(res.locker_id)
        if locker:
            locker.status = LockerStatus.PENDING_RELEASE
        return res

    def confirm_release(self, res_id: str) -> Optional[Reservation]:
        res = self.reservations.get(res_id)
        if not res:
            return None
        if not res.release:
            return None
        locker = self.lockers.get(res.locker_id)
        if not locker:
            return None
        if locker.status == LockerStatus.AVAILABLE:
            return None
        if res.status in {ReservationStatus.OVERTIME, ReservationStatus.RELEASED}:
            res.status = ReservationStatus.RELEASED
        locker.status = LockerStatus.AVAILABLE
        return res

    def cancel_reservation(self, res_id: str) -> Optional[Reservation]:
        res = self.reservations.get(res_id)
        if not res:
            return None
        res.status = ReservationStatus.CANCELLED
        locker = self.lockers.get(res.locker_id)
        if locker and locker.status == LockerStatus.RESERVED:
            locker.status = LockerStatus.AVAILABLE
        return res

    def get_active_reservations_for_locker(self, locker_id: str, exclude_res_id: Optional[str] = None) -> List[Reservation]:
        active_statuses = {ReservationStatus.RESERVED, ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME}
        result = []
        for r in self.reservations.values():
            if r.locker_id != locker_id:
                continue
            if exclude_res_id and r.id == exclude_res_id:
                continue
            if r.status in active_statuses:
                result.append(r)
        return result

    def get_active_reservations_for_user(self, user_id_number: str, exclude_res_id: Optional[str] = None) -> List[Reservation]:
        active_statuses = {ReservationStatus.RESERVED, ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME}
        result = []
        for r in self.reservations.values():
            if r.user_id_number != user_id_number:
                continue
            if exclude_res_id and r.id == exclude_res_id:
                continue
            if r.status in active_statuses:
                result.append(r)
        return result

    def create_anomaly_record(self, data: AnomalyRecordCreate) -> AnomalyRecord:
        record = AnomalyRecord(
            id=self._gen_id(),
            **data.model_dump(),
            created_at=datetime.utcnow(),
        )
        self.anomaly_records[record.id] = record
        return record

    def get_anomaly_record(self, record_id: str) -> Optional[AnomalyRecord]:
        return self.anomaly_records.get(record_id)

    def list_anomaly_records(
        self,
        status: Optional[AnomalyStatus] = None,
        anomaly_type: Optional[AnomalyType] = None,
    ) -> List[AnomalyRecord]:
        result = list(self.anomaly_records.values())
        if status:
            result = [a for a in result if a.status == status]
        if anomaly_type:
            result = [a for a in result if a.type == anomaly_type]
        return result

    def review_anomaly(self, record_id: str, review: AnomalyReview) -> Optional[AnomalyRecord]:
        record = self.anomaly_records.get(record_id)
        if not record:
            return None
        record.status = review.status
        record.reviewer = review.reviewer
        record.review_notes = review.review_notes
        record.reviewed_at = datetime.utcnow()
        self._sync_business_state_on_anomaly_review(record)
        return record

    def _sync_business_state_on_anomaly_review(self, record: AnomalyRecord):
        if record.reservation_id:
            res = self.get_reservation(record.reservation_id)
        else:
            res = None
        if record.locker_id:
            locker = self.get_locker(record.locker_id)
        elif res:
            locker = self.get_locker(res.locker_id)
        else:
            locker = None

        if record.status == AnomalyStatus.RESOLVED:
            self._sync_anomaly_resolved(record, res, locker)
        elif record.status == AnomalyStatus.REJECTED:
            self._sync_anomaly_rejected(record, res, locker)

    def _sync_anomaly_resolved(self, record: AnomalyRecord, res: Optional[Reservation], locker: Optional[Locker]):
        if record.type == AnomalyType.OVERTIME and res and locker:
            if not res.release:
                now = datetime.utcnow()
                res.release = ReleaseRecord(
                    release_time=now,
                    operator=record.reviewer or "system",
                    handling_suggestion="超时异常处理完成，自动释放",
                    remarks="异常解决时自动释放",
                )
                res.overtime_minutes = int((now - res.end_time).total_seconds() // 60)
                res.is_overtime = True
            if res.status == ReservationStatus.OVERTIME:
                res.status = ReservationStatus.RELEASED
            if locker.status in {LockerStatus.IN_USE, LockerStatus.PENDING_RELEASE}:
                locker.status = LockerStatus.AVAILABLE

        elif record.type == AnomalyType.RELEASE_CONFIRM_MISSING and res and locker:
            if res.release and locker.status == LockerStatus.PENDING_RELEASE:
                locker.status = LockerStatus.AVAILABLE

        elif record.type == AnomalyType.NO_SHOW and res and locker:
            if locker.status == LockerStatus.RESERVED:
                locker.status = LockerStatus.AVAILABLE

        elif record.type == AnomalyType.DISABLED_LOCKER_RESERVED and locker:
            pass

        elif record.type == AnomalyType.ABNORMAL_OCCUPANCY and locker:
            pass

    def _sync_anomaly_rejected(self, record: AnomalyRecord, res: Optional[Reservation], locker: Optional[Locker]):
        if record.type == AnomalyType.NO_SHOW and res and locker:
            if res.status == ReservationStatus.NO_SHOW:
                res.status = ReservationStatus.RESERVED
                if locker.status == LockerStatus.AVAILABLE:
                    locker.status = LockerStatus.RESERVED

        elif record.type == AnomalyType.OVERTIME and res and locker:
            if res.status == ReservationStatus.OVERTIME:
                if res.release:
                    res.status = ReservationStatus.RELEASED
                else:
                    res.status = ReservationStatus.CHECKED_IN

        elif record.type == AnomalyType.RELEASE_CONFIRM_MISSING and res and locker:
            pass

        elif record.type == AnomalyType.DISABLED_LOCKER_RESERVED and locker:
            pass

        elif record.type == AnomalyType.ABNORMAL_OCCUPANCY and locker:
            pass

    def update_anomaly_record(self, record_id: str, data: AnomalyRecordUpdate) -> Optional[AnomalyRecord]:
        record = self.anomaly_records.get(record_id)
        if not record:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(record, key, value)
        return record

    def get_anomalies_for_reservation(self, reservation_id: str) -> List[AnomalyRecord]:
        return [a for a in self.anomaly_records.values() if a.reservation_id == reservation_id]

    def _format_remaining(self, seconds: Optional[int]) -> Optional[str]:
        if seconds is None or seconds < 0:
            return None
        if seconds >= 86400:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days}天{hours}小时" if hours > 0 else f"{days}天"
        elif seconds >= 3600:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}小时{mins}分钟" if mins > 0 else f"{hours}小时"
        else:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}分{secs}秒" if secs > 0 else f"{mins}分钟"

    def _compute_fulfillment_summary(
        self,
        res: Reservation,
        locker: Locker,
        anomalies: List[AnomalyRecord],
    ) -> ReservationFulfillmentSummary:
        now = datetime.utcnow()
        current_stage = "reserved"
        current_stage_label = "已预约"
        next_action = None
        next_action_label = None
        time_left_seconds: Optional[int] = None

        active_anomalies = [a for a in anomalies if a.status in {AnomalyStatus.PENDING, AnomalyStatus.CONFIRMED}]

        if res.status == ReservationStatus.CANCELLED:
            current_stage = "cancelled"
            current_stage_label = "已取消"
        elif res.status == ReservationStatus.NO_SHOW:
            current_stage = "no_show"
            current_stage_label = "未签到"
        elif res.status == ReservationStatus.RESERVED:
            current_stage = "reserved"
            current_stage_label = "待签到"
            next_action = "check_in"
            next_action_label = "签到"
            deadline = res.start_time + timedelta(minutes=settings.auto_checkin_timeout_minutes)
            delta = int((deadline - now).total_seconds())
            time_left_seconds = delta
        elif res.status == ReservationStatus.CHECKED_IN:
            current_stage = "checked_in"
            current_stage_label = "使用中"
            next_action = "release"
            next_action_label = "释放储物格"
            delta = int((res.end_time - now).total_seconds())
            time_left_seconds = delta
        elif res.status == ReservationStatus.OVERTIME:
            current_stage = "overtime"
            current_stage_label = "超时使用"
            next_action = "release"
            next_action_label = "释放储物格"
            delta = int((res.end_time - now).total_seconds())
            time_left_seconds = delta
        elif res.status == ReservationStatus.RELEASED:
            if locker.status == LockerStatus.PENDING_RELEASE:
                current_stage = "pending_confirm"
                current_stage_label = "待确认释放"
                next_action = "confirm_release"
                next_action_label = "确认释放"
                if res.release:
                    deadline = res.release.release_time + timedelta(hours=1)
                    delta = int((deadline - now).total_seconds())
                    time_left_seconds = delta
            else:
                current_stage = "completed"
                current_stage_label = "已完成"

        return ReservationFulfillmentSummary(
            current_stage=current_stage,
            current_stage_label=current_stage_label,
            next_action=next_action,
            next_action_label=next_action_label,
            time_left_seconds=time_left_seconds if time_left_seconds is not None and time_left_seconds > 0 else None,
            time_left_text=self._format_remaining(time_left_seconds if time_left_seconds and time_left_seconds > 0 else None),
            has_active_anomaly=len(active_anomalies) > 0,
            active_anomaly_count=len(active_anomalies),
        )

    def _enrich_fulfillment_steps(
        self,
        res: Reservation,
        locker: Locker,
        steps: List[FulfillmentStep],
    ) -> List[FulfillmentStep]:
        now = datetime.utcnow()
        enriched: List[FulfillmentStep] = []
        for s in steps:
            deadline: Optional[datetime] = None
            remaining: Optional[int] = None
            is_warning = False
            is_overdue = False

            if s.step == "check_in" and s.status == "pending":
                deadline = res.start_time + timedelta(minutes=settings.auto_checkin_timeout_minutes)
            elif s.step == "release" and s.status == "pending":
                deadline = res.end_time
            elif s.step == "confirm_release" and s.status == "pending" and res.release:
                deadline = res.release.release_time + timedelta(hours=1)

            if deadline and s.status == "pending":
                remaining = int((deadline - now).total_seconds())
                if remaining < 0:
                    is_overdue = True
                elif remaining <= 600:
                    is_warning = True

            enriched.append(FulfillmentStep(
                step=s.step,
                label=s.label,
                status=s.status,
                completed_at=s.completed_at,
                operator=s.operator,
                remarks=s.remarks,
                deadline_at=deadline,
                remaining_seconds=remaining if remaining is not None and remaining >= 0 else None,
                is_warning=is_warning,
                is_overdue=is_overdue,
            ))
        return enriched

    def get_reservation_fulfillment_detail(self, res_id: str) -> Optional[ReservationFulfillmentDetail]:
        res = self.get_reservation(res_id)
        if not res:
            return None
        locker = self.get_locker(res.locker_id)
        if not locker:
            return None

        area = self.get_area(locker.area_id)

        raw_steps: List[FulfillmentStep] = []

        raw_steps.append(FulfillmentStep(
            step="create",
            label="创建预约",
            status="completed",
            completed_at=res.created_at,
            operator=res.created_by,
        ))

        if res.check_in:
            raw_steps.append(FulfillmentStep(
                step="check_in",
                label="签到",
                status="completed",
                completed_at=res.check_in.check_in_time,
                operator=res.check_in.operator,
                remarks=res.check_in.remarks,
            ))
        elif res.status in {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW}:
            raw_steps.append(FulfillmentStep(
                step="check_in",
                label="签到",
                status="skipped" if res.status == ReservationStatus.CANCELLED else "failed",
            ))
        else:
            raw_steps.append(FulfillmentStep(
                step="check_in",
                label="签到",
                status="pending",
            ))

        if res.release:
            raw_steps.append(FulfillmentStep(
                step="release",
                label="释放储物格",
                status="completed",
                completed_at=res.release.release_time,
                operator=res.release.operator,
                remarks=res.release.remarks,
            ))
        elif res.status in {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW}:
            raw_steps.append(FulfillmentStep(
                step="release",
                label="释放储物格",
                status="skipped",
            ))
        else:
            raw_steps.append(FulfillmentStep(
                step="release",
                label="释放储物格",
                status="pending",
            ))

        if res.release and locker.status == LockerStatus.AVAILABLE:
            raw_steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="completed",
            ))
        elif res.release and locker.status == LockerStatus.PENDING_RELEASE:
            raw_steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="pending",
            ))
        elif res.status in {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW}:
            raw_steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="skipped",
            ))
        else:
            raw_steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="pending",
            ))

        steps = self._enrich_fulfillment_steps(res, locker, raw_steps)

        anomalies = self.get_anomalies_for_reservation(res_id)

        can_raise_anomaly = res.status in {
            ReservationStatus.RESERVED,
            ReservationStatus.CHECKED_IN,
            ReservationStatus.OVERTIME,
            ReservationStatus.RELEASED,
        }

        can_release = res.status in {ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME}
        can_check_in = res.status == ReservationStatus.RESERVED
        can_cancel = res.status == ReservationStatus.RESERVED

        can_confirm_release = (
            res.status in {ReservationStatus.RELEASED, ReservationStatus.OVERTIME}
            and res.release is not None
            and locker.status == LockerStatus.PENDING_RELEASE
        )

        available_actions: List[Dict] = []
        if can_check_in:
            available_actions.append({"action": "check_in", "label": "签到", "priority": 1})
        if can_release:
            available_actions.append({"action": "release", "label": "释放储物格", "priority": 2})
        if can_confirm_release:
            available_actions.append({"action": "confirm_release", "label": "确认释放", "priority": 3})
        if can_cancel:
            available_actions.append({"action": "cancel", "label": "取消预约", "priority": 4})
        if can_raise_anomaly:
            available_actions.append({"action": "raise_anomaly", "label": "发起异常", "priority": 5})

        fulfillment_summary = self._compute_fulfillment_summary(res, locker, anomalies)

        return ReservationFulfillmentDetail(
            reservation=res,
            locker=locker,
            area=area,
            fulfillment_steps=steps,
            anomalies=anomalies,
            fulfillment_summary=fulfillment_summary,
            can_raise_anomaly=can_raise_anomaly,
            can_release=can_release,
            can_confirm_release=can_confirm_release,
            can_check_in=can_check_in,
            can_cancel=can_cancel,
            available_actions=available_actions,
        )

    def get_unresolved_anomalies_for_locker(self, locker_id: str) -> List[AnomalyRecord]:
        return [
            a for a in self.anomaly_records.values()
            if a.locker_id == locker_id and a.status in {AnomalyStatus.PENDING, AnomalyStatus.CONFIRMED}
        ]

    def get_locker_anomaly_impact(self, locker_id: str) -> Optional[LockerAnomalyImpact]:
        locker = self.get_locker(locker_id)
        if not locker:
            return None

        area = self.get_area(locker.area_id)
        unresolved_anomalies = self.get_unresolved_anomalies_for_locker(locker_id)
        pending_disable_reasons = self.list_disable_reasons(locker_id=locker_id, resolved=False)
        active_reservations = self.get_active_reservations_for_locker(locker_id)

        can_reserve = True
        can_disable = True
        can_restore = True
        impact_reasons: List[str] = []

        if locker.status == LockerStatus.DISABLED:
            can_reserve = False
        else:
            can_restore = False

        if unresolved_anomalies:
            can_reserve = False
            can_disable = False
            can_restore = False
            impact_reasons.append(f"存在 {len(unresolved_anomalies)} 条未解决的异常记录")
        if pending_disable_reasons:
            can_reserve = False
            can_restore = False
            impact_reasons.append(f"存在 {len(pending_disable_reasons)} 条未处理的停用原因")
        if active_reservations:
            can_reserve = False
            can_disable = False
            can_restore = False
            impact_reasons.append(f"存在 {len(active_reservations)} 个未完成的预约")

        if locker.status in {LockerStatus.IN_USE, LockerStatus.RESERVED, LockerStatus.PENDING_RELEASE}:
            can_reserve = False
            if can_disable and locker.status != LockerStatus.RESERVED:
                can_disable = False

        return LockerAnomalyImpact(
            locker_id=locker.id,
            locker_number=locker.locker_number,
            current_status=locker.status,
            area_id=locker.area_id,
            area_name=area.name if area else None,
            unresolved_anomaly_count=len(unresolved_anomalies),
            unresolved_anomalies=unresolved_anomalies,
            pending_disable_reason_count=len(pending_disable_reasons),
            pending_disable_reasons=pending_disable_reasons,
            active_reservation_count=len(active_reservations),
            active_reservations=active_reservations,
            can_reserve=can_reserve,
            can_disable=can_disable,
            can_restore=can_restore,
            impact_reasons=impact_reasons,
        )

    def check_locker_availability(self, locker_id: str) -> Optional[LockerAvailabilityCheck]:
        locker = self.get_locker(locker_id)
        if not locker:
            return None

        blocking_reasons: List[str] = []
        unresolved_disable_reasons = self.list_disable_reasons(locker_id=locker_id, resolved=False)
        active_reservations = self.get_active_reservations_for_locker(locker_id)
        unresolved_anomalies = self.get_unresolved_anomalies_for_locker(locker_id)
        anomaly_impact = self.get_locker_anomaly_impact(locker_id)

        can_reserve = True
        can_restore = True
        can_disable = True

        if locker.status == LockerStatus.DISABLED:
            can_reserve = False
            blocking_reasons.append("储物格已停用")
        else:
            can_restore = False

        if unresolved_disable_reasons:
            can_reserve = False
            can_restore = False
            blocking_reasons.append(f"存在 {len(unresolved_disable_reasons)} 条未解决的停用原因")

        if active_reservations:
            can_reserve = False
            can_restore = False
            can_disable = False
            blocking_reasons.append(f"存在 {len(active_reservations)} 个未完成的预约")

        if unresolved_anomalies:
            can_reserve = False
            can_restore = False
            can_disable = False
            blocking_reasons.append(f"存在 {len(unresolved_anomalies)} 条未解决的异常记录")

        if locker.status in {LockerStatus.IN_USE, LockerStatus.RESERVED, LockerStatus.PENDING_RELEASE}:
            can_reserve = False
            if locker.status != LockerStatus.RESERVED or not active_reservations:
                status_label = {
                    LockerStatus.IN_USE: "使用中",
                    LockerStatus.RESERVED: "已被预约",
                    LockerStatus.PENDING_RELEASE: "待确认释放",
                }.get(locker.status, locker.status)
                blocking_reasons.append(f"储物格当前状态: {status_label}")
            if locker.status != LockerStatus.RESERVED:
                can_disable = False

        return LockerAvailabilityCheck(
            locker_id=locker.id,
            locker_number=locker.locker_number,
            current_status=locker.status,
            can_reserve=can_reserve,
            can_restore=can_restore,
            can_disable=can_disable,
            blocking_reasons=blocking_reasons,
            unresolved_disable_reasons=unresolved_disable_reasons,
            active_reservations=active_reservations,
            unresolved_anomalies=unresolved_anomalies,
            anomaly_impact=anomaly_impact,
        )

    def list_anomaly_records_enhanced(
        self,
        status: Optional[AnomalyStatus] = None,
        anomaly_type: Optional[AnomalyType] = None,
        area_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
        locker_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[AnomalyRecord]:
        result = list(self.anomaly_records.values())
        if status:
            result = [a for a in result if a.status == status]
        if anomaly_type:
            result = [a for a in result if a.type == anomaly_type]
        if area_id:
            filtered: List[AnomalyRecord] = []
            for a in result:
                target_locker_id = a.locker_id
                if not target_locker_id and a.reservation_id:
                    res = self.get_reservation(a.reservation_id)
                    if res:
                        target_locker_id = res.locker_id
                if target_locker_id:
                    locker = self.get_locker(target_locker_id)
                    if locker and locker.area_id == area_id:
                        filtered.append(a)
            result = filtered
        if reservation_id:
            result = [a for a in result if a.reservation_id == reservation_id]
        if locker_id:
            result = [a for a in result if a.locker_id == locker_id]
        if start_date:
            result = [a for a in result if a.created_at.date() >= start_date]
        if end_date:
            result = [a for a in result if a.created_at.date() <= end_date]
        return result

    def list_anomaly_with_relations(
        self,
        status: Optional[AnomalyStatus] = None,
        anomaly_type: Optional[AnomalyType] = None,
        area_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
        locker_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[AnomalyRecordWithRelations]:
        records = self.list_anomaly_records_enhanced(
            status=status, anomaly_type=anomaly_type, area_id=area_id,
            reservation_id=reservation_id, locker_id=locker_id,
            start_date=start_date, end_date=end_date,
        )
        enriched: List[AnomalyRecordWithRelations] = []
        for a in records:
            res = self.get_reservation(a.reservation_id) if a.reservation_id else None
            target_locker_id = a.locker_id or (res.locker_id if res else None)
            locker = self.get_locker(target_locker_id) if target_locker_id else None
            area = self.get_area(locker.area_id) if locker else None
            data = a.model_dump()
            enriched.append(AnomalyRecordWithRelations(
                **data,
                reservation=res,
                locker=locker,
                area=area,
                locker_number=locker.locker_number if locker else None,
                area_name=area.name if area else None,
                user_name=res.user_name if res else None,
            ))
        return enriched

    def get_anomaly_statistics(self, area_id: Optional[str] = None) -> AnomalyStatistics:
        all_records = self.list_anomaly_records_enhanced(area_id=area_id)
        by_type: Dict[str, int] = {}
        for t in AnomalyType:
            by_type[t.value] = 0
        by_area: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        for s in AnomalyStatus:
            by_status[s.value] = 0

        today = date.today()
        today_new = 0
        resolved_today = 0
        resolve_minutes_list: List[int] = []

        for a in all_records:
            by_type[a.type.value] = by_type.get(a.type.value, 0) + 1
            by_status[a.status.value] = by_status.get(a.status.value, 0) + 1
            target_locker_id = a.locker_id
            if not target_locker_id and a.reservation_id:
                res = self.get_reservation(a.reservation_id)
                if res:
                    target_locker_id = res.locker_id
            if target_locker_id:
                locker = self.get_locker(target_locker_id)
                if locker:
                    area_name = locker.area_id
                    by_area[area_name] = by_area.get(area_name, 0) + 1
            if a.created_at.date() == today:
                today_new += 1
            if a.status == AnomalyStatus.RESOLVED and a.reviewed_at:
                if a.reviewed_at.date() == today:
                    resolved_today += 1
                delta = a.reviewed_at - a.created_at
                resolve_minutes_list.append(int(delta.total_seconds() // 60))

        avg_resolve = (sum(resolve_minutes_list) / len(resolve_minutes_list)) if resolve_minutes_list else None

        return AnomalyStatistics(
            total=len(all_records),
            pending=len([a for a in all_records if a.status == AnomalyStatus.PENDING]),
            confirmed=len([a for a in all_records if a.status == AnomalyStatus.CONFIRMED]),
            resolved=len([a for a in all_records if a.status == AnomalyStatus.RESOLVED]),
            rejected=len([a for a in all_records if a.status == AnomalyStatus.REJECTED]),
            by_type=by_type,
            by_area=by_area,
            by_status=by_status,
            today_new=today_new,
            resolved_today=resolved_today,
            avg_resolve_minutes=round(avg_resolve, 1) if avg_resolve is not None else None,
        )

    def get_anomaly_type_distribution(self, area_id: Optional[str] = None) -> List[AnomalyTypeDistribution]:
        type_labels = {
            AnomalyType.NO_SHOW: "未签到",
            AnomalyType.OVERTIME: "超时使用",
            AnomalyType.DISABLED_LOCKER_RESERVED: "停用储物格仍有预约",
            AnomalyType.RELEASE_CONFIRM_MISSING: "释放未确认",
            AnomalyType.ABNORMAL_OCCUPANCY: "异常占用",
        }
        records = self.list_anomaly_records_enhanced(area_id=area_id)
        total = len(records)
        counts: Dict[str, int] = {}
        for t in AnomalyType:
            counts[t.value] = 0
        for a in records:
            counts[a.type.value] = counts.get(a.type.value, 0) + 1

        dist = []
        for t in AnomalyType:
            count = counts.get(t.value, 0)
            pct = round(((count / total) * 100) if total > 0 else 0.0, 2)
            dist.append(AnomalyTypeDistribution(
                type=t,
                label=type_labels.get(t, t.value),
                count=count,
                percentage=pct,
            ))
        return dist

    def get_area_anomaly_summary(self) -> List[AreaAnomalySummary]:
        areas = self.list_areas()
        result = []
        for area in areas:
            records = self.list_anomaly_records_enhanced(area_id=area.id)
            result.append(AreaAnomalySummary(
                area_id=area.id,
                area_name=area.name,
                total=len(records),
                pending=len([a for a in records if a.status == AnomalyStatus.PENDING]),
                confirmed=len([a for a in records if a.status == AnomalyStatus.CONFIRMED]),
                resolved=len([a for a in records if a.status == AnomalyStatus.RESOLVED]),
                rejected=len([a for a in records if a.status == AnomalyStatus.REJECTED]),
            ))
        return result

    def list_reservations_with_fulfillment(
        self,
        area_id: Optional[str] = None,
        locker_id: Optional[str] = None,
        user_name: Optional[str] = None,
        status: Optional[ReservationStatus] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_overtime: Optional[bool] = None,
    ) -> List[ReservationWithFulfillment]:
        reservations = self.list_reservations(
            area_id=area_id, locker_id=locker_id, user_name=user_name,
            status=status, start_date=start_date, end_date=end_date, is_overtime=is_overtime,
        )
        result: List[ReservationWithFulfillment] = []
        for res in reservations:
            locker = self.get_locker(res.locker_id)
            area = self.get_area(locker.area_id) if locker else None
            anomalies = self.get_anomalies_for_reservation(res.id)
            summary = self._compute_fulfillment_summary(res, locker, anomalies) if locker else None
            data = res.model_dump()
            result.append(ReservationWithFulfillment(
                **data,
                locker_number=locker.locker_number if locker else None,
                area_id=locker.area_id if locker else None,
                area_name=area.name if area else None,
                fulfillment_summary=summary,
                anomaly_count=len(anomalies),
            ))
        return result

    def get_fulfillment_overview(self, area_id: Optional[str] = None) -> FulfillmentOverview:
        reservations = self.list_reservations(area_id=area_id)
        now = datetime.utcnow()
        warning_count = 0
        overdue_count = 0
        overview = FulfillmentOverview(total_reservations=len(reservations))
        for res in reservations:
            locker = self.get_locker(res.locker_id)
            if res.status == ReservationStatus.RESERVED:
                overview.stage_reserved += 1
                deadline = res.start_time + timedelta(minutes=settings.auto_checkin_timeout_minutes)
                delta = int((deadline - now).total_seconds())
                if 0 < delta <= 600:
                    warning_count += 1
                elif delta < 0:
                    overdue_count += 1
            elif res.status == ReservationStatus.CHECKED_IN:
                overview.stage_checked_in += 1
                delta = int((res.end_time - now).total_seconds())
                if 0 < delta <= 1800:
                    warning_count += 1
                elif delta < 0:
                    overdue_count += 1
            elif res.status == ReservationStatus.OVERTIME:
                overview.stage_overtime += 1
                overdue_count += 1
            elif res.status == ReservationStatus.RELEASED:
                if locker and locker.status == LockerStatus.PENDING_RELEASE:
                    overview.stage_released += 1
                    if res.release:
                        deadline = res.release.release_time + timedelta(hours=1)
                        delta = int((deadline - now).total_seconds())
                        if 0 < delta <= 600:
                            warning_count += 1
                        elif delta < 0:
                            overdue_count += 1
                else:
                    overview.stage_completed += 1
            elif res.status == ReservationStatus.CANCELLED:
                overview.stage_cancelled += 1
            elif res.status == ReservationStatus.NO_SHOW:
                overview.stage_no_show += 1
        overview.warning_count = warning_count
        overview.overdue_count = overdue_count
        return overview

    def disable_locker_with_validation(self, locker_id: str, reason_data: DisableReasonCreate) -> Optional[DisableReason]:
        check = self.check_locker_availability(locker_id)
        if not check:
            return None
        if not check.can_disable:
            return None
        dr = self.create_disable_reason(reason_data)
        self.update_locker(locker_id, LockerUpdate(status=LockerStatus.DISABLED))
        return dr

    def restore_locker_with_validation(self, locker_id: str) -> Optional[Locker]:
        check = self.check_locker_availability(locker_id)
        if not check:
            return None
        if not check.can_restore:
            return None
        unresolved = self.list_disable_reasons(locker_id=locker_id, resolved=False)
        for dr in unresolved:
            self.resolve_disable_reason(dr.id, "system_restore")
        locker = self.get_locker(locker_id)
        if locker and locker.status == LockerStatus.DISABLED:
            self.update_locker(locker_id, LockerUpdate(status=LockerStatus.AVAILABLE))
        return self.get_locker(locker_id)

    def create_anomaly_with_reporter(self, data: AnomalyRecordCreate, reporter: str) -> AnomalyRecord:
        data.reporter = reporter
        return self.create_anomaly_record(data)

    def resolve_anomaly_with_notes(
        self,
        record_id: str,
        resolve_data: AnomalyResolveData,
        reviewer: str,
    ) -> Optional[AnomalyRecord]:
        record = self.get_anomaly_record(record_id)
        if not record:
            return None
        if record.status not in {AnomalyStatus.PENDING, AnomalyStatus.CONFIRMED}:
            return None
        record.status = AnomalyStatus.RESOLVED
        record.reviewer = reviewer
        record.review_notes = resolve_data.review_notes
        if resolve_data.handling_notes:
            if record.supplementary_notes:
                record.supplementary_notes = (record.supplementary_notes + "\n处理说明: " + resolve_data.handling_notes)
            else:
                record.supplementary_notes = "处理说明: " + resolve_data.handling_notes
        record.reviewed_at = datetime.utcnow()
        res = self.get_reservation(record.reservation_id) if record.reservation_id else None
        locker = self.get_locker(record.locker_id) if record.locker_id else (self.get_locker(res.locker_id) if res else None)
        self._sync_anomaly_resolved(record, res, locker)
        return record

    def create_credit_record(self, data: CreditRecordCreate) -> CreditRecord:
        record = CreditRecord(
            id=self._gen_id(),
            **data.model_dump(),
            created_at=datetime.utcnow(),
        )
        self.credit_records[record.id] = record
        self._update_user_credit_profile(record.user_id_number)
        return record

    def get_credit_record(self, record_id: str) -> Optional[CreditRecord]:
        return self.credit_records.get(record_id)

    def list_credit_records(
        self,
        user_id_number: Optional[str] = None,
        violation_type: Optional[ViolationType] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[CreditRecord]:
        result = list(self.credit_records.values())
        if user_id_number:
            result = [c for c in result if c.user_id_number == user_id_number]
        if violation_type:
            result = [c for c in result if c.violation_type == violation_type]
        if start_date:
            result = [c for c in result if c.created_at.date() >= start_date]
        if end_date:
            result = [c for c in result if c.created_at.date() <= end_date]
        return result

    def get_user_credit_profile(self, user_id_number: str) -> Optional[UserCreditProfile]:
        return self.user_credit_profiles.get(user_id_number)

    def _get_or_create_credit_profile(self, user_id_number: str) -> UserCreditProfile:
        profile = self.user_credit_profiles.get(user_id_number)
        if not profile:
            profile = UserCreditProfile(
                user_id_number=user_id_number,
                violation_counts={vt.value: 0 for vt in ViolationType},
                last_updated=datetime.utcnow(),
            )
            self.user_credit_profiles[user_id_number] = profile
        return profile

    def _update_user_credit_profile(self, user_id_number: str) -> UserCreditProfile:
        profile = self._get_or_create_credit_profile(user_id_number)
        now = datetime.utcnow()

        for res in self.reservations.values():
            if res.user_id_number == user_id_number:
                if profile.user_name is None and res.user_name:
                    profile.user_name = res.user_name
                if profile.user_phone is None and res.user_phone:
                    profile.user_phone = res.user_phone

        active_rules = {rule.violation_type: rule for rule in self.risk_rules.values() if rule.is_active}

        for vt in ViolationType:
            rule = active_rules.get(vt)
            if rule:
                window_start = now - timedelta(days=rule.time_window_days)
                count = len([
                    c for c in self.credit_records.values()
                    if c.user_id_number == user_id_number
                    and c.violation_type == vt
                    and c.created_at >= window_start
                ])
            else:
                count = len([
                    c for c in self.credit_records.values()
                    if c.user_id_number == user_id_number and c.violation_type == vt
                ])
            profile.violation_counts[vt.value] = count

        total = sum(profile.violation_counts.values())
        profile.total_violations = total

        user_records = [c for c in self.credit_records.values() if c.user_id_number == user_id_number]
        if user_records:
            profile.last_violation_at = max(c.created_at for c in user_records)

        max_risk = RiskLevel.NORMAL
        restriction_rule = None
        for vt, rule in active_rules.items():
            count = profile.violation_counts.get(vt.value, 0)
            if count >= rule.restricted_threshold:
                if max_risk != RiskLevel.RESTRICTED:
                    max_risk = RiskLevel.RESTRICTED
                    restriction_rule = rule
            elif count >= rule.high_risk_threshold:
                if max_risk.value < RiskLevel.HIGH_RISK.value:
                    max_risk = RiskLevel.HIGH_RISK
            elif count >= rule.medium_risk_threshold:
                if max_risk.value < RiskLevel.MEDIUM_RISK.value:
                    max_risk = RiskLevel.MEDIUM_RISK
            elif count >= rule.low_risk_threshold:
                if max_risk.value < RiskLevel.LOW_RISK.value:
                    max_risk = RiskLevel.LOW_RISK

        if profile.manually_lifted and max_risk == RiskLevel.RESTRICTED:
            max_risk = RiskLevel.HIGH_RISK

        profile.risk_level = max_risk

        if max_risk == RiskLevel.RESTRICTED and restriction_rule:
            profile.is_restricted = True
            if not profile.restriction_until or profile.restriction_until < now:
                profile.restriction_until = now + timedelta(days=restriction_rule.restriction_days)
                profile.restriction_reason = f"违规次数达到限制阈值（{restriction_rule.name}）"
        elif profile.restriction_until and profile.restriction_until < now:
            profile.is_restricted = False
            profile.restriction_until = None
            profile.restriction_reason = None
        else:
            profile.is_restricted = max_risk == RiskLevel.RESTRICTED

        profile.last_updated = now
        return profile

    def refresh_all_credit_profiles(self):
        for user_id_number in list(self.user_credit_profiles.keys()):
            self._update_user_credit_profile(user_id_number)

    def get_user_risk_reminder(self, user_id_number: str) -> UserRiskReminder:
        profile = self._get_or_create_credit_profile(user_id_number)
        self._update_user_credit_profile(user_id_number)
        profile = self.user_credit_profiles[user_id_number]

        now = datetime.utcnow()
        can_reserve = True
        warning_message = None

        if profile.is_restricted:
            if profile.restriction_until and profile.restriction_until > now:
                can_reserve = False
                days_left = (profile.restriction_until - now).days
                warning_message = f"该使用人已被限制预约，限制至 {profile.restriction_until.strftime('%Y-%m-%d')}（剩余{days_left}天），原因：{profile.restriction_reason or '违规次数过多'}"
            else:
                can_reserve = True
                self._update_user_credit_profile(user_id_number)
                profile = self.user_credit_profiles[user_id_number]
        elif profile.risk_level == RiskLevel.HIGH_RISK:
            warning_message = f"该使用人信用风险等级为高风险，共有{profile.total_violations}次违规记录，请谨慎操作"
        elif profile.risk_level == RiskLevel.MEDIUM_RISK:
            warning_message = f"该使用人信用风险等级为中风险，共有{profile.total_violations}次违规记录"
        elif profile.risk_level == RiskLevel.LOW_RISK:
            warning_message = f"该使用人信用风险等级为低风险，共有{profile.total_violations}次违规记录"

        recent_cutoff = now - timedelta(days=30)
        recent_violations = [
            c for c in self.credit_records.values()
            if c.user_id_number == user_id_number and c.created_at >= recent_cutoff
        ]
        recent_violations.sort(key=lambda c: c.created_at, reverse=True)
        recent_violations = recent_violations[:10]

        return UserRiskReminder(
            user_id_number=user_id_number,
            user_name=profile.user_name,
            user_phone=profile.user_phone,
            risk_level=profile.risk_level,
            risk_level_label=RISK_LEVEL_LABELS.get(profile.risk_level, profile.risk_level.value),
            total_violations=profile.total_violations,
            violation_counts=profile.violation_counts,
            is_restricted=profile.is_restricted,
            restriction_until=profile.restriction_until,
            can_reserve=can_reserve,
            warning_message=warning_message,
            recent_violations=recent_violations,
        )

    def can_user_reserve(self, user_id_number: str) -> bool:
        reminder = self.get_user_risk_reminder(user_id_number)
        return reminder.can_reserve

    def create_risk_rule(self, data: RiskRuleCreate) -> RiskRule:
        now = datetime.utcnow()
        rule = RiskRule(
            id=self._gen_id(),
            **data.model_dump(),
            created_at=now,
            updated_at=now,
        )
        self.risk_rules[rule.id] = rule
        return rule

    def get_risk_rule(self, rule_id: str) -> Optional[RiskRule]:
        return self.risk_rules.get(rule_id)

    def list_risk_rules(self, violation_type: Optional[ViolationType] = None, is_active: Optional[bool] = None) -> List[RiskRule]:
        result = list(self.risk_rules.values())
        if violation_type:
            result = [r for r in result if r.violation_type == violation_type]
        if is_active is not None:
            result = [r for r in result if r.is_active == is_active]
        return result

    def update_risk_rule(self, rule_id: str, data: RiskRuleUpdate) -> Optional[RiskRule]:
        rule = self.risk_rules.get(rule_id)
        if not rule:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)
        rule.updated_at = datetime.utcnow()
        self.refresh_all_credit_profiles()
        return rule

    def delete_risk_rule(self, rule_id: str) -> bool:
        if rule_id in self.risk_rules:
            del self.risk_rules[rule_id]
            self.refresh_all_credit_profiles()
            return True
        return False

    def manually_lift_restriction(self, user_id_number: str, operator: str, notes: Optional[str] = None) -> Optional[UserCreditProfile]:
        profile = self.user_credit_profiles.get(user_id_number)
        if not profile:
            return None
        if not profile.is_restricted:
            return None
        profile.manually_lifted = True
        profile.is_restricted = False
        profile.restriction_until = None
        profile.restriction_reason = f"由 {operator} 人工解除限制" + (f"：{notes}" if notes else "")
        profile.last_updated = datetime.utcnow()
        self._update_user_credit_profile(user_id_number)
        return self.user_credit_profiles[user_id_number]

    def manually_restrict_user(self, user_id_number: str, operator: str, restriction_days: int = 30, notes: Optional[str] = None) -> Optional[UserCreditProfile]:
        profile = self._get_or_create_credit_profile(user_id_number)
        now = datetime.utcnow()
        profile.is_restricted = True
        profile.restriction_until = now + timedelta(days=restriction_days)
        profile.restriction_reason = f"由 {operator} 人工设置限制" + (f"：{notes}" if notes else "")
        profile.manually_lifted = False
        profile.last_updated = now
        return profile

    def supervisor_confirm_risk(self, user_id_number: str, operator: str, notes: Optional[str] = None) -> Optional[UserCreditProfile]:
        profile = self.user_credit_profiles.get(user_id_number)
        if not profile:
            return None
        if notes:
            existing = profile.restriction_reason or ""
            profile.restriction_reason = existing + f" | 监督确认({operator}): {notes}" if existing else f"监督确认({operator}): {notes}"
        profile.last_updated = datetime.utcnow()
        return profile

    def list_high_risk_users(self, min_risk_level: RiskLevel = RiskLevel.MEDIUM_RISK) -> List[UserCreditProfile]:
        risk_order = {
            RiskLevel.NORMAL: 0,
            RiskLevel.LOW_RISK: 1,
            RiskLevel.MEDIUM_RISK: 2,
            RiskLevel.HIGH_RISK: 3,
            RiskLevel.RESTRICTED: 4,
        }
        min_order = risk_order.get(min_risk_level, 0)
        result = [
            p for p in self.user_credit_profiles.values()
            if risk_order.get(p.risk_level, 0) >= min_order
        ]
        result.sort(key=lambda p: (-risk_order.get(p.risk_level, 0), -p.total_violations))
        return result

    def get_credit_risk_statistics(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> CreditRiskStatistics:
        all_profiles = list(self.user_credit_profiles.values())
        total_users = len(all_profiles)

        risk_counts = {rl: 0 for rl in RiskLevel}
        for p in all_profiles:
            risk_counts[p.risk_level] = risk_counts.get(p.risk_level, 0) + 1

        distribution = []
        for rl in RiskLevel:
            count = risk_counts.get(rl, 0)
            pct = round(((count / total_users) * 100) if total_users > 0 else 0.0, 2)
            distribution.append(CreditRiskDistribution(
                risk_level=rl,
                risk_level_label=RISK_LEVEL_LABELS.get(rl, rl.value),
                count=count,
                percentage=pct,
            ))

        user_violation_map: Dict[str, Dict] = {}
        for c in self.credit_records.values():
            if start_date and c.created_at.date() < start_date:
                continue
            if end_date and c.created_at.date() > end_date:
                continue
            if c.user_id_number not in user_violation_map:
                profile = self.user_credit_profiles.get(c.user_id_number)
                user_violation_map[c.user_id_number] = {
                    "user_name": c.user_name or (profile.user_name if profile else None),
                    "total": 0,
                    "counts": {vt.value: 0 for vt in ViolationType},
                    "risk_level": profile.risk_level if profile else RiskLevel.NORMAL,
                }
            user_violation_map[c.user_id_number]["total"] += 1
            user_violation_map[c.user_id_number]["counts"][c.violation_type.value] += 1

        ranking = [
            ViolationRankingItem(
                user_name=v["user_name"],
                user_id_number=k,
                total_violations=v["total"],
                violation_counts=v["counts"],
                risk_level=v["risk_level"],
            )
            for k, v in user_violation_map.items()
        ]
        ranking.sort(key=lambda x: -x.total_violations)

        trend = []
        if start_date and end_date:
            current = start_date
            while current <= end_date:
                day_violations = len([
                    c for c in self.credit_records.values()
                    if c.created_at.date() == current
                ])
                day_restricted = len([
                    p for p in all_profiles
                    if p.is_restricted and p.restriction_until and p.restriction_until.date() >= current
                ])
                trend.append(RiskTrendItem(
                    date=current,
                    new_violations=day_violations,
                    total_restricted=day_restricted,
                ))
                current += timedelta(days=1)

        return CreditRiskStatistics(
            total_users=total_users,
            normal_count=risk_counts.get(RiskLevel.NORMAL, 0),
            low_risk_count=risk_counts.get(RiskLevel.LOW_RISK, 0),
            medium_risk_count=risk_counts.get(RiskLevel.MEDIUM_RISK, 0),
            high_risk_count=risk_counts.get(RiskLevel.HIGH_RISK, 0),
            restricted_count=risk_counts.get(RiskLevel.RESTRICTED, 0),
            distribution=distribution,
            violation_ranking=ranking,
            risk_trend=trend,
        )

    def _anomaly_type_to_violation_type(self, anomaly_type: AnomalyType) -> Optional[ViolationType]:
        mapping = {
            AnomalyType.NO_SHOW: ViolationType.NO_SHOW,
            AnomalyType.OVERTIME: ViolationType.OVERTIME,
            AnomalyType.ABNORMAL_OCCUPANCY: ViolationType.ABNORMAL_OCCUPANCY,
            AnomalyType.RELEASE_CONFIRM_MISSING: ViolationType.RELEASE_UNCONFIRMED,
        }
        return mapping.get(anomaly_type)

    def record_violation_from_anomaly(self, anomaly: AnomalyRecord) -> Optional[CreditRecord]:
        violation_type = self._anomaly_type_to_violation_type(anomaly.type)
        if not violation_type:
            return None

        res = self.get_reservation(anomaly.reservation_id) if anomaly.reservation_id else None
        if not res:
            return None

        user_id_number = res.user_id_number
        existing = [
            c for c in self.credit_records.values()
            if c.user_id_number == user_id_number
            and c.anomaly_record_id == anomaly.id
        ]
        if existing:
            return None

        data = CreditRecordCreate(
            user_id_number=user_id_number,
            user_phone=res.user_phone,
            user_name=res.user_name,
            violation_type=violation_type,
            reservation_id=res.id,
            anomaly_record_id=anomaly.id,
            description=anomaly.description,
        )
        return self.create_credit_record(data)


db = InMemoryDB()
