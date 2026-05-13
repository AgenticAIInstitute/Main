from __future__ import annotations
import logging
from models.schemas import BioAgentState, NewsResult

logger = logging.getLogger(__name__)

POSITIVE_KEYWORDS = ["FDA 승인", "임상 성공", "기술수출", "특허 취득", "품목허가", "신속승인"]
NEGATIVE_KEYWORDS = ["임상 실패", "FDA 거절", "식약처 제재", "횡령", "상장폐지", "감사의견 거절", "임상 지연", "소송"]
CRITICAL_NEGATIVE_KEYWORDS = ["횡령", "상장폐지", "감사의견 거절"]


class NewsAgent:
    """뉴스 키워드 분석으로 news_score 산출. 뉴스 없으면 None(판단 불확실성)."""

    def run(self, state: BioAgentState) -> BioAgentState:
        news_list = state.company_data.news
        company_name = state.company_data.company_name

        if not news_list:
            state.news_result = NewsResult(
                news_score=None,
                positive_keywords=[],
                negative_keywords=[],
                negative_critical_event=False,
                missing_news=True,
            )
            logger.info("[NewsAgent] %s | 뉴스 데이터 없음 → missing_news=True", company_name)
            return state

        all_text = " ".join(item.title + " " + item.content for item in news_list)
        found_positive = [kw for kw in POSITIVE_KEYWORDS if kw in all_text]
        found_negative = [kw for kw in NEGATIVE_KEYWORDS if kw in all_text]
        critical_event = any(kw in all_text for kw in CRITICAL_NEGATIVE_KEYWORDS)

        base_score = 50.0
        score = base_score + len(found_positive) * 12.0 - len(found_negative) * 15.0
        if critical_event:
            score -= 20.0
        score = max(0.0, min(100.0, score))

        state.news_result = NewsResult(
            news_score=round(score, 2),
            positive_keywords=found_positive,
            negative_keywords=found_negative,
            negative_critical_event=critical_event,
            missing_news=False,
        )
        logger.info(
            "[NewsAgent] %s | score=%.1f | pos=%s | neg=%s | critical=%s",
            company_name, score, found_positive, found_negative, critical_event,
        )
        return state
