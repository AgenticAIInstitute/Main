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
    """임상단계·파이프라인·기술수출·특허·핵심의존도 및 뉴스 이벤트 기반 바이오 도메인 점수 산출."""

    def run(self, state: BioAgentState) -> BioAgentState:
        bd = state.company_data.bio_domain
        company_name = state.company_data.company_name
        domain_risks: list[str] = []

        # 1. 임상 단계 (clinical_stage) - 35점 만점
        stage_score = CLINICAL_STAGE_SCORE.get(bd.clinical_stage, 5.0)

        # 2. 파이프라인 개수 (pipeline_count) - 20점 만점
        if bd.pipeline_count >= 7:
            pipeline_score = 20.0
        elif bd.pipeline_count >= 4:
            pipeline_score = 14.0
        elif bd.pipeline_count >= 2:
            pipeline_score = 8.0
        else:
            pipeline_score = 3.0
            domain_risks.append(f"파이프라인 부족 (보유 {bd.pipeline_count}개)")

        # 3. 기술수출 여부 (has_tech_export) - 20점 만점
        tech_export_score = 20.0 if bd.has_tech_export else 0.0

        # 4. 특허 여부 (has_patent) - 15점 만점
        patent_score = 15.0 if bd.has_patent else 0.0
        if not bd.has_patent:
            domain_risks.append("보유 핵심 특허 없음")

        # 5. 핵심 파이프라인 의존도 (core_pipeline_dependency) - 10점 만점
        dep = bd.core_pipeline_dependency
        if dep <= 0.40:
            dep_score = 10.0
        elif dep <= 0.60:
            dep_score = 6.0
        elif dep <= 0.75:
            dep_score = 3.0
        else:
            dep_score = 0.0
            domain_risks.append(f"핵심 파이프라인 높은 의존도 (의존도 {dep:.0%})")

        # 기본 바이오 점수 계산
        base_bio_score = stage_score + pipeline_score + tech_export_score + patent_score + dep_score

        # 🌟 뉴스 에이전트 분석 결과와의 상호 연동 (Agentic Cross-Collaboration)
        # 만약 임상 실패, 승인 거절 등 뉴스 에이전트에서 치명적인 임상 부정 이벤트를 감지했다면 바이오 점수에서도 강력 감점
        has_clinical_penalty = False
        if state.news_result and state.news_result.negative_critical_event:
            # 부정 키워드 중 임상/인허가 실패 관련 단어 확인
            critical_news_keywords = ["실패", "거절", "제재", "해지"]
            if any(k in "".join(state.news_result.negative_keywords) for k in critical_news_keywords):
                has_clinical_penalty = True
                base_bio_score -= 15.0  # 임상 실패/인허가 거절 감점 적용
                domain_risks.append("최신 뉴스 내 임상 실패/승인 거절 등 주요 리스크 확인")
                logger.info(
                    "[BioDomainAgent] %s | 임상 부정 뉴스 이벤트 감지로 바이오 점수 페널티 적용 (-15.0점)",
                    company_name
                )

        bio_score = max(0.0, min(100.0, base_bio_score))

        state.bio_domain_result = BioDomainResult(
            bio_score=round(bio_score, 2),
            domain_risks=domain_risks,
        )

        logger.info(
            "[BioDomainAgent] %s | score=%.1f | risks=%s | 임상실패감점=%s",
            company_name, bio_score, domain_risks, has_clinical_penalty
        )
        return state
