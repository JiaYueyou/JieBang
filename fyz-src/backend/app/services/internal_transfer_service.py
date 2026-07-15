"""内部岗位、企业人才、转岗规则和确定性人岗匹配服务。"""

from __future__ import annotations

import re
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidParameterError, ResourceNotFoundError
from app.models import (
    EnterpriseEmployeeDirectory,
    EnterpriseTalent,
    InternalPosition,
    TransferDecision,
    TransferRuleSet,
)
from app.schemas.internal_transfer import (
    EmployeeDirectoryCreate,
    EmployeeDirectorySummary,
    EnterpriseTalentCreate,
    EnterpriseTalentSummary,
    InternalMatchResult,
    InternalPositionCreate,
    InternalPositionStatus,
    InternalPositionSummary,
    SkillDemandSummary,
    TransferDecisionCreate,
    TransferDecisionSummary,
    TransferRuleSetCreate,
    TransferRuleSetSummary,
)


def _clean_list(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in values if item.strip()))


def _skill_key(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", value.casefold())


class InternalTransferService:
    POSITION_TRANSITIONS = {
        "draft": {"pending_approval", "closed"},
        "pending_approval": {"draft", "open", "closed"},
        "open": {"paused", "filled", "closed"},
        "paused": {"open", "closed"},
        "filled": {"closed"},
        "closed": set(),
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def talent_summary(row: EnterpriseTalent) -> EnterpriseTalentSummary:
        return EnterpriseTalentSummary(
            id=row.id,
            employee_no=row.employee_no,
            name=row.name,
            department=row.department,
            current_position=row.current_position,
            level=row.level,
            location=row.location,
            tenure_months=row.tenure_months,
            position_tenure_months=row.position_tenure_months,
            skills=row.skills or [],
            project_highlights=row.project_highlights or [],
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def employee_summary(
        row: EnterpriseEmployeeDirectory, *, in_talent_pool: bool
    ) -> EmployeeDirectorySummary:
        return EmployeeDirectorySummary(
            id=row.id,
            employee_no=row.employee_no,
            name=row.name,
            department=row.department,
            current_position=row.current_position,
            level=row.level,
            location=row.location,
            tenure_months=row.tenure_months,
            position_tenure_months=row.position_tenure_months,
            skills=row.skills or [],
            project_highlights=row.project_highlights or [],
            status=row.status,
            source=row.source,
            in_talent_pool=in_talent_pool,
            synced_at=row.synced_at,
        )

    @staticmethod
    def position_summary(row: InternalPosition) -> InternalPositionSummary:
        return InternalPositionSummary(
            id=row.id,
            title=row.title,
            standardized_title=row.standardized_title,
            department=row.department,
            receiving_manager=row.receiving_manager,
            level=row.level,
            headcount=row.headcount,
            open_reason=row.open_reason,
            responsibilities=row.responsibilities or [],
            requirements=row.requirements or [],
            required_skills=row.required_skills or [],
            trainable_skills=row.trainable_skills or [],
            transfer_profile=row.transfer_profile or [],
            manager_confirmations=row.manager_confirmations or [],
            min_tenure_months=row.min_tenure_months,
            min_position_tenure_months=row.min_position_tenure_months,
            allowed_departments=row.allowed_departments or [],
            restrictions=row.restrictions or [],
            target_start_date=row.target_start_date,
            open_from=row.open_from,
            open_until=row.open_until,
            internal_description=row.internal_description,
            status=InternalPositionStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def rule_summary(row: TransferRuleSet) -> TransferRuleSetSummary:
        return TransferRuleSetSummary(
            id=row.id,
            name=row.name,
            version=row.version,
            min_tenure_months=row.min_tenure_months,
            min_position_tenure_months=row.min_position_tenure_months,
            min_match_score=row.min_match_score,
            skill_weight=row.skill_weight,
            tenure_weight=row.tenure_weight,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_talents(self) -> list[EnterpriseTalentSummary]:
        rows = list((await self.db.execute(
            select(EnterpriseTalent).order_by(EnterpriseTalent.updated_at.desc(), EnterpriseTalent.id.desc())
        )).scalars())
        return [self.talent_summary(row) for row in rows]

    async def search_employee_directory(
        self, keyword: str, *, limit: int = 10
    ) -> list[EmployeeDirectorySummary]:
        keyword = keyword.strip()
        statement = select(EnterpriseEmployeeDirectory).where(
            EnterpriseEmployeeDirectory.status == "active"
        )
        if keyword:
            pattern = f"%{keyword}%"
            statement = statement.where(or_(
                EnterpriseEmployeeDirectory.employee_no.like(pattern),
                EnterpriseEmployeeDirectory.name.like(pattern),
            ))
        rows = list((await self.db.execute(
            statement.order_by(EnterpriseEmployeeDirectory.employee_no).limit(limit)
        )).scalars())
        employee_numbers = [row.employee_no for row in rows]
        talent_numbers = set()
        if employee_numbers:
            talent_numbers = set((await self.db.execute(
                select(EnterpriseTalent.employee_no).where(
                    EnterpriseTalent.employee_no.in_(employee_numbers)
                )
            )).scalars())
        return [
            self.employee_summary(row, in_talent_pool=row.employee_no in talent_numbers)
            for row in rows
        ]

    async def upsert_employee_directory(
        self, payload: EmployeeDirectoryCreate, *, user_id: int
    ) -> EmployeeDirectorySummary:
        row = await self.db.scalar(select(EnterpriseEmployeeDirectory).where(
            EnterpriseEmployeeDirectory.employee_no == payload.employee_no
        ))
        values = payload.model_dump(exclude={"skills", "project_highlights"})
        values["skills"] = _clean_list(payload.skills)
        values["project_highlights"] = _clean_list(payload.project_highlights)
        if row is None:
            row = EnterpriseEmployeeDirectory(**values, synced_by=user_id)
            self.db.add(row)
        else:
            for field, value in values.items():
                setattr(row, field, value)
            row.synced_by = user_id
            row.synced_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        in_pool = await self.db.scalar(select(EnterpriseTalent.id).where(
            EnterpriseTalent.employee_no == row.employee_no
        )) is not None
        return self.employee_summary(row, in_talent_pool=in_pool)

    async def create_talent(self, payload: EnterpriseTalentCreate, *, user_id: int) -> EnterpriseTalentSummary:
        exists = await self.db.scalar(select(EnterpriseTalent.id).where(EnterpriseTalent.employee_no == payload.employee_no))
        if exists is not None:
            raise InvalidParameterError("员工编号已存在")
        row = EnterpriseTalent(
            **payload.model_dump(exclude={"skills", "project_highlights"}),
            skills=_clean_list(payload.skills),
            project_highlights=_clean_list(payload.project_highlights),
            created_by=user_id,
        )
        self.db.add(row)
        directory_row = await self.db.scalar(select(EnterpriseEmployeeDirectory).where(
            EnterpriseEmployeeDirectory.employee_no == payload.employee_no
        ))
        if directory_row is None:
            self.db.add(EnterpriseEmployeeDirectory(
                **payload.model_dump(exclude={"skills", "project_highlights"}),
                skills=_clean_list(payload.skills),
                project_highlights=_clean_list(payload.project_highlights),
                source="manual_talent_entry",
                synced_by=user_id,
            ))
        await self.db.commit()
        await self.db.refresh(row)
        return self.talent_summary(row)

    async def create_talent_from_directory(
        self, employee_id: int, *, user_id: int
    ) -> EnterpriseTalentSummary:
        employee = await self.db.get(EnterpriseEmployeeDirectory, employee_id)
        if employee is None or employee.status != "active":
            raise ResourceNotFoundError("企业员工目录中不存在该员工")
        exists = await self.db.scalar(select(EnterpriseTalent.id).where(
            EnterpriseTalent.employee_no == employee.employee_no
        ))
        if exists is not None:
            raise InvalidParameterError("该员工已在企业人才池中")
        row = EnterpriseTalent(
            employee_no=employee.employee_no,
            name=employee.name,
            department=employee.department,
            current_position=employee.current_position,
            level=employee.level,
            location=employee.location,
            tenure_months=employee.tenure_months,
            position_tenure_months=employee.position_tenure_months,
            skills=employee.skills or [],
            project_highlights=employee.project_highlights or [],
            status="active",
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self.talent_summary(row)

    async def list_positions(self) -> list[InternalPositionSummary]:
        rows = list((await self.db.execute(
            select(InternalPosition).order_by(InternalPosition.updated_at.desc(), InternalPosition.id.desc())
        )).scalars())
        return [self.position_summary(row) for row in rows]

    async def create_position(self, payload: InternalPositionCreate, *, user_id: int) -> InternalPositionSummary:
        if payload.status != InternalPositionStatus.draft:
            raise InvalidParameterError("内部岗位必须先保存为草稿并经过审批")
        values = payload.model_dump()
        values["status"] = InternalPositionStatus.draft.value
        for field in (
            "responsibilities", "requirements", "required_skills", "trainable_skills",
            "transfer_profile", "manager_confirmations", "allowed_departments", "restrictions",
        ):
            values[field] = _clean_list(values[field])
        row = InternalPosition(**values, created_by=user_id)
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self.position_summary(row)

    async def update_position_status(self, position_id: int, status: InternalPositionStatus) -> InternalPositionSummary:
        row = await self.db.get(InternalPosition, position_id)
        if row is None:
            raise ResourceNotFoundError("内部岗位不存在")
        if status.value not in self.POSITION_TRANSITIONS.get(row.status, set()):
            raise InvalidParameterError(f"内部岗位不能从 {row.status} 直接变更为 {status.value}")
        row.status = status.value
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        return self.position_summary(row)

    async def list_rule_sets(self) -> list[TransferRuleSetSummary]:
        rows = list((await self.db.execute(
            select(TransferRuleSet).order_by(TransferRuleSet.status.asc(), TransferRuleSet.id.desc())
        )).scalars())
        return [self.rule_summary(row) for row in rows]

    async def create_rule_set(self, payload: TransferRuleSetCreate, *, user_id: int) -> TransferRuleSetSummary:
        if payload.status == "active":
            active_rows = list((await self.db.execute(
                select(TransferRuleSet).where(TransferRuleSet.status == "active")
            )).scalars())
            for active in active_rows:
                active.status = "inactive"
        max_version = await self.db.scalar(
            select(func.max(TransferRuleSet.version)).where(TransferRuleSet.name == payload.name)
        )
        row = TransferRuleSet(
            **payload.model_dump(),
            version=int(max_version or 0) + 1,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self.rule_summary(row)

    async def list_skill_demands(self) -> list[SkillDemandSummary]:
        positions = list((await self.db.execute(
            select(InternalPosition).where(InternalPosition.status.in_(("pending_approval", "open", "paused")))
        )).scalars())
        talents = list((await self.db.execute(
            select(EnterpriseTalent).where(EnterpriseTalent.status == "active")
        )).scalars())
        talent_keys = [{_skill_key(skill) for skill in (talent.skills or [])} for talent in talents]
        demand: dict[tuple[str, str], dict] = {}
        for position in positions:
            for kind, skills in (("required", position.required_skills or []), ("trainable", position.trainable_skills or [])):
                for skill in skills:
                    key = (_skill_key(skill), kind)
                    item = demand.setdefault(key, {
                        "skill": skill,
                        "positions": set(),
                        "headcount": 0,
                        "departments": set(),
                    })
                    item["positions"].add(position.id)
                    item["headcount"] += position.headcount
                    item["departments"].add(position.department)
        result = []
        for (key, kind), item in demand.items():
            supply = sum(1 for skills in talent_keys if key in skills)
            result.append(SkillDemandSummary(
                skill=item["skill"],
                position_count=len(item["positions"]),
                demand_headcount=item["headcount"],
                talent_supply=supply,
                gap=max(0, item["headcount"] - supply),
                departments=sorted(item["departments"]),
                requirement_type=kind,
            ))
        return sorted(result, key=lambda item: (-item.gap, -item.demand_headcount, item.skill))

    async def match_by_talent(
        self, talent_id: int, *, position_ids: list[int], rule_set_id: int | None
    ) -> list[InternalMatchResult]:
        talent = await self.db.get(EnterpriseTalent, talent_id)
        if talent is None:
            raise ResourceNotFoundError("企业人才不存在")
        statement = select(InternalPosition).where(InternalPosition.status == "open")
        if position_ids:
            statement = statement.where(InternalPosition.id.in_(position_ids))
        positions = list((await self.db.execute(statement)).scalars())
        rule = await self._resolve_rule(rule_set_id)
        return sorted(
            [self._match(talent, position, rule) for position in positions],
            key=lambda item: (not item.eligible, -item.score, item.position_id),
        )

    async def match_by_position(
        self, position_id: int, *, talent_ids: list[int], rule_set_id: int | None
    ) -> list[InternalMatchResult]:
        position = await self.db.get(InternalPosition, position_id)
        if position is None or position.status != "open":
            raise ResourceNotFoundError("内部开放岗位不存在")
        statement = select(EnterpriseTalent).where(EnterpriseTalent.status == "active")
        if talent_ids:
            statement = statement.where(EnterpriseTalent.id.in_(talent_ids))
        talents = list((await self.db.execute(statement)).scalars())
        rule = await self._resolve_rule(rule_set_id)
        return sorted(
            [self._match(talent, position, rule) for talent in talents],
            key=lambda item: (not item.eligible, -item.score, item.talent_id),
        )

    async def create_decision(self, payload: TransferDecisionCreate, *, user_id: int) -> TransferDecisionSummary:
        talent = await self.db.get(EnterpriseTalent, payload.talent_id, with_for_update=True)
        position = await self.db.get(InternalPosition, payload.position_id, with_for_update=True)
        if talent is None or position is None:
            raise ResourceNotFoundError("企业人才或内部岗位不存在")
        if talent.status != "active":
            raise InvalidParameterError("该员工当前不能参与转岗")
        if position.status != "open":
            raise InvalidParameterError("只能对内部开放岗位确认转岗")
        rule = await self._resolve_rule(payload.rule_set_id)
        if rule["id"] is None:
            raise InvalidParameterError("请先发布一套生效的转岗规则")
        match = self._match(talent, position, rule)
        if not match.eligible:
            raise InvalidParameterError("该人岗组合未通过硬性转岗规则")
        if match.score < rule["min_match_score"]:
            raise InvalidParameterError("该人岗组合未达到转岗匹配阈值")
        existing_talent_decision = await self.db.scalar(select(TransferDecision.id).where(
            TransferDecision.talent_id == talent.id,
            TransferDecision.status == "confirmed",
        ))
        if existing_talent_decision is not None:
            raise InvalidParameterError("该员工已经存在已确认的转岗决定")
        confirmed_count = await self.db.scalar(select(func.count(TransferDecision.id)).where(
            TransferDecision.position_id == position.id,
            TransferDecision.status == "confirmed",
        ))
        if int(confirmed_count or 0) >= position.headcount:
            raise InvalidParameterError("该内部岗位的确认名额已满")
        row = TransferDecision(
            talent_id=talent.id,
            position_id=position.id,
            match_score=match.score,
            matched_skills=match.matched_skills,
            missing_skills=match.missing_skills,
            rule_snapshot=rule,
            status="confirmed",
            note=payload.note,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self._decision_summary(row, talent, position)

    async def list_decisions(self) -> list[TransferDecisionSummary]:
        rows = list((await self.db.execute(
            select(TransferDecision).order_by(TransferDecision.created_at.desc(), TransferDecision.id.desc())
        )).scalars())
        result = []
        for row in rows:
            talent = await self.db.get(EnterpriseTalent, row.talent_id)
            position = await self.db.get(InternalPosition, row.position_id)
            if talent and position:
                result.append(self._decision_summary(row, talent, position))
        return result

    async def _resolve_rule(self, rule_set_id: int | None) -> dict:
        row = await self.db.get(TransferRuleSet, rule_set_id) if rule_set_id else None
        if row is None and rule_set_id is not None:
            raise ResourceNotFoundError("转岗规则不存在")
        if row is not None and row.status != "active":
            raise InvalidParameterError("只能使用当前生效的转岗规则")
        if row is None:
            row = await self.db.scalar(
                select(TransferRuleSet).where(TransferRuleSet.status == "active").order_by(TransferRuleSet.id.desc())
            )
        if row is None:
            return {
                "id": None,
                "version": 1,
                "name": "系统默认规则",
                "min_tenure_months": 0,
                "min_position_tenure_months": 0,
                "min_match_score": 60,
                "skill_weight": 85,
                "tenure_weight": 15,
            }
        return {
            "id": row.id,
            "version": row.version,
            "name": row.name,
            "min_tenure_months": row.min_tenure_months,
            "min_position_tenure_months": row.min_position_tenure_months,
            "min_match_score": row.min_match_score,
            "skill_weight": row.skill_weight,
            "tenure_weight": row.tenure_weight,
        }

    @staticmethod
    def _match(talent: EnterpriseTalent, position: InternalPosition, rule: dict) -> InternalMatchResult:
        talent_by_key = {_skill_key(item): item for item in (talent.skills or [])}
        required_by_key = {_skill_key(item): item for item in (position.required_skills or [])}
        matched_keys = set(talent_by_key) & set(required_by_key)
        matched = [required_by_key[key] for key in required_by_key if key in matched_keys]
        missing = [required_by_key[key] for key in required_by_key if key not in matched_keys]
        trainable_keys = {_skill_key(item): item for item in (position.trainable_skills or [])}
        trainable_gaps = [value for key, value in trainable_keys.items() if key not in talent_by_key]
        coverage = len(matched) / len(required_by_key) if required_by_key else 0.0
        required_tenure = max(position.min_tenure_months, rule["min_tenure_months"])
        required_position_tenure = max(position.min_position_tenure_months, rule["min_position_tenure_months"])
        disqualifications = []
        if not required_by_key:
            disqualifications.append("内部岗位尚未配置必备技能")
        if talent.tenure_months < required_tenure:
            disqualifications.append(f"司龄不足 {required_tenure} 个月")
        if talent.position_tenure_months < required_position_tenure:
            disqualifications.append(f"当前岗位任职不足 {required_position_tenure} 个月")
        allowed = {item.casefold() for item in (position.allowed_departments or [])}
        if allowed and talent.department.casefold() not in allowed:
            disqualifications.append("当前部门不在内部开放范围")
        if talent.status != "active":
            disqualifications.append("人才档案当前不可参与转岗")
        today = date.today()
        if position.open_from and today < position.open_from:
            disqualifications.append("内部岗位尚未到开放时间")
        if position.open_until and today > position.open_until:
            disqualifications.append("内部岗位开放时间已结束")
        tenure_ratio = 1.0 if required_tenure == 0 else min(1.0, talent.tenure_months / required_tenure)
        score = round(coverage * rule["skill_weight"] + tenure_ratio * rule["tenure_weight"])
        return InternalMatchResult(
            talent_id=talent.id,
            employee_no=talent.employee_no,
            talent_name=talent.name,
            current_department=talent.department,
            current_position=talent.current_position,
            position_id=position.id,
            position_title=position.title,
            target_department=position.department,
            eligible=not disqualifications,
            disqualifications=disqualifications,
            score=max(0, min(100, score)),
            matched_skills=matched,
            missing_skills=missing,
            trainable_gaps=trainable_gaps,
            estimated_development_weeks=min(52, max(1, len(missing) * 2 + len(trainable_gaps))),
            rule_set_id=rule["id"],
            rule_version=rule["version"],
        )

    @staticmethod
    def _decision_summary(
        row: TransferDecision, talent: EnterpriseTalent, position: InternalPosition
    ) -> TransferDecisionSummary:
        return TransferDecisionSummary(
            id=row.id,
            talent_id=row.talent_id,
            talent_name=talent.name,
            position_id=row.position_id,
            position_title=position.title,
            match_score=row.match_score,
            matched_skills=row.matched_skills or [],
            missing_skills=row.missing_skills or [],
            status=row.status,
            note=row.note,
            created_at=row.created_at,
        )
