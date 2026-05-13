from typing import List
from biocredit_agent.models.schemas import CompanyData
from biocredit_agent.data.mock_companies import MOCK_COMPANIES

class PlannerAgent:
    """
    분석 대상 기업 목록과 필요한 데이터 항목을 정리한다.
    """
    def plan(self) -> List[CompanyData]:
        print("[PlannerAgent] 대상 기업 목록 로딩 완료")
        return MOCK_COMPANIES
