import sys
import sys; sys.stdout.reconfigure(encoding='utf-8')
from pprint import pprint
from agents.planner_agent import planner_node

# 모의 기업 데이터 클래스 (속성 접근 방식을 모방하기 위함)
class MockCompanyData:
    def __init__(self, financial=None, news=None, bio_domain=None, disclosure=None):
        self.company_name = "테스트바이오(가상)"
        self.financial = financial
        self.news = news
        self.bio_domain = bio_domain
        self.disclosure = disclosure

def run_tests():
    print("======================================================")
    print("▶ 시나리오 1: 최초 실행 데이터 누락 케이스 (financial, news 누락)")
    print("======================================================")
    # financial과 news가 없는 상태로 모의 객체 생성
    mock_company = MockCompanyData(financial=None, news=None, bio_domain="OK", disclosure="OK")
    state_case1 = {
        "company_data": mock_company,
        "restart_count": 0,
        "restart_required": False
    }
    result1 = planner_node(state_case1)
    print("반환된 결과:")
    pprint(result1)
    
    print("\n======================================================")
    print("▶ 시나리오 2: 재시작 케이스 (restart_required=True)")
    print("======================================================")
    state_case2 = {
        "company_data": mock_company,  # 재시작 시에는 데이터가 있다고 가정
        "restart_count": 3,            # 무한루프 방지 카운트는 유지되어야 함
        "restart_required": True,
        "financial_result": "OLD_DATA",
        "news_result": "OLD_DATA",
        "errors": ["이전 분석 단계에서의 오류 메시지"]
    }
    result2 = planner_node(state_case2)
    print("반환된 결과 (State 패치):")
    pprint(result2)

if __name__ == "__main__":
    run_tests()
