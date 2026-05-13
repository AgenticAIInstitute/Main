from biocredit_agent.models.schemas import AgentResult

class LoanDecisionAgent:
    """
    최종 판단 규칙:
    1) special_case == True -> "HUMAN_IN_THE_LOOP"
    2) grade == "C" -> "HUMAN_IN_THE_LOOP"
    3) grade in ["A", "B"] -> "APPROVED"
    4) grade in ["D", "E"] -> "REJECTED"
    """
    def analyze(self, result: AgentResult) -> AgentResult:
        if result.special_case:
            result.final_decision = "HUMAN_IN_THE_LOOP"
            result.decision_reason = "특이사항 감지로 인해 전문가 심층 심사 배정."
        elif result.grade == "C":
            result.final_decision = "HUMAN_IN_THE_LOOP"
            result.decision_reason = "C등급(경계선)으로 분류되어 전문가의 확인이 필요함."
        elif result.grade in ["A", "B"]:
            result.final_decision = "APPROVED"
            result.decision_reason = f"{result.grade}등급 획득 및 특이사항 없음. 시스템 자동 승인 처리."
        elif result.grade in ["D", "E"]:
            result.final_decision = "REJECTED"
            result.decision_reason = f"{result.grade}등급 획득으로 여신 가이드라인에 따라 부결 처리."
        else:
            result.final_decision = "HUMAN_IN_THE_LOOP"
            result.decision_reason = "알 수 없는 등급 산출 오류."
            
        return result
