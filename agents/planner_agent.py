from __future__ import annotations
import logging
from models.schemas import BioAgentState

logger = logging.getLogger(__name__)


class PlannerAgent:
    """분석 대상 기업 목록과 필요한 데이터 항목을 정리한다."""

    REQUIRED_DATA_ITEMS: list[str] = [
        "financial_data",
        "news_data",
        "bio_domain_data",
        "disclosure_data",
    ]

    def run(self, state: BioAgentState) -> BioAgentState:
        company = state.company_data
        logger.info("[PlannerAgent] 기업 분석 시작: %s (%s)", company.company_name, company.company_id)

        missing: list[str] = []
        if company.news is None:
            missing.append("news_data")
        if not company.financial:
            missing.append("financial_data")
        if not company.bio_domain:
            missing.append("bio_domain_data")
        if not company.disclosure:
            missing.append("disclosure_data")

        if missing:
            logger.warning("[PlannerAgent] 누락 데이터: %s", missing)
            state.errors.append(f"PlannerAgent: 누락 데이터 항목 - {missing}")

        logger.info(
            "[PlannerAgent] 분석 계획 완료 | 필수항목=%s | 누락=%s",
            self.REQUIRED_DATA_ITEMS,
            missing,
        )
        return state
