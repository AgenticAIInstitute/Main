import sys
import sys; sys.stdout.reconfigure(encoding='utf-8')
from pprint import pprint
from agents.planner_agent import planner_node

# 紐⑥쓽 湲곗뾽 ?곗씠???대옒??(?띿꽦 ?묎렐 諛⑹떇??紐⑤갑?섍린 ?꾪븿)
class MockCompanyData:
    def __init__(self, financial=None, news=None, bio_domain=None, disclosure=None):
        self.company_name = "?뚯뒪?몃컮?댁삤(媛??"
        self.financial = financial
        self.news = news
        self.bio_domain = bio_domain
        self.disclosure = disclosure

def run_tests():
    print("======================================================")
    print("???쒕굹由ъ삤 1: 理쒖큹 ?ㅽ뻾 ?곗씠???꾨씫 耳?댁뒪 (financial, news ?꾨씫)")
    print("======================================================")
    # financial怨?news媛 ?녿뒗 ?곹깭濡?紐⑥쓽 媛앹껜 ?앹꽦
    mock_company = MockCompanyData(financial=None, news=None, bio_domain="OK", disclosure="OK")
    state_case1 = {
        "company_data": mock_company,
        "restart_count": 0,
        "restart_required": False
    }
    result1 = planner_node(state_case1)
    print("諛섑솚??寃곌낵:")
    pprint(result1)

    print("\n======================================================")
    print("???쒕굹由ъ삤 2: ?ъ떆??耳?댁뒪 (restart_required=True)")
    print("======================================================")
    state_case2 = {
        "company_data": mock_company,  # ?ъ떆???쒖뿉???곗씠?곌? ?덈떎怨?媛??
        "restart_count": 3,            # 臾댄븳猷⑦봽 諛⑹? 移댁슫?몃뒗 ?좎??섏뼱????
        "restart_required": True,
        "financial_result": "OLD_DATA",
        "news_result": "OLD_DATA",
        "errors": ["?댁쟾 遺꾩꽍 ?④퀎?먯꽌???ㅻ쪟 硫붿떆吏"]
    }
    result2 = planner_node(state_case2)
    print("諛섑솚??寃곌낵 (State ?⑥튂):")
    pprint(result2)

if __name__ == "__main__":
    run_tests()
