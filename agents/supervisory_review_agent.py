from __future__ import annotations
import logging
from models.schemas import BioAgentState, SupervisoryResult, DisclosureRiskLevel, GradeEnum
from services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class SupervisoryReviewAgent:
    """
    관리·감독 Agent.
    점수 간 모순·데이터 누락·판단 불확실성·치명적 리스크를 감지한다.
    """

    def run(self, state: BioAgentState) -> BioAgentState:
        company_name = state.company_data.company_name
        rsr = state.risk_score_result
        nr = state.news_result
        fr = state.financial_result
        dr = state.disclosure_result

        fin = fr.financial_score if fr else 0.0
        news = nr.news_score if nr else None
        bio = state.bio_domain_result.bio_score if state.bio_domain_result else 0.0
        grade = rsr.grade if rsr else GradeEnum.E
        missing_news = rsr.missing_news if rsr else True
        disc_level = dr.disclosure_risk_level if dr else DisclosureRiskLevel.MEDIUM
        critical_event = nr.negative_critical_event if nr else False

        flags: list[str] = []

        # a. 재무 낮 & 뉴스 좋음 → 데이터 간 모순
        if fin <= 50 and news is not None and news >= 75:
            flags.append("a: 재무점수 낮음(≤50)에도 뉴스점수 높음(≥75) — 점수 간 모순 감지")

        # b. 재무 높 & 뉴스 없음 → 판단 근거 불충분
        if fin >= 75 and news is None:
            flags.append("b: 재무점수 높음(≥75)이나 뉴스 데이터 부재 — 판단 불확실성")

        # c. 3개 점수 간 최대 편차 35점 이상
        available_scores = [s for s in [fin, news, bio] if s is not None]
        if len(available_scores) >= 2:
            max_diff = max(available_scores) - min(available_scores)
            if max_diff >= 35:
                flags.append(f"c: 점수 간 최대 편차 {max_diff:.1f}점 — 분석 지표 불일치")

        # d. 치명적 부정 이벤트
        if critical_event:
            flags.append("d: 치명적 부정 이벤트(횡령·상장폐지·감사거절) 감지")

        # e. 뉴스 없음 + A/B 등급 → 고등급 근거 불충분
        if missing_news and grade in (GradeEnum.A, GradeEnum.B):
            flags.append(f"e: 뉴스 데이터 없음에도 {grade.value}등급 산출 — 고등급 신뢰도 점검 필요")

        # f. 공시 리스크 HIGH
        if disc_level == DisclosureRiskLevel.HIGH:
            flags.append("f: 공시 리스크 HIGH — 관리종목·계속기업·감사의견 등 중대 리스크")

        special_case = len(flags) > 0

        base_reason = self._build_base_reason(company_name, flags, special_case)
        reason = self._enhance_with_gemini(company_name, base_reason, flags) if special_case else base_reason

        state.supervisory_result = SupervisoryResult(
            special_case=special_case,
            special_case_reason=reason,
            flags=flags,
        )
        logger.info(
            "[SupervisoryReviewAgent] %s | special=%s | flags=%d",
            company_name, special_case, len(flags),
        )
        return state

    def _build_base_reason(self, company_name: str, flags: list[str], special_case: bool) -> str:
        if not special_case:
            return f"{company_name}은(는) 특이사항 없이 정상 심사 기준에 부합합니다."
        reasons = "\n".join(f"  • {f}" for f in flags)
        return (
            f"{company_name} 심사 시 다음 특이사항이 감지되어 Human-in-the-Loop 검토가 필요합니다:\n"
            f"{reasons}"
        )

    def _enhance_with_gemini(self, company_name: str, base_reason: str, flags: list[str]) -> str:
        gemini = get_gemini_client()
        if not gemini.is_available():
            return base_reason

        flag_text = "\n".join(f"- {f}" for f in flags)
        prompt = (
            f"당신은 바이오 기업 여신 심사 전문 AI입니다.\n"
            f"다음은 '{company_name}' 기업에 대한 감독 AI의 특이사항 감지 결과입니다:\n\n"
            f"{flag_text}\n\n"
            f"위 내용을 바탕으로 여신 심사 담당자가 이해하기 쉬운 자연스러운 한국어 보고서 문장으로 "
            f"2~4문장으로 요약해 주세요. 전문적이고 간결하게 작성하세요."
        )
        result = gemini.generate(prompt)
        return result if result else base_reason
