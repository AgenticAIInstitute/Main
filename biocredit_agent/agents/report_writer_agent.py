from biocredit_agent.models.schemas import AgentResult
from biocredit_agent.services.gemini_client import gemini_client

class ReportWriterAgent:
    """
    각 기업별 최종 보고서 생성
    Gemini API를 사용하여 자연스러운 문장 생성 시도, 실패시 템플릿 반환
    """
    def analyze(self, result: AgentResult) -> AgentResult:
        template = f"""
기업명: {result.company_name}
최초 산출 등급: {result.grade} (총점 {result.final_score}점)
- 재무 점수: {result.financial_score}
- 뉴스 점수: {result.news_score if result.news_score is not None else '데이터 없음(판단 보류)'}
- 바이오 점수: {result.bio_score}
- 공시 리스크: {result.disclosure_risk_level}

특이사항 여부: {'있음' if result.special_case else '없음'}
특이사항 사유: {result.special_case_reason if result.special_case else '-'}

최종 판단: {result.final_decision}
최종 판단 근거: {result.decision_reason}
"""
        
        prompt = f"""
당신은 금융권의 시니어 바이오 심사역입니다. 
다음 분석 데이터를 바탕으로 자연스럽고 전문적인 '최종 심사 보고서'를 작성해주세요. 
반드시 아래의 항목들을 모두 포함해야 합니다.

<분석 데이터>
{template}

보고서는 마크다운 형식으로 보기 좋게 정리해주세요.
결론을 명확히 제시해주세요.
"""
        final_report = gemini_client.generate_text(prompt, fallback_text=template.strip())
        result.final_report = final_report
        return result
