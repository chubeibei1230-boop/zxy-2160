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
        self._init_default_users()
        self._init_default_rule()

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
                self.create_anomaly_record(AnomalyRecordCreate(
                    type=AnomalyType.OVERTIME,
                    reservation_id=res.id,
                    locker_id=res.locker_id,
                    description=f"使用人 {res.user_name} 超时 {res.overtime_minutes} 分钟释放",
                ))
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
        locker = self.lockers.get(res.locker_id)
        if locker:
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

    def get_reservation_fulfillment_detail(self, res_id: str) -> Optional[ReservationFulfillmentDetail]:
        res = self.get_reservation(res_id)
        if not res:
            return None
        locker = self.get_locker(res.locker_id)
        if not locker:
            return None

        steps: List[FulfillmentStep] = []

        steps.append(FulfillmentStep(
            step="create",
            label="创建预约",
            status="completed",
            completed_at=res.created_at,
            operator=res.created_by,
        ))

        if res.check_in:
            steps.append(FulfillmentStep(
                step="check_in",
                label="签到",
                status="completed",
                completed_at=res.check_in.check_in_time,
                operator=res.check_in.operator,
                remarks=res.check_in.remarks,
            ))
        elif res.status in {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW}:
            steps.append(FulfillmentStep(
                step="check_in",
                label="签到",
                status="skipped" if res.status == ReservationStatus.CANCELLED else "failed",
            ))
        else:
            steps.append(FulfillmentStep(
                step="check_in",
                label="签到",
                status="pending",
            ))

        if res.release:
            steps.append(FulfillmentStep(
                step="release",
                label="释放储物格",
                status="completed",
                completed_at=res.release.release_time,
                operator=res.release.operator,
                remarks=res.release.remarks,
            ))
        elif res.status in {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW}:
            steps.append(FulfillmentStep(
                step="release",
                label="释放储物格",
                status="skipped",
            ))
        else:
            steps.append(FulfillmentStep(
                step="release",
                label="释放储物格",
                status="pending",
            ))

        if res.release and locker.status == LockerStatus.AVAILABLE:
            steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="completed",
            ))
        elif res.release and locker.status == LockerStatus.PENDING_RELEASE:
            steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="pending",
            ))
        elif res.status in {ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW}:
            steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="skipped",
            ))
        else:
            steps.append(FulfillmentStep(
                step="confirm_release",
                label="确认释放",
                status="pending",
            ))

        anomalies = self.get_anomalies_for_reservation(res_id)

        can_raise_anomaly = res.status in {
            ReservationStatus.RESERVED,
            ReservationStatus.CHECKED_IN,
            ReservationStatus.OVERTIME,
            ReservationStatus.RELEASED,
        }

        can_release = res.status in {ReservationStatus.CHECKED_IN, ReservationStatus.OVERTIME}

        can_confirm_release = (
            res.status in {ReservationStatus.RELEASED, ReservationStatus.OVERTIME}
            and res.release is not None
            and locker.status == LockerStatus.PENDING_RELEASE
        )

        return ReservationFulfillmentDetail(
            reservation=res,
            locker=locker,
            fulfillment_steps=steps,
            anomalies=anomalies,
            can_raise_anomaly=can_raise_anomaly,
            can_release=can_release,
            can_confirm_release=can_confirm_release,
        )

    def check_locker_availability(self, locker_id: str) -> Optional[LockerAvailabilityCheck]:
        locker = self.get_locker(locker_id)
        if not locker:
            return None

        blocking_reasons: List[str] = []
        unresolved_disable_reasons = self.list_disable_reasons(locker_id=locker_id, resolved=False)
        active_reservations = self.get_active_reservations_for_locker(locker_id)

        can_reserve = True
        can_restore = True

        if locker.status == LockerStatus.DISABLED:
            can_reserve = False
            blocking_reasons.append("储物格已停用")

        if unresolved_disable_reasons:
            can_reserve = False
            can_restore = False
            blocking_reasons.append(f"存在 {len(unresolved_disable_reasons)} 条未解决的停用原因")

        if active_reservations:
            can_reserve = False
            can_restore = False
            blocking_reasons.append(f"存在 {len(active_reservations)} 个未完成的预约")

        if locker.status in {LockerStatus.IN_USE, LockerStatus.RESERVED, LockerStatus.PENDING_RELEASE}:
            can_reserve = False
            if locker.status != LockerStatus.RESERVED or not active_reservations:
                status_label = {
                    LockerStatus.IN_USE: "使用中",
                    LockerStatus.RESERVED: "已被预约",
                    LockerStatus.PENDING_RELEASE: "待确认释放",
                }.get(locker.status, locker.status)
                blocking_reasons.append(f"储物格当前状态: {status_label}")

        return LockerAvailabilityCheck(
            locker_id=locker.id,
            locker_number=locker.locker_number,
            current_status=locker.status,
            can_reserve=can_reserve,
            can_restore=can_restore,
            blocking_reasons=blocking_reasons,
            unresolved_disable_reasons=unresolved_disable_reasons,
            active_reservations=active_reservations,
        )

    def list_anomaly_records_enhanced(
        self,
        status: Optional[AnomalyStatus] = None,
        anomaly_type: Optional[AnomalyType] = None,
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
        if reservation_id:
            result = [a for a in result if a.reservation_id == reservation_id]
        if locker_id:
            result = [a for a in result if a.locker_id == locker_id]
        if start_date:
            result = [a for a in result if a.created_at.date() >= start_date]
        if end_date:
            result = [a for a in result if a.created_at.date() <= end_date]
        return result

    def get_anomaly_statistics(self) -> AnomalyStatistics:
        all_records = list(self.anomaly_records.values())
        by_type: Dict[str, int] = {}
        for t in AnomalyType:
            by_type[t.value] = 0
        for a in all_records:
            by_type[a.type.value] = by_type.get(a.type.value, 0) + 1
        return AnomalyStatistics(
            total=len(all_records),
            pending=len([a for a in all_records if a.status == AnomalyStatus.PENDING]),
            confirmed=len([a for a in all_records if a.status == AnomalyStatus.CONFIRMED]),
            resolved=len([a for a in all_records if a.status == AnomalyStatus.RESOLVED]),
            rejected=len([a for a in all_records if a.status == AnomalyStatus.REJECTED]),
            by_type=by_type,
        )

    def disable_locker_with_validation(self, locker_id: str, reason_data: DisableReasonCreate) -> Optional[DisableReason]:
        check = self.check_locker_availability(locker_id)
        if not check:
            return None
        if check.active_reservations:
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


db = InMemoryDB()
