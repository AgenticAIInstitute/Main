from biocredit_agent.models.schemas import CompanyData, AgentResult

class FinancialAgent:
    """
    유동비율, 부채비율, 영업현금흐름, 현금성 자산, Cash Runway를 기반으로 재무 점수를 계산한다.
    0~100점 사이의 financial_score와 재무 위험 요인 리스트를 반환한다.
    """
    def analyze(self, company: CompanyData, result: AgentResult) -> AgentResult:
        fin = company.financials
        score = 0
        risks = []

        # Current Ratio (유동비율)
        if fin.get("current_ratio", 0) >= 1.5:
            score += 20
        elif fin.get("current_ratio", 0) >= 1.0:
            score += 10
        else:
            risks.append("낮은 유동비율")

        # Debt Ratio (부채비율)
        if fin.get("debt_ratio", 999) <= 100:
            score += 20
        elif fin.get("debt_ratio", 999) <= 200:
            score += 10
        else:
            risks.append("높은 부채비율")

        # Operating Cash Flow (영업현금흐름)
        if fin.get("operating_cash_flow", 0) > 0:
            score += 20
        elif fin.get("operating_cash_flow", 0) > -500:
            score += 10
        else:
            risks.append("심각한 영업현금흐름 적자")

        # Cash Runway (현금 소진 예상 기간)
        if fin.get("cash_runway_months", 0) >= 24:
            score += 40
        elif fin.get("cash_runway_months", 0) >= 12:
            score += 20
        else:
            risks.append("현금성 자산 고갈 위험 (런웨이 1년 미만)")

        result.financial_score = min(max(score, 0), 100)
        result.financial_risks = risks
        return result
