import sys; sys.stdout.reconfigure(encoding='utf-8')
import os
from pprint import pprint

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.bio_domain_agent import BioDomainAgent
import agents.bio_domain_agent as bda

# --- Mocking Gemini Client ---
class MockGeminiClient:
    def is_available(self):
        return True
    def generate(self, prompt):
        print("====== [Gemini LLM 프롬프트 전달 내용 확인] ======\n" + prompt + "\n==================================================")
        return "테스트바이오의 주요 파이프라인은 현재 임상 2상 진행 중이며, ClinicalTrials.gov에 등재되어 글로벌 투명성을 확보하고 있습니다. 더불어 FDA 희귀의약품 지정(ODD) 트랙을 준비 중이므로 글로벌 규제 기관 진출 가능성이 긍정적이나, 핵심 파이프라인 의존도가 55%로 다소 높은 점은 유의할 리스크입니다."

# Inject the mock to simulate LLM execution perfectly
bda.get_gemini_client = lambda: MockGeminiClient()

# --- Mocking State and Models ---
class MockBioDomain:
    clinical_stage: str = "Phase 2"
    pipeline_count: int = 5
    has_tech_export: bool = True
    has_patent: bool = True
    core_pipeline_dependency: float = 0.55

class MockCompanyData:
    company_name: str = "테스트바이오(가상)"
    bio_domain: MockBioDomain = MockBioDomain()

class MockNewsResult:
    def __init__(self, negative_critical_event=False, negative_keywords=None):
        self.negative_critical_event = negative_critical_event
        self.negative_keywords = negative_keywords

class MockState:
    def __init__(self, news_result=None):
        self.company_data = MockCompanyData()
        self.news_result = news_result
        self.bio_domain_result = None

def run_tests():
    agent = BioDomainAgent()
    
    print("======================================================")
    print("▶ 시나리오 A: 정상/호재 케이스 (news_result 가 None인 경우)")
    print("======================================================")
    state_a = MockState(news_result=None)
    result_a = agent.run(state_a)
    
    res_a = result_a.bio_domain_result
    print(f"\n[시나리오 A 산출 결과]")
    print(f"최종 바이오 점수: {res_a.bio_score}")
    print(f"도출된 도메인 리스크: {res_a.domain_risks}")
    print("\n\n")
    
    print("======================================================")
    print("▶ 시나리오 B: 치명적 뉴스 페널티 케이스")
    print("======================================================")
    # negative_critical_event=True, negative_keywords에 리스크 단어 포함
    news_res = MockNewsResult(
        negative_critical_event=True, 
        negative_keywords=["임상", "실패", "거절"]
    )
    state_b = MockState(news_result=news_res)
    result_b = agent.run(state_b)
    
    res_b = result_b.bio_domain_result
    print(f"\n[시나리오 B 산출 결과]")
    print(f"최종 바이오 점수: {res_b.bio_score}")
    print(f"도출된 도메인 리스크: {res_b.domain_risks}")

if __name__ == "__main__":
    run_tests()
