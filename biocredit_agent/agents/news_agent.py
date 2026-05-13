from biocredit_agent.models.schemas import CompanyData, AgentResult

class NewsAgent:
    """
    뉴스 데이터가 있으면 긍정/부정 키워드를 분석한다.
    데이터가 없으면 판단 불확실성으로 처리한다.
    """
    def __init__(self):
        self.positive_keywords = ["FDA 승인", "임상 성공", "기술수출", "특허 취득", "품목허가"]
        self.negative_keywords = ["임상 실패", "FDA 거절", "식약처 제재", "횡령", "상장폐지", "감사의견 거절", "임상 지연", "소송"]

    def analyze(self, company: CompanyData, result: AgentResult) -> AgentResult:
        if company.news is None or len(company.news) == 0:
            result.news_score = None
            result.missing_news = True
            return result
        
        score = 50
        found_pos = []
        found_neg = []
        
        for article in company.news:
            for kw in self.positive_keywords:
                if kw in article:
                    score += 15
                    found_pos.append(kw)
            for kw in self.negative_keywords:
                if kw in article:
                    score -= 30
                    found_neg.append(kw)
        
        result.news_score = min(max(score, 0), 100)
        result.news_keywords = {"positive": list(set(found_pos)), "negative": list(set(found_neg))}
        result.missing_news = False
        
        if len(found_neg) > 0:
            result.negative_critical_event = True
            
        return result
