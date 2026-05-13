from __future__ import annotations
import logging
from models.schemas import (
    BioAgentState, RiskScoreResult, GradeEnum, DisclosureRiskLevel
)

logger = logging.getLogger(__name__)

DISCLOSURE_SCORE_MAP = {
    DisclosureRiskLevel.LOW: 100.0,
    DisclosureRiskLevel.MEDIUM: 60.0,
    DisclosureRiskLevel.HIGH: 20.0,
}

WEIGHT_FINANCIAL = 0.40
WEIGHT_NEWS = 0.25
WEIGHT_BIO = 0.25
WEIGHT_DISCLOSURE = 0.10


def _grade(score: float) -> GradeEnum:
    if score >= 85:
        return GradeEnum.A
    if score >= 70:
        return GradeEnum.B
    if score >= 55:
        return GradeEnum.C
    if score >= 40:
        return GradeEnum.D
    return GradeEnum.E


class RiskScoringAgent:
    """
    가중 합산 최종 점수 및 A~E 등급 산출.
    news_score 없으면 중립 50점 임시 반영 + missing_news 플래그 설정.
    """

    def run(self, state: BioAgentState) -> BioAgentState:
        company_name = state.company_data.company_name

        fin_score = state.financial_result.financial_score if state.financial_result else 0.0
        bio_score = state.bio_domain_result.bio_score if state.bio_domain_result else 0.0
        disc_level = (
            state.disclosure_result.disclosure_risk_level
            if state.disclosure_result
            else DisclosureRiskLevel.MEDIUM
        )

        news_raw = state.news_result.news_score if state.news_result else None
        missing_news = state.news_result.missing_news if state.news_result else True
        news_effective = news_raw if news_raw is not None else 50.0

        disc_score = DISCLOSURE_SCORE_MAP[disc_level]

        final_score = (
            WEIGHT_FINANCIAL * fin_score
            + WEIGHT_NEWS * news_effective
            + WEIGHT_BIO * bio_score
            + WEIGHT_DISCLOSURE * disc_score
        )
        final_score = round(final_score, 2)
        grade = _grade(final_score)

        state.risk_score_result = RiskScoreResult(
            final_score=final_score,
            grade=grade,
            missing_news=missing_news,
            score_breakdown={
                "financial_score": fin_score,
                "news_score_effective": news_effective,
                "news_score_raw": news_raw,
                "bio_score": bio_score,
                "disclosure_score": disc_score,
                "weights": {
                    "financial": WEIGHT_FINANCIAL,
                    "news": WEIGHT_NEWS,
                    "bio": WEIGHT_BIO,
                    "disclosure": WEIGHT_DISCLOSURE,
                },
            },
        )
        logger.info(
            "[RiskScoringAgent] %s | final=%.2f | grade=%s | missing_news=%s",
            company_name, final_score, grade, missing_news,
        )
        return state
