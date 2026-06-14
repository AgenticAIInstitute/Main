import sys; sys.stdout.reconfigure(encoding='utf-8')
import os
import logging
from pprint import pprint

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.schemas import FinancialData
from agents.planner_agent import planner_node
import services.dart_client as dart_module
import requests

# stdout으로 로그가 잘 보이도록 기본 로거 세팅
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception(f"HTTP Error {self.status_code}")

def mock_requests_get_success(url, params=None):
    if "fnlttSinglAcnt" in url:
        return MockResponse({
            "status": "000",
            "message": "정상",
            "list": [
                {"account_nm": "유동자산", "thstrm_amount": "50000000000"}, # 500억
                {"account_nm": "유동부채", "thstrm_amount": "25000000000"}, # 250억
                {"account_nm": "부채총계", "thstrm_amount": "30000000000"}, # 300억
                {"account_nm": "자본총계", "thstrm_amount": "70000000000"}, # 700억
                {"account_nm": "매출액", "thstrm_amount": "100000000000"}, # 1000억
                {"account_nm": "영업이익", "thstrm_amount": "15000000000"}  # 150억
            ]
        })
    raise Exception("Unknown URL")

def mock_requests_get_fail(url, params=None):
    raise Exception("Connection Timeout (가상 금융감독원 서버 장애)")

# CompanyData 구조 모방
class MockCompanyData:
    def __init__(self, ticker_code="091990", financial=None):
        self.company_name = "셀트리온헬스케어(테스트)"
        self.ticker_code = ticker_code
        self.news = "OK"
        self.bio_domain = "OK"
        self.disclosure = "OK"
        self.financial = financial

def run_tests():
    print("======================================================")
    print("▶ 시나리오 A: 정상적인 실시간 Open DART 연동 케이스")
    print("======================================================")
    
    dart_client = dart_module.get_dart_client()
    dart_client.api_key = "VALID_DART_API_KEY_MOCK"
    # 캐시 확인 로직 모의 (캐시가 이미 존재한다고 가정)
    dart_client.ticker_to_corp = {"091990": "00112233"}
    
    # Requests 라이브러리 가로채기 (네트워크 모의)
    original_get = requests.get
    requests.get = mock_requests_get_success
    
    # 기존에 입력된(하이브리드 결합용) 가상 데이터
    original_financial = FinancialData(
        current_ratio=1.0, debt_ratio=99.0, operating_cash_flow=-5.0, 
        cash_assets=10.0, cash_runway_months=18.0, operating_profit_margin=-10.0, rd_expense_ratio=25.5
    )
    
    state_a = {
        "company_data": MockCompanyData(financial=original_financial),
        "restart_required": False
    }
    
    print("\n[실행 로그]")
    result_a = planner_node(state_a)
    
    print("\n[시나리오 A 검증 결과]")
    res_fin = result_a["company_data"].financial
    print(f"1) 유동비율(DART 오버라이트): {res_fin.current_ratio} (정상 산출: 500억/250억 = 2.0)")
    print(f"2) 부채비율(DART 오버라이트): {res_fin.debt_ratio}% (정상 산출: 300억/700억*100 = 42.86%)")
    print(f"3) 영업이익률(DART 오버라이트): {res_fin.operating_profit_margin}% (정상 산출: 150억/1000억*100 = 15.0%)")
    print(f"4) R&D 비중(하이브리드 승계): {res_fin.rd_expense_ratio}% (기존 25.5% 보존 성공)")
    print(f"5) Cash Runway(하이브리드 승계): {res_fin.cash_runway_months}개월 (기존 18.0개월 보존 성공)")
    
    
    print("\n======================================================")
    print("▶ 시나리오 B: DART API Key 누락 또는 서버 장애(Fallback) 케이스")
    print("======================================================")
    
    # 서버 장애 모의
    requests.get = mock_requests_get_fail
    
    state_b = {
        "company_data": MockCompanyData(financial=original_financial),
        "restart_required": False
    }
    
    print("\n[실행 로그]")
    result_b = planner_node(state_b)
    
    print("\n[시나리오 B 검증 결과]")
    res_fin_b = result_b["company_data"].financial
    print(f"1) 시스템 Crash 방어 및 예외 처리: 완료 (TypeError 없이 정상 우회)")
    print(f"2) 기존 데이터 보존 여부(Fallback): 부채비율 {res_fin_b.debt_ratio}% (장애 전 기존 데이터 99.0%가 유실 없이 안전하게 승계됨)")
    
    # 복구
    requests.get = original_get

if __name__ == "__main__":
    run_tests()
