from __future__ import annotations
import logging
from models.schemas import BioAgentState, DisclosureResult, DisclosureRiskLevel

logger = logging.getLogger(__name__)

HIGH_RISK_KEYWORDS = {"관리종목", "계속기업 불확실성", "감사의견 한정", "최대주주 변경"}
MEDIUM_RISK_KEYWORDS = {"유상증자 반복", "소송 계류"}


class DisclosureAgent:
    """공시 리스크 문구 분석 → LOW / MEDIUM / HIGH 판정."""

    def run(self, state: BioAgentState) -> BioAgentState:
        keywords = state.company_data.disclosure_data.risk_keywords
        company_name = state.company_data.company_name

        detected: list[str] = []
        has_high = False
        has_medium = False

        for kw in keywords:
            if kw in HIGH_RISK_KEYWORDS:
                detected.append(kw)
                has_high = True
            elif kw in MEDIUM_RISK_KEYWORDS:
                detected.append(kw)
                has_medium = True
            else:
                detected.append(kw)

        if has_high:
            risk_level = DisclosureRiskLevel.HIGH
        elif has_medium:
            risk_level = DisclosureRiskLevel.MEDIUM
        elif detected:
            risk_level = DisclosureRiskLevel.MEDIUM
        else:
            risk_level = DisclosureRiskLevel.LOW

        state.disclosure_result = DisclosureResult(
            disclosure_risk_level=risk_level,
            detected_keywords=detected,
        )
        logger.info(
            "[DisclosureAgent] %s | risk=%s | keywords=%s",
            company_name, risk_level, detected,
        )
        return state
