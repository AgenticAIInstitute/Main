from __future__ import annotations

import logging

from data.company_aliases import aliases_for_company
from models.schemas import BioAgentState, BioDomainResult
from services.clinical_trials_client import STAGE_RANK, ClinicalTrialSummary, get_clinical_trials_client
from services.patent_client import PatentSummary, get_patent_client

logger = logging.getLogger(__name__)

CLINICAL_STAGE_SCORE: dict[str, float] = {
    "Approved": 35.0,
    "NDA": 32.0,
    "Phase 3": 30.0,
    "Phase 2": 22.0,
    "Phase 1": 12.0,
    "Preclinical": 3.0,
}


class BioDomainAgent:
    """Score bio domain strength from clinical-trial registration and patent data."""

    def run(self, state: BioAgentState) -> BioAgentState:
        company = state.company_data
        company_name = company.company_name
        fallback = company.bio_domain
        domain_risks: list[str] = []
        aliases = aliases_for_company(company_name)

        clinical = get_clinical_trials_client().search_company(company_name, aliases=aliases)
        patent = get_patent_client().search_company(company_name, aliases=aliases)

        clinical_stage = self._clinical_stage(clinical, fallback.clinical_stage)
        trial_count = clinical.trial_count if clinical.source_available else fallback.pipeline_count
        has_patent = self._has_patent(patent, fallback.has_patent)

        stage_score = CLINICAL_STAGE_SCORE.get(clinical_stage, 3.0)
        trial_score = self._trial_score(trial_count)
        status_score = self._status_score(clinical)
        patent_score = self._patent_score(patent, has_patent)

        if not clinical.source_available:
            domain_risks.append("clinical_trial_source_unavailable")
        elif clinical.trial_count == 0:
            domain_risks.append("no_registered_clinical_trial")

        if clinical.source_available and clinical.stopped_count > 0:
            domain_risks.append(f"stopped_clinical_trials_detected:{clinical.stopped_count}")

        if not patent.source_available:
            domain_risks.append(patent.message or "patent_source_unavailable")
        elif patent.patent_count == 0:
            domain_risks.append("no_patent_record_found")

        bio_score = max(0.0, min(100.0, stage_score + trial_score + status_score + patent_score))
        summary = self._summary(clinical_stage, trial_count, clinical, patent, bio_score, aliases)

        state.bio_domain_result = BioDomainResult(
            bio_domain_score=round(bio_score, 2),
            domain_risks=domain_risks,
            summary=summary,
        )

        logger.info(
            "[BioDomainAgent] %s | score=%.1f | stage=%s | trials=%s | patent_count=%s | risks=%s",
            company_name,
            bio_score,
            clinical_stage,
            trial_count,
            patent.patent_count if patent.source_available else "N/A",
            domain_risks,
        )
        return state

    @staticmethod
    def _clinical_stage(clinical: ClinicalTrialSummary, fallback_stage: str) -> str:
        if clinical.source_available and clinical.trial_count > 0:
            return clinical.highest_stage
        if fallback_stage in STAGE_RANK:
            return fallback_stage
        return "Preclinical"

    @staticmethod
    def _has_patent(patent: PatentSummary, fallback_has_patent: bool) -> bool:
        if patent.source_available:
            return patent.patent_count > 0 or patent.registered_count > 0 or patent.applied_count > 0
        return fallback_has_patent

    @staticmethod
    def _trial_score(trial_count: int) -> float:
        if trial_count >= 7:
            return 20.0
        if trial_count >= 4:
            return 16.0
        if trial_count >= 2:
            return 12.0
        if trial_count == 1:
            return 6.0
        return 0.0

    @staticmethod
    def _status_score(clinical: ClinicalTrialSummary) -> float:
        if not clinical.source_available:
            return 0.0
        score = 0.0
        if clinical.active_count > 0:
            score += 10.0
        elif clinical.completed_count > 0:
            score += 8.0

        if clinical.stopped_count > 0:
            score -= 15.0
        return score

    @staticmethod
    def _patent_score(patent: PatentSummary, has_patent: bool) -> float:
        if patent.source_available:
            registered_score = BioDomainAgent._registered_patent_score(patent.registered_count)
            if registered_score > 0:
                return registered_score
            return BioDomainAgent._applied_patent_score(max(patent.applied_count, patent.patent_count))
        return 10.0 if has_patent else 0.0

    @staticmethod
    def _registered_patent_score(count: int) -> float:
        if count >= 11:
            return 25.0
        if count >= 6:
            return 20.0
        if count >= 3:
            return 15.0
        if count >= 1:
            return 10.0
        return 0.0

    @staticmethod
    def _applied_patent_score(count: int) -> float:
        if count >= 11:
            return 15.0
        if count >= 6:
            return 12.0
        if count >= 3:
            return 8.0
        if count >= 1:
            return 5.0
        return 0.0

    @staticmethod
    def _summary(
        stage: str,
        trial_count: int,
        clinical: ClinicalTrialSummary,
        patent: PatentSummary,
        score: float,
        aliases: list[str],
    ) -> str:
        clinical_source = (
            "ClinicalTrials.gov"
            if clinical.source_available and clinical.trial_count > 0
            else "대체 데이터"
        )
        patent_source = "KIPRISPlus" if patent.source_available else "대체 데이터 또는 특허 데이터 사용 불가"
        patent_count = str(patent.patent_count) if patent.source_available else "확인 불가"
        matched_terms = ", ".join(patent.matched_terms or []) or "없음"
        clinical_matched_terms = ", ".join(clinical.matched_terms or []) or "없음"
        searched_terms = ", ".join(aliases[:8]) or "없음"
        stage_label = BioDomainAgent._korean_stage(stage)
        return (
            f"바이오 도메인 점수는 {score:.1f}점입니다. "
            f"임상 데이터 출처는 {clinical_source}이며, 확인된 최고 임상 단계는 {stage_label}입니다. "
            f"임상시험은 총 {trial_count}건이고, 진행 중 {clinical.active_count}건, 완료 {clinical.completed_count}건, "
            f"중단 {clinical.stopped_count}건으로 집계되었습니다. "
            f"임상 검색에서 매칭된 용어는 {clinical_matched_terms}입니다. "
            f"특허 데이터 출처는 {patent_source}이며, 확인된 특허 기록은 {patent_count}건입니다. "
            f"특허 출원인 매칭 용어는 {matched_terms}입니다. "
            f"검색에 사용한 회사명/별칭은 {searched_terms}입니다."
        )

    @staticmethod
    def _korean_stage(stage: str) -> str:
        labels = {
            "Approved": "허가 완료",
            "NDA": "허가 신청 단계",
            "Phase 3": "임상 3상",
            "Phase 2": "임상 2상",
            "Phase 1": "임상 1상",
            "Preclinical": "전임상",
        }
        return labels.get(stage, stage)
