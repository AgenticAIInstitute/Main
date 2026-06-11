import sys; sys.stdout.reconfigure(encoding='utf-8')
from pprint import pprint

# agents.financial_agent import
# But wait, it imports from models.schemas import BioAgentState, FinancialResult
# I need to mock these properly or let the actual models load.
# Since app/models are in the directory, I can just import them or mock if they are pydantic.
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.financial_agent import FinancialAgent

class MockBioDomain:
    clinical_stage: str = "Phase 2"

class MockFinancial:
    current_ratio: float = 1.8
    debt_ratio: float = 55.0
    operating_profit_margin: float = -25.0
    operating_cash_flow: float = -10.0
    cash_assets: float = 250.0
    rd_expense_ratio: float = 22.5
    cash_runway_months: float = 15

class MockCompanyData:
    company_name: str = "적자바이오(가상)"
    financial: MockFinancial = MockFinancial()
    bio_domain: MockBioDomain = MockBioDomain()

class MockState:
    company_data: MockCompanyData = MockCompanyData()
    financial_result = None

def run_tests():
    print("======================================================")
    print("▶ 2번 Financial Agent 독립 시뮬레이션 테스트")
    print("======================================================")
    
    state = MockState()
    agent = FinancialAgent()
    
    print("[입력된 재무 데이터 검증]")
    fd = state.company_data.financial
    print(f"1. 유동비율: {fd.current_ratio} (배점: 20점)")
    print(f"2. 부채비율: {fd.debt_ratio}% (배점: 20점)")
    print(f"3. 영업이익률: {fd.operating_profit_margin}% (배점: 2점 + 리스크 추가 안됨(R&D 높아서))")
    print(f"4. 영업현금흐름: {fd.operating_cash_flow}억 (배점: 2점 + 리스크 추가)")
    print(f"5. 현금성 자산: {fd.cash_assets}억 (배점: 6점)")
    print(f"6. R&D 비용 비중: {fd.rd_expense_ratio}% (배점: 10점)")
    print(f"7. Cash Runway: {fd.cash_runway_months}개월 (배점: 3점)")
    print("------------------------------------------------------")
    print("=> Base Score 합산 예상치: 20 + 20 + 2 + 2 + 6 + 10 + 3 = 63.0 점")
    print("=> Deficit-R&D Protection 가점 예상치: +5.0 점")
    print("=> 최종 예상 점수: 68.0 점\n")
    
    # Run Agent
    new_state = agent.run(state)
    
    print("[에이전트 산출 결과 (FinancialResult 객체)]")
    res = new_state.financial_result
    print(f"- 최종 점수(financial_score): {res.financial_score}")
    print("- 도출된 리스크 요인(risk_factors):")
    for r in res.risk_factors:
        print(f"  * {r}")

if __name__ == "__main__":
    run_tests()
