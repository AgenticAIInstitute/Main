from __future__ import annotations
import logging
from models.schemas import BioAgentState, BioDomainResult
from services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

CLINICAL_STAGE_SCORE: dict[str, float] = {
    "Approved": 35.0,
    "NDA": 30.0,
    "Phase 3": 25.0,
    "Phase 2": 15.0,
    "Phase 1": 8.0,
    "Preclinical": 3.0,
}


class BioDomainAgent:
    """임상단계·파이프라인·기술수출·특허·핵심의존도 및 뉴스 이벤트 기반 바이오 도메인 점수 산출."""

    def run(self, state: BioAgentState) -> BioAgentState:
        bd = state.company_data.bio_domain
        company_name = state.company_data.company_name
        domain_risks: list[str] = []

        # 1. 임상 단계 (clinical_stage) - 35점 만점
        stage_score = CLINICAL_STAGE_SCORE.get(bd.clinical_stage, 5.0)

        # 2. 파이프라인 개수 (pipeline_count) - 20점 만점
        if bd.pipeline_count >= 7:
            pipeline_score = 20.0
        elif bd.pipeline_count >= 4:
            pipeline_score = 14.0
        elif bd.pipeline_count >= 2:
            pipeline_score = 8.0
        else:
            pipeline_score = 3.0
            domain_risks.append(f"파이프라인 부족 (보유 {bd.pipeline_count}개)")

        # 3. 기술수출 여부 (has_tech_export) - 20점 만점
        tech_export_score = 20.0 if bd.has_tech_export else 0.0

        # 4. 특허 여부 (has_patent) - 15점 만점
        patent_score = 15.0 if bd.has_patent else 0.0
        if not bd.has_patent:
            domain_risks.append("보유 핵심 특허 없음")

        # 5. 핵심 파이프라인 의존도 (core_pipeline_dependency) - 10점 만점
        dep = bd.core_pipeline_dependency
        if dep <= 0.40:
            dep_score = 10.0
        elif dep <= 0.60:
            dep_score = 6.0
        elif dep <= 0.75:
            dep_score = 3.0
        else:
            dep_score = 0.0
            domain_risks.append(f"핵심 파이프라인 높은 의존도 (의존도 {dep:.0%})")

        # 기본 바이오 점수 계산
        base_bio_score = stage_score + pipeline_score + tech_export_score + patent_score + dep_score

        # 🌟 뉴스 에이전트 분석 결과와의 상호 연동 (방어적 코드 설계 완료)
        has_clinical_penalty = False
        if state.news_result and getattr(state.news_result, "negative_critical_event", False):
            # negative_keywords가 None일 경우를 대비해 안전장치 'or []' 추가
            keywords_list = getattr(state.news_result, "negative_keywords", []) or []
            critical_news_keywords = ["실패", "거절", "제재", "해지"]
            
            if any(k in "".join(keywords_list) for k in critical_news_keywords):
                has_clinical_penalty = True
                base_bio_score -= 15.0  # 임상 실패/인허가 거절 감점 적용
                domain_risks.append("최신 뉴스 내 임상 실패/승인 거절 등 주요 리스크 확인")
                logger.info(
                    "[BioDomainAgent] %s | 임상 부정 뉴스 이벤트 감지로 바이오 점수 페널티 적용 (-15.0점)",
                    company_name
                )

        bio_score = max(0.0, min(100.0, base_bio_score))

        # Gemini LLM 바이오 도메인 분석 요약 (선택적 — API 가용 시만 실행)
        try:
            gemini = get_gemini_client()
            if gemini.is_available():
                prompt = (
                    f"코스닥 바이오 기업 '{company_name}'의 바이오 도메인 분석 결과입니다.\n"
                    f"- 바이오 점수: {bio_score:.1f}/100점\n"
                    f"- 임상 단계: {bd.clinical_stage}\n"
                    f"- 파이프라인 수: {bd.pipeline_count}개\n"
                    f"- 기술수출 여부: {'있음' if bd.has_tech_export else '없음'}\n"
                    f"- 핵심 특허 보유: {'있음' if bd.has_patent else '없음'}\n"
                    f"- 핵심 파이프라인 의존도: {bd.core_pipeline_dependency:.0%}\n"
                    f"- 도메인 리스크: {', '.join(domain_risks) if domain_risks else '없음'}\n\n"
                    f"위 데이터를 바탕으로 여신 심사관 대출 심사 참고용으로 "
                    f"이 기업의 바이오 기술 경쟁력과 상업화 리스크를 3~4문장으로 간결하게 한국어로 요약해주세요.\n"
                    f"단, 다음 2가지 지침을 반드시 반영하여 심사의 신뢰도를 높여주세요:\n"
                    f"1. 글로벌 투명성: LLM의 사전 지식을 바탕으로, 이 기업의 주력 파이프라인이 ClinicalTrials.gov 등 글로벌 임상 레지스트리 등재 여부나 주요 글로벌 학회 발표 이력이 있는지 가볍게 짚어줄 것.\n"
                    f"2. 규제 기관 트랙: 단순히 파이프라인 개수를 넘어, FDA(패스트트랙, 희귀의약품 등)나 EMA 같은 글로벌 규제 기관 심사 트랙 진입 가능성이 있는지(또는 국내용에 치중되어 있는지) 정성적인 코멘트를 포함할 것."
                )
                llm_summary = gemini.generate(prompt)
                if llm_summary:
                    # 요약 데이터가 넘어왔음을 로그로 증명
                    logger.info("[BioDomainAgent] %s | Gemini LLM 분석 완료", company_name)
        except Exception as e:
            logger.warning("[BioDomainAgent] Gemini 호출 실패 (무시): %s", e)

        state.bio_domain_result = BioDomainResult(
            bio_score=round(bio_score, 2),
            domain_risks=domain_risks,
        )

        logger.info(
            "[BioDomainAgent] %s | score=%.1f | risks=%s | 임상실패감점=%s",
            company_name, bio_score, domain_risks, has_clinical_penalty
        )
        return state