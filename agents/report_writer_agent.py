from __future__ import annotations
import logging
from models.schemas import (
    BioAgentState, CompanyReport, GradeEnum, DisclosureRiskLevel, FinalDecision
)
from services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

DECISION_LABEL = {
    FinalDecision.APPROVED: "승인",
    FinalDecision.REJECTED: "부결",
    FinalDecision.HUMAN_IN_THE_LOOP: "Human-in-the-Loop (전문가 검토 필요)",
}


class ReportWriterAgent:
    """각 기업별 최종 보고서 생성. Gemini 사용 가능 시 자연어 보고서 생성."""

    def run(self, state: BioAgentState) -> BioAgentState:
        company = state.company_data
        rsr = state.risk_score_result
        svr = state.supervisory_result
        ldr = state.loan_decision_result
        nr = state.news_result
        dr = state.disclosure_result

        grade = rsr.grade if rsr else GradeEnum.E
        final_score = rsr.final_score if rsr else 0.0
        fin_score = rsr.score_breakdown.get("financial_score", 0.0) if rsr else 0.0
        news_score = nr.news_score if nr else None
        bio_score = rsr.score_breakdown.get("bio_score", 0.0) if rsr else 0.0
        disc_level = dr.disclosure_risk_level if dr else DisclosureRiskLevel.MEDIUM
        special_case = svr.special_case if svr else False
        special_reason = svr.special_case_reason if svr else ""
        decision = ldr.final_decision if ldr else FinalDecision.REJECTED
        decision_reason = ldr.decision_reason if ldr else ""

        report_text = self._build_report(
            company.company_name, grade, final_score, fin_score, news_score,
            bio_score, disc_level, special_case, special_reason, decision, decision_reason,
        )

        state.report = CompanyReport(
            company_id=company.company_id,
            company_name=company.company_name,
            grade=grade,
            final_score=final_score,
            financial_score=round(fin_score, 2),
            news_score=round(news_score, 2) if news_score is not None else None,
            bio_score=round(bio_score, 2),
            disclosure_risk_level=disc_level,
            special_case=special_case,
            special_case_reason=special_reason,
            final_decision=decision,
            decision_reason=decision_reason,
            report_text=report_text,
        )
        logger.info(
            "[ReportWriterAgent] %s | decision=%s | grade=%s",
            company.company_name, decision, grade,
        )
        return state

    def _build_report(
        self,
        name: str,
        grade: GradeEnum,
        score: float,
        fin: float,
        news: float | None,
        bio: float,
        disc: DisclosureRiskLevel,
        special: bool,
        special_reason: str,
        decision: FinalDecision,
        reason: str,
    ) -> str:
        gemini = get_gemini_client()

        news_str = f"{news:.1f}점" if news is not None else "데이터 없음(판단 불확실)"
        special_str = "있음" if special else "없음"
        decision_str = DECISION_LABEL[decision]

        template = (
            f"■ {name} 여신심사 최종 보고서\n"
            f"{'=' * 50}\n"
            f"최초 산출 등급  : {grade.value}등급\n"
            f"최종 점수       : {score:.2f}점\n"
            f"재무 점수       : {fin:.1f}점\n"
            f"뉴스 점수       : {news_str}\n"
            f"바이오 점수     : {bio:.1f}점\n"
            f"공시 리스크     : {disc.value}\n"
            f"특이사항        : {special_str}\n"
            f"특이사항 사유   : {special_reason or '해당 없음'}\n"
            f"최종 판단       : {decision_str}\n"
            f"판단 근거       : {reason}\n"
        )

        if not gemini.is_available():
            return template

        prompt = (
            f"당신은 바이오 기업 여신 심사 보고서 작성 전문 AI입니다.\n"
            f"다음 심사 결과를 바탕으로 여신 심사 보고서를 자연스러운 한국어로 작성해 주세요.\n\n"
            f"기업명: {name}\n"
            f"등급: {grade.value}등급 (최종 점수: {score:.2f}점)\n"
            f"재무 점수: {fin:.1f}점 | 뉴스 점수: {news_str} | 바이오 점수: {bio:.1f}점\n"
            f"공시 리스크: {disc.value}\n"
            f"특이사항: {special_str}\n"
            f"특이사항 사유: {special_reason or '해당 없음'}\n"
            f"최종 판단: {decision_str}\n"
            f"판단 근거: {reason}\n\n"
            f"위 내용을 포함해서 3~5문장의 전문적인 여신 심사 보고서 문단을 작성해 주세요. "
            f"마지막 문장에 최종 판단 결과를 명확히 포함하세요."
        )
        ai_text = gemini.generate(prompt)
        if ai_text:
            return f"■ {name} 여신심사 최종 보고서\n{'=' * 50}\n{ai_text}\n\n[원본 데이터]\n{template}"
        return template
