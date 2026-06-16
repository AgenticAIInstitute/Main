"""Report Writer Agent — 각 기업별 최종 보고서 생성.

개선사항:
  1. supervisory_result 필드 최신화 (original_grade, adjusted_grade, is_error)
  2. 재시작 이력 보고서 반영
  3. _build_report 인자를 딕셔너리로 통합
  4. LLM 프롬프트에 SupervisoryAgent 판단 근거 추가
  5. LLM 가용성 체크 중복 제거
"""
from __future__ import annotations

import logging
from models.schemas import (
    BioAgentState, CompanyReport, GradeEnum, DisclosureRiskLevel, FinalDecision
)
from services.openai_client import get_openai_client

logger = logging.getLogger(__name__)

DECISION_LABEL = {
    FinalDecision.APPROVED:          "승인",
    FinalDecision.REJECTED:          "부결",
    FinalDecision.HUMAN_IN_THE_LOOP: "Human-in-the-Loop (전문가 검토 필요)",
}


class ReportWriterAgent:
    """각 기업별 최종 보고서 생성. OpenAI 사용 가능 시 자연어 보고서 생성."""

    def run(self, state: BioAgentState) -> BioAgentState:
        company = state.company_data
        rsr     = state.risk_score_result
        svr     = state.supervisory_result
        ldr     = state.loan_decision_result
        nr      = state.news_result
        dr      = state.disclosure_result

        # ── 각 결과 추출 ──────────────────────────
        grade           = rsr.grade        if rsr else GradeEnum.E
        final_score     = rsr.final_score  if rsr else 0.0
        fin_score       = state.financial_result.financial_score if state.financial_result else 0.0
        risk_factors    = state.financial_result.risk_factors if state.financial_result else []
        bio_domain_score = (
            state.bio_domain_result.bio_domain_score
            if state.bio_domain_result
            else (rsr.score_breakdown.get("bio_domain_score", 0.0) if rsr else 0.0)
        )
        domain_risks    = state.bio_domain_result.domain_risks if state.bio_domain_result else []
        bio_summary     = state.bio_domain_result.summary if state.bio_domain_result else ""
        news_score      = nr.news_score    if nr  else None
        disc_level      = dr.disclosure_risk_level if dr else DisclosureRiskLevel.MEDIUM
        decision        = ldr.final_decision  if ldr else FinalDecision.REJECTED
        decision_reason = ldr.decision_reason if ldr else ""

        # ── SupervisoryResult 최신 필드 ───────────
        original_grade     = svr.original_grade if svr else None
        adjusted_grade     = svr.adjusted_grade if svr else None
        supervisory_reason = svr.special_case_reason if svr else ""
        is_error           = svr.is_error        if svr else False
        llm_called         = svr.llm_called      if svr else False

        # ── 재시작 이력 추출 ──────────────────────
        restart_history = [e for e in state.errors if "재시작" in e]

        # ── 보고서 데이터 딕셔너리 ────────────────
        report_data = {
            "name":               company.company_name,
            "grade":              grade,
            "final_score":        final_score,
            "fin_score":          fin_score,
            "risk_factors":       risk_factors,
            "news_score":         news_score,
            "bio_domain_score":   bio_domain_score,
            "domain_risks":       domain_risks,
            "bio_summary":        bio_summary,
            "disc_level":         disc_level,
            "original_grade":     original_grade,
            "adjusted_grade":     adjusted_grade,
            "supervisory_reason": supervisory_reason,
            "llm_called":         llm_called,
            "is_error":           is_error,
            "decision":           decision,
            "decision_reason":    decision_reason,
            "restart_history":    restart_history,
        }

        report_text = self._build_report(report_data)

        state.report = CompanyReport(
            company_id           = company.company_id,
            company_name         = company.company_name,
            grade                = grade,
            final_score          = final_score,
            financial_score      = round(fin_score, 2),
            news_score           = round(news_score, 2) if news_score is not None else None,
            bio_score            = round(bio_domain_score, 2),
            disclosure_risk_level= disc_level,
            special_case         = llm_called,
            special_case_reason  = supervisory_reason,
            final_decision       = decision,
            decision_reason      = decision_reason,
            report_text          = report_text,
            financial_risk_factors= risk_factors,
            news_positive_keywords= nr.positive_keywords if nr else [],
            news_negative_keywords= nr.negative_keywords if nr else [],
            news_negative_critical_event= nr.negative_critical_event if nr else False,
            news_keyword_score= nr.keyword_score if nr else None,
            news_keyword_hits= nr.keyword_hits if nr else 0,
            news_llm_score= nr.llm_score if nr else None,
            news_llm_summary= nr.llm_summary if nr else "",
            news_merge_weights= nr.merge_weights if nr else "",
            bio_domain_risks     = domain_risks,
            bio_domain_summary   = bio_summary,
            disclosure_detected_keywords= dr.detected_keywords if dr else [],
        )

        logger.info(
            "[ReportWriterAgent] %s | decision=%s | grade=%s | restart=%d건",
            company.company_name, decision, grade, len(restart_history),
        )
        return state

    def _build_report(self, data: dict) -> str:
        """보고서 생성 — OpenAI 가용 시 자연어, 불가 시 템플릿."""

        name               = data["name"]
        grade              = data["grade"]
        final_score        = data["final_score"]
        fin_score          = data["fin_score"]
        risk_factors       = data["risk_factors"]
        news_score         = data["news_score"]
        bio_domain_score   = data["bio_domain_score"]
        domain_risks       = data["domain_risks"]
        bio_summary        = data["bio_summary"]
        disc_level         = data["disc_level"]
        original_grade     = data["original_grade"]
        adjusted_grade     = data["adjusted_grade"]
        supervisory_reason = data["supervisory_reason"]
        llm_called         = data["llm_called"]
        is_error           = data["is_error"]
        decision           = data["decision"]
        decision_reason    = data["decision_reason"]
        restart_history    = data["restart_history"]

        news_str     = f"{news_score:.1f}점" if news_score is not None else "데이터 없음 (판단 불확실)"
        decision_str = DECISION_LABEL[decision]

        # 등급 조정 여부
        if original_grade and adjusted_grade and original_grade != adjusted_grade:
            grade_change_str = f"{original_grade} → {adjusted_grade} (조정됨)"
        else:
            grade_change_str = f"{grade.value} (조정 없음)"

        # 재시작 이력
        restart_str = (
            f"{len(restart_history)}회 재시작 발생\n" +
            "\n".join(f"  - {e}" for e in restart_history)
        ) if restart_history else "없음"

        # 오류 여부
        error_str = "LLM 판단 오류 발생 — 담당자 검토 필요" if is_error else "없음"

        # ── 템플릿 보고서 ─────────────────────────
        template = (
            f"■ {name} 여신심사 최종 보고서\n"
            f"{'=' * 50}\n"
            f"최초 산출 등급  : {original_grade or grade.value}등급\n"
            f"등급 조정       : {grade_change_str}\n"
            f"최종 점수       : {final_score:.2f}점\n"
            f"재무 점수       : {fin_score:.1f}점\n"
            f"재무 리스크     : {', '.join(risk_factors) if risk_factors else '없음'}\n"
            f"뉴스 점수       : {news_str}\n"
            f"바이오 점수     : {bio_domain_score:.1f}점\n"
            f"바이오 리스크   : {', '.join(domain_risks) if domain_risks else '없음'}\n"
            f"바이오 요약     : {bio_summary or '없음'}\n"
            f"공시 리스크     : {disc_level.value}\n"
            f"특이사항 검토   : {'있음' if llm_called else '없음'}\n"
            f"특이사항 사유   : {supervisory_reason or '해당 없음'}\n"
            f"재시작 이력     : {restart_str}\n"
            f"오류 여부       : {error_str}\n"
            f"최종 판단       : {decision_str}\n"
            f"판단 근거       : {decision_reason}\n"
        )

        # ── OpenAI 자연어 보고서 ──────────────────
        openai = get_openai_client()
        if not openai.is_available():
            return template

        prompt = (
            f"당신은 바이오 기업 여신 심사 보고서 작성 전문 AI입니다.\n"
            f"다음 심사 결과를 바탕으로 여신 심사 보고서를 자연스러운 한국어로 작성해 주세요.\n\n"
            f"기업명: {name}\n"
            f"최초 등급: {original_grade or grade.value}등급 → 최종 등급: {grade.value}등급\n"
            f"최종 점수: {final_score:.2f}점\n"
            f"재무 점수: {fin_score:.1f}점 | 뉴스 점수: {news_str} | 바이오 점수: {bio_domain_score:.1f}점\n"
            f"재무 리스크: {', '.join(risk_factors) if risk_factors else '없음'}\n"
            f"바이오 리스크: {', '.join(domain_risks) if domain_risks else '없음'}\n"
            f"바이오 요약: {bio_summary or '없음'}\n"
            f"공시 리스크: {disc_level.value}\n"
            f"등급 조정 사유: {supervisory_reason or '조정 없음'}\n"
            f"재시작 이력: {restart_str}\n"
            f"오류 여부: {error_str}\n"
            f"최종 판단: {decision_str}\n"
            f"판단 근거: {decision_reason}\n\n"
            f"위 내용을 포함해서 3~5문장의 전문적인 여신 심사 보고서 문단을 작성해 주세요. "
            f"마지막 문장에 최종 판단 결과를 명확히 포함하세요. "
            f"재시작 이력이나 오류가 있으면 신뢰도 한계를 명시하세요."
        )

        ai_text = openai.generate(prompt)
        if ai_text:
            return (
                f"■ {name} 여신심사 최종 보고서\n"
                f"{'=' * 50}\n"
                f"{ai_text}\n\n"
                f"[원본 데이터]\n{template}"
            )
        return template
