from __future__ import annotations
import logging
from models.schemas import BioAgentState, BioDomainResult

logger = logging.getLogger(__name__)

CLINICAL_STAGE_SCORE: dict[str, float] = {
    "Approved": 35.0,
    "NDA": 30.0,
    "Phase 3": 25.0,
    "Phase 2": 15.0,
    "Phase 1": 8.0,
    "Preclinical": 3.0,
}


class BioDomainAgent:
    """임상단계·파이프라인·기술수출·특허·핵심의존도 기반 바이오 도메인 점수 산출."""

    def run(self, state: BioAgentState) -> BioAgentState:
        bd = state.company_data.bio_domain
        company_name = state.company_data.company_name
        domain_risks: list[str] = []

        # 임상 단계
        stage_score = CLINICAL_STAGE_SCORE.get(bd.clinical_stage, 5.0)

        # 파이프라인 개수
        if bd.pipeline_count >= 7:
            pipeline_score = 20.0
        elif bd.pipeline_count >= 4:
            pipeline_score = 14.0
        elif bd.pipeline_count >= 2:
            pipeline_score = 8.0
        else:
            pipeline_score = 3.0
            domain_risks.append(f"파이프라인 부족 (보유 {bd.pipeline_count}개)")

        # 기술수출 여부
        tech_export_score = 20.0 if bd.has_tech_export else 0.0

        # 특허 여부
        patent_score = 15.0 if bd.has_patent else 0.0
        if not bd.has_patent:
            domain_risks.append("보유 특허 없음")

        # 핵심 파이프라인 의존도 (낮을수록 좋음)
        dep = bd.core_pipeline_dependency
        if dep <= 0.40:
            dep_score = 10.0
        elif dep <= 0.60:
            dep_score = 6.0
        elif dep <= 0.75:
            dep_score = 3.0
        else:
            dep_score = 0.0
            domain_risks.append(f"핵심 파이프라인 집중 위험 (의존도 {dep:.0%})")

        bio_score = stage_score + pipeline_score + tech_export_score + patent_score + dep_score
        bio_score = max(0.0, min(100.0, bio_score))

        state.bio_domain_result = BioDomainResult(
            bio_score=round(bio_score, 2),
            domain_risks=domain_risks,
        )
        logger.info(
            "[BioDomainAgent] %s | score=%.1f | risks=%s",
            company_name, bio_score, domain_risks,
        )
        return state
