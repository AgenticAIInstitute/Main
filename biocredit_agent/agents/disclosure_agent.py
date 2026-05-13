from biocredit_agent.models.schemas import CompanyData, AgentResult

class DisclosureAgent:
    """
    공시 리스크 문구를 분석하여 HIGH, MEDIUM, LOW 결정
    """
    def __init__(self):
        self.high_risk = ["관리종목", "계속기업 불확실성", "감사의견 한정", "감사의견 거절"]
        self.medium_risk = ["최대주주 변경", "유상증자 반복", "유상증자 결정"]

    def analyze(self, company: CompanyData, result: AgentResult) -> AgentResult:
        disclosures = company.disclosures
        level = "LOW"
        
        for d in disclosures:
            for hr in self.high_risk:
                if hr in d:
                    level = "HIGH"
                    result.negative_critical_event = True
                    break
            if level == "HIGH":
                break
                
            for mr in self.medium_risk:
                if mr in d:
                    level = "MEDIUM"
        
        result.disclosure_risk_level = level
        return result
