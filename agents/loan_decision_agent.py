from __future__ import annotations
import logging
from models.schemas import (
    BioAgentState, LoanDecisionResult, FinalDecision, GradeEnum
)

logger = logging.getLogger(__name__)

DECISION_REASONS = {
    FinalDecision.APPROVED: "재무 건전성 및 바이오 도메인 경쟁력이 우수하여 여신 승인을 권고합니다.",
    FinalDecision.REJECTED: "재무 위험도가 높고 바이오 파이프라인 리스크가 심각하여 여신 부결을 권고합니다.",
    FinalDecision.HUMAN_IN_THE_LOOP: (
        "자동 심사 기준만으로 판단하기 어려운 특이사항이 존재하므로 "
        "여신 심사 전문가의 추가 검토가 필요합니다."
    ),
}


class LoanDecisionAgent:
    """최종 여신 판단: APPROVED / REJECTED / HUMAN_IN_THE_LOOP."""

    def run(self, state: BioAgentState) -> BioAgentState:
        company_name = state.company_data.company_name
        rsr = state.risk_score_result
        svr = state.supervisory_result

        grade = rsr.grade if rsr else GradeEnum.E
        special_case = svr.special_case if svr else False

        # 판단 규칙 (우선순위 순서)
        if special_case:
            decision = FinalDecision.HUMAN_IN_THE_LOOP
            reason = (
                f"감독 AI가 특이사항을 감지했습니다. {DECISION_REASONS[FinalDecision.HUMAN_IN_THE_LOOP]}"
            )
        elif grade == GradeEnum.C:
            decision = FinalDecision.HUMAN_IN_THE_LOOP
            reason = f"C등급은 경계 구간으로 자동 결정 불가합니다. {DECISION_REASONS[FinalDecision.HUMAN_IN_THE_LOOP]}"
        elif grade in (GradeEnum.A, GradeEnum.B):
            decision = FinalDecision.APPROVED
            reason = f"{grade.value}등급 기업 — {DECISION_REASONS[FinalDecision.APPROVED]}"
        else:
            decision = FinalDecision.REJECTED
            reason = f"{grade.value}등급 기업 — {DECISION_REASONS[FinalDecision.REJECTED]}"

        state.loan_decision_result = LoanDecisionResult(
            final_decision=decision,
            decision_reason=reason,
        )
        logger.info(
            "[LoanDecisionAgent] %s | grade=%s | special=%s | decision=%s",
            company_name, grade, special_case, decision,
        )
        return state
