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
    company_name: str = "?곸옄諛붿씠??媛??"
    financial: MockFinancial = MockFinancial()
    bio_domain: MockBioDomain = MockBioDomain()

class MockState:
    company_data: MockCompanyData = MockCompanyData()
    financial_result = None

def run_tests():
    print("======================================================")
    print("??2踰?Financial Agent ?낅┰ ?쒕??덉씠???뚯뒪??)
    print("======================================================")

    state = MockState()
    agent = FinancialAgent()

    print("[?낅젰???щТ ?곗씠??寃利?")
    fd = state.company_data.financial
    print(f"1. ?좊룞鍮꾩쑉: {fd.current_ratio} (諛곗젏: 20??")
    print(f"2. 遺梨꾨퉬?? {fd.debt_ratio}% (諛곗젏: 20??")
    print(f"3. ?곸뾽?댁씡瑜? {fd.operating_profit_margin}% (諛곗젏: 2??+ 由ъ뒪??異붽? ?덈맖(R&D ?믪븘??)")
    print(f"4. ?곸뾽?꾧툑?먮쫫: {fd.operating_cash_flow}??(諛곗젏: 2??+ 由ъ뒪??異붽?)")
    print(f"5. ?꾧툑???먯궛: {fd.cash_assets}??(諛곗젏: 6??")
    print(f"6. R&D 鍮꾩슜 鍮꾩쨷: {fd.rd_expense_ratio}% (諛곗젏: 10??")
    print(f"7. Cash Runway: {fd.cash_runway_months}媛쒖썡 (諛곗젏: 3??")
    print("------------------------------------------------------")
    print("=> Base Score ?⑹궛 ?덉긽移? 20 + 20 + 2 + 2 + 6 + 10 + 3 = 63.0 ??)
    print("=> Deficit-R&D Protection 媛???덉긽移? +5.0 ??)
    print("=> 理쒖쥌 ?덉긽 ?먯닔: 68.0 ??n")

    # Run Agent
    new_state = agent.run(state)

    print("[?먯씠?꾪듃 ?곗텧 寃곌낵 (FinancialResult 媛앹껜)]")
    res = new_state.financial_result
    print(f"- 理쒖쥌 ?먯닔(financial_score): {res.financial_score}")
    print("- ?꾩텧??由ъ뒪???붿씤(risk_factors):")
    for r in res.risk_factors:
        print(f"  * {r}")

if __name__ == "__main__":
    run_tests()
