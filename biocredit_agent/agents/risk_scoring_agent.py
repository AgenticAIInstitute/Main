from biocredit_agent.models.schemas import AgentResult

class RiskScoringAgent:
    """
    financial_score 40%, bio_score 25%, news_score 25%, disclosure/market 보정 10%
    news_score가 None이면 기본 50점으로 계산
    A: 85+, B: 70+, C: 55+, D: 40+, E: <40
    """
    def analyze(self, result: AgentResult) -> AgentResult:
        n_score = result.news_score if result.news_score is not None else 50
        
        d_score = 100
        if result.disclosure_risk_level == "HIGH":
            d_score = 0
        elif result.disclosure_risk_level == "MEDIUM":
            d_score = 50
            
        final = (result.financial_score * 0.4) + (result.bio_score * 0.25) + (n_score * 0.25) + (d_score * 0.1)
        result.final_score = round(final, 1)
        
        if final >= 85:
            result.grade = "A"
        elif final >= 70:
            result.grade = "B"
        elif final >= 55:
            result.grade = "C"
        elif final >= 40:
            result.grade = "D"
        else:
            result.grade = "E"
            
        return result
