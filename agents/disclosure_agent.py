from __future__ import annotations
import logging
from models.schemas import BioAgentState, DisclosureResult, DisclosureRiskLevel
from services.dart_client import get_dart_client

logger = logging.getLogger(__name__)

HIGH_RISK_KEYWORDS = {"관리종목", "계속기업 불확실성", "감사의견 한정", "최대주주 변경"}
MEDIUM_RISK_KEYWORDS = {"유상증자 반복", "소송 계류"}


class DisclosureAgent:
    """공시 리스크 문구 분석 및 실시간 DART 공시 수집 → LOW / MEDIUM / HIGH 판정."""

    def run(self, state: BioAgentState) -> BioAgentState:
        company_name = state.company_data.company_name
        ticker_code = state.company_data.ticker_code

        detected: list[str] = []
        has_high = False
        has_medium = False

        # Open DART 실시간 공시 연동 시도
        dart = get_dart_client()
        live_disclosures = []
        if ticker_code and dart.is_available():
            try:
                live_disclosures = dart.fetch_disclosures(ticker_code)
                logger.info(
                    "[DisclosureAgent] %s (%s) 실시간 DART 공시 %d건 수집 성공",
                    company_name,
                    ticker_code,
                    len(live_disclosures),
                )
            except Exception as e:
                logger.warning("[DisclosureAgent] 실시간 DART 공시 수집 오류: %s", e)

        if live_disclosures:
            # 실시간 공시 제목 기반 위험 형태소 스캔
            high_kws = ["관리종목", "불성실공시", "의견한정", "의견부적정", "의견거절", "불확실성", "배임", "횡령", "부도", "회생", "상장폐지"]
            medium_kws = ["소송", "유상증자", "전환사채", "신주인수권부사채", "담보", "벌금", "제재", "과징금", "가압류"]

            for disc in live_disclosures:
                title = disc.get("report_nm", "")
                
                # 고위험 키워드 매칭
                for kw in high_kws:
                    if kw in title:
                        desc = f"DART 실시간 감지: {kw} 관련 공시 ({title})"
                        if desc not in detected:
                            detected.append(desc)
                        has_high = True

                # 중위험 키워드 매칭
                for kw in medium_kws:
                    if kw in title:
                        desc = f"DART 실시간 감지: {kw} 관련 공시 ({title})"
                        if desc not in detected:
                            detected.append(desc)
                        has_medium = True
        else:
            # 룰베이스 로컬 모의 데이터 폴백 적용
            keywords = state.company_data.disclosure.risk_keywords
            for kw in keywords:
                if kw in HIGH_RISK_KEYWORDS:
                    detected.append(kw)
                    has_high = True
                elif kw in MEDIUM_RISK_KEYWORDS:
                    detected.append(kw)
                    has_medium = True
                else:
                    detected.append(kw)

        # 리스크 종합 등급 판정
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
            "[DisclosureAgent] %s | risk=%s | 감지된 공시 키워드=%s",
            company_name,
            risk_level,
            detected,
        )
        return state

