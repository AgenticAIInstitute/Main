import sys; sys.stdout.reconfigure(encoding='utf-8')
import os
import logging
from pprint import pprint

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.schemas import FinancialData
from agents.planner_agent import planner_node
import services.dart_client as dart_module
import requests

# stdout?쇰줈 濡쒓렇媛 ??蹂댁씠?꾨줉 湲곕낯 濡쒓굅 ?명똿
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
            "message": "?뺤긽",
            "list": [
                {"account_nm": "?좊룞?먯궛", "thstrm_amount": "50000000000"}, # 500??
                {"account_nm": "?좊룞遺梨?, "thstrm_amount": "25000000000"}, # 250??
                {"account_nm": "遺梨꾩킑怨?, "thstrm_amount": "30000000000"}, # 300??
                {"account_nm": "?먮낯珥앷퀎", "thstrm_amount": "70000000000"}, # 700??
                {"account_nm": "留ㅼ텧??, "thstrm_amount": "100000000000"}, # 1000??
                {"account_nm": "?곸뾽?댁씡", "thstrm_amount": "15000000000"}  # 150??
            ]
        })
    raise Exception("Unknown URL")

def mock_requests_get_fail(url, params=None):
    raise Exception("Connection Timeout (媛??湲덉쑖媛먮룆???쒕쾭 ?μ븷)")

# CompanyData 援ъ“ 紐⑤갑
class MockCompanyData:
    def __init__(self, ticker_code="091990", financial=None):
        self.company_name = "??몃━?⑦뿬?ㅼ????뚯뒪??"
        self.ticker_code = ticker_code
        self.news = "OK"
        self.bio_domain = "OK"
        self.disclosure = "OK"
        self.financial = financial

def run_tests():
    print("======================================================")
    print("???쒕굹由ъ삤 A: ?뺤긽?곸씤 ?ㅼ떆媛?Open DART ?곕룞 耳?댁뒪")
    print("======================================================")

    dart_client = dart_module.get_dart_client()
    dart_client.api_key = "VALID_DART_API_KEY_MOCK"
    # 罹먯떆 ?뺤씤 濡쒖쭅 紐⑥쓽 (罹먯떆媛 ?대? 議댁옱?쒕떎怨?媛??
    dart_client.ticker_to_corp = {"091990": "00112233"}

    # Requests ?쇱씠釉뚮윭由?媛濡쒖콈湲?(?ㅽ듃?뚰겕 紐⑥쓽)
    original_get = requests.get
    requests.get = mock_requests_get_success

    # 湲곗〈???낅젰???섏씠釉뚮━??寃고빀?? 媛???곗씠??
    original_financial = FinancialData(
        current_ratio=1.0, debt_ratio=99.0, operating_cash_flow=-5.0,
        cash_assets=10.0, cash_runway_months=18.0, operating_profit_margin=-10.0, rd_expense_ratio=25.5
    )

    state_a = {
        "company_data": MockCompanyData(financial=original_financial),
        "restart_required": False
    }

    print("\n[?ㅽ뻾 濡쒓렇]")
    result_a = planner_node(state_a)

    print("\n[?쒕굹由ъ삤 A 寃利?寃곌낵]")
    res_fin = result_a["company_data"].financial
    print(f"1) ?좊룞鍮꾩쑉(DART ?ㅻ쾭?쇱씠??: {res_fin.current_ratio} (?뺤긽 ?곗텧: 500??250??= 2.0)")
    print(f"2) 遺梨꾨퉬??DART ?ㅻ쾭?쇱씠??: {res_fin.debt_ratio}% (?뺤긽 ?곗텧: 300??700??100 = 42.86%)")
    print(f"3) ?곸뾽?댁씡瑜?DART ?ㅻ쾭?쇱씠??: {res_fin.operating_profit_margin}% (?뺤긽 ?곗텧: 150??1000??100 = 15.0%)")
    print(f"4) R&D 鍮꾩쨷(?섏씠釉뚮━???밴퀎): {res_fin.rd_expense_ratio}% (湲곗〈 25.5% 蹂댁〈 ?깃났)")
    print(f"5) Cash Runway(?섏씠釉뚮━???밴퀎): {res_fin.cash_runway_months}媛쒖썡 (湲곗〈 18.0媛쒖썡 蹂댁〈 ?깃났)")


    print("\n======================================================")
    print("???쒕굹由ъ삤 B: DART API Key ?꾨씫 ?먮뒗 ?쒕쾭 ?μ븷(Fallback) 耳?댁뒪")
    print("======================================================")

    # ?쒕쾭 ?μ븷 紐⑥쓽
    requests.get = mock_requests_get_fail

    state_b = {
        "company_data": MockCompanyData(financial=original_financial),
        "restart_required": False
    }

    print("\n[?ㅽ뻾 濡쒓렇]")
    result_b = planner_node(state_b)

    print("\n[?쒕굹由ъ삤 B 寃利?寃곌낵]")
    res_fin_b = result_b["company_data"].financial
    print(f"1) ?쒖뒪??Crash 諛⑹뼱 諛??덉쇅 泥섎━: ?꾨즺 (TypeError ?놁씠 ?뺤긽 ?고쉶)")
    print(f"2) 湲곗〈 ?곗씠??蹂댁〈 ?щ?(Fallback): 遺梨꾨퉬??{res_fin_b.debt_ratio}% (?μ븷 ??湲곗〈 ?곗씠??99.0%媛 ?좎떎 ?놁씠 ?덉쟾?섍쾶 ?밴퀎??")

    # 蹂듦뎄
    requests.get = original_get

if __name__ == "__main__":
    run_tests()
