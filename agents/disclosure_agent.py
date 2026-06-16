from __future__ import annotations

import logging

from models.schemas import BioAgentState, DisclosureResult, DisclosureRiskLevel

logger = logging.getLogger(__name__)

HIGH_RISK_KEYWORDS = {
    "관리종목",
    "상장폐지",
    "거래정지",
    "감사의견 관련",
    "감사의견 한정",
    "감사의견 거절",
    "계속기업 불확실성",
    "횡령",
    "배임",
    "회생절차",
    "불성실공시",
    "영업정지",
}
MEDIUM_RISK_KEYWORDS = {
    "유상증자 반복",
    "최대주주 변경",
    "소송",
}


class DisclosureAgent:
    """Classify disclosure risk keywords into LOW / MEDIUM / HIGH."""

    def run(self, state: BioAgentState) -> BioAgentState:
        keywords = state.company_data.disclosure_data.risk_keywords
        company_name = state.company_data.company_name

        detected: list[str] = []
        has_high = False
        has_medium = False

        for keyword in keywords:
            if keyword in HIGH_RISK_KEYWORDS:
                has_high = True
            elif keyword in MEDIUM_RISK_KEYWORDS:
                has_medium = True
            if keyword not in detected:
                detected.append(keyword)

        if has_high:
            risk_level = DisclosureRiskLevel.HIGH
        elif has_medium or detected:
            risk_level = DisclosureRiskLevel.MEDIUM
        else:
            risk_level = DisclosureRiskLevel.LOW

        state.disclosure_result = DisclosureResult(
            disclosure_risk_level=risk_level,
            detected_keywords=detected,
        )
        logger.info(
            "[DisclosureAgent] %s | risk=%s | keywords=%s",
            company_name,
            risk_level,
            detected,
        )
        return state
