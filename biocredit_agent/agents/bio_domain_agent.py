from biocredit_agent.models.schemas import CompanyData, AgentResult

class BioDomainAgent:
    """
    임상 단계, 파이프라인 개수, 기술수출 여부, 특허 여부, 핵심 파이프라인 의존도를 분석하여 bio_score(0~100) 계산
    """
    def analyze(self, company: CompanyData, result: AgentResult) -> AgentResult:
        bio = company.bio_data
        score = 0
        risks = []
        
        stage = bio.get("clinical_stage", "").lower()
        if "approved" in stage or "nda" in stage:
            score += 40
        elif "phase 3" in stage:
            score += 30
        elif "phase 2" in stage:
            score += 20
        elif "phase 1" in stage:
            score += 10
        else:
            risks.append("초기 개발 단계 (임상 전/실패)")
            
        if "failed" in stage:
            score = 0
            risks.append("임상 실패 이력")

        if bio.get("pipeline_count", 0) >= 3:
            score += 20
        else:
            risks.append("단일/소수 파이프라인 의존")
            
        if bio.get("tech_export", False):
            score += 20
            
        if bio.get("has_patent", False):
            score += 10
            
        dep = bio.get("core_pipeline_dependency", 1.0)
        if dep <= 0.5:
            score += 10
        elif dep > 0.8:
            risks.append("핵심 파이프라인 극도 의존")
            
        result.bio_score = min(max(score, 0), 100)
        result.bio_risks = risks
        return result
