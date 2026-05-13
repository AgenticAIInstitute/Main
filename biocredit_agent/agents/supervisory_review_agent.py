from biocredit_agent.models.schemas import AgentResult
from biocredit_agent.services.gemini_client import gemini_client

class SupervisoryReviewAgent:
    """
    RiskScoringAgent의 결과를 검토해서 특이사항이 있는지 판단한다.
    조건:
    a. financial_score <= 50 and news_score >= 75
    b. financial_score >= 75 and news_score is None
    c. 최대 점수 차이 35점 이상
    d. negative_critical_event == True
    e. missing_news == True and grade in ["A", "B"]
    f. disclosure_risk_level == "HIGH"
    """
    def analyze(self, result: AgentResult) -> AgentResult:
        reasons = []
        n_score = result.news_score if result.news_score is not None else -1
        
        # a
        if result.financial_score <= 50 and n_score >= 75:
            reasons.append("재무 상태는 저조하나 뉴스를 통한 긍정적 모멘텀이 존재함.")
            
        # b
        if result.financial_score >= 75 and result.missing_news:
            reasons.append("재무 건전성은 우수하나 최근 시장(뉴스) 데이터가 부재하여 검증이 필요함.")
            
        # c
        scores = [result.financial_score, result.bio_score]
        if n_score != -1:
            scores.append(n_score)
        if max(scores) - min(scores) >= 35:
            reasons.append("에이전트 간 평가 점수 편차가 매우 커(35점 이상) 다각적 검토가 요구됨.")
            
        # d
        if result.negative_critical_event:
            reasons.append("부정적 핵심 이슈(임상 실패, 소송, 감사 문제 등)가 발견됨.")
            
        # e
        if result.missing_news and result.grade in ["A", "B"]:
            reasons.append("최상위 등급(A/B)으로 산출되었으나, 시장 반응(뉴스) 데이터가 없어 불확실성이 존재함.")
            
        # f
        if result.disclosure_risk_level == "HIGH":
            reasons.append("공시 상 심각한 리스크(관리종목, 의견거절 등)가 존재함.")
            
        if len(reasons) > 0:
            result.special_case = True
            base_reason = " ".join(reasons)
            
            prompt = f"다음은 기업 대출 심사에서 발견된 특이사항입니다. 이를 자연스럽고 전문적인 금융 보고서 문장으로 1~2문장으로 요약해주세요.\n내용: {base_reason}"
            improved_reason = gemini_client.generate_text(prompt, fallback_text=base_reason)
            result.special_case_reason = improved_reason
        else:
            result.special_case = False
            
        return result
