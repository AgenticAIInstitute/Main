from __future__ import annotations
import logging
from typing import Any
from models.schemas import BioAgentState, CompanyData

logger = logging.getLogger(__name__)


class PlannerAgent:
    """분석 대상 기업 목록과 필요한 데이터 항목을 정리한다."""

    REQUIRED_DATA_ITEMS: list[str] = [
        "financial_data",
        "news_data",
        "bio_domain_data",
        "disclosure_data",
    ]

    def get_companies(self) -> list[CompanyData]:
        """분석 대상 기업 리스트를 반환한다 (Agent 1이 정의하고 관리)."""
        from data.mock_companies import MOCK_COMPANIES
        return MOCK_COMPANIES

    def get_companies_by_id(self) -> dict[str, CompanyData]:
        """분석 대상 기업 ID 매핑을 반환한다."""
        from data.mock_companies import COMPANIES_BY_ID
        return COMPANIES_BY_ID

    def run(self, state: BioAgentState) -> BioAgentState:
        company = state.company_data
        company_name = company.company_name
        ticker_code = company.ticker_code

        logger.info(
            "[PlannerAgent] 기업 분석 시작: %s (%s) [종목코드: %s | 분류: %s | 시총: %s억원]",
            company_name,
            company.company_id,
            ticker_code,
            company.industry_category,
            f"{company.market_cap:,.0f}" if company.market_cap else "미등록",
        )

        # 🌟 Open DART 실시간 재무 데이터 수집 및 연동 시도 (결측치 검사 전 실행)
        from services.dart_client import get_dart_client
        dart = get_dart_client()
        if ticker_code and dart.is_available():
            try:
                live_fin = dart.fetch_financials(ticker_code)
                if live_fin:
                    logger.info(
                        "[PlannerAgent] %s (%s) DART 실시간 재무 수집 성공: %s",
                        company_name,
                        ticker_code,
                        live_fin,
                    )
                    
                    # 1. 유동비율 계산 (유동자산 / 유동부채)
                    ca = live_fin.get("current_assets", 0.0)
                    cl = live_fin.get("current_liabilities", 0.0)
                    if cl > 0:
                        company.financial.current_ratio = round(ca / cl, 2)
                    
                    # 2. 부채비율 계산 (부채총계 / 자본총계 * 100)
                    tl = live_fin.get("total_liabilities", 0.0)
                    te = live_fin.get("total_equity", 0.0)
                    if te > 0:
                        company.financial.debt_ratio = round((tl / te) * 100.0, 2)

                    # 3. 영업이익률 계산 (영업이익 / 매출액 * 100)
                    oi = live_fin.get("operating_income", 0.0)
                    rev = live_fin.get("revenue", 0.0)
                    if rev > 0:
                        company.financial.operating_profit_margin = round((oi / rev) * 100.0, 2)
            except Exception as e:
                logger.warning("[PlannerAgent] DART 실시간 재무 수집 실패로 baseline 모의 데이터 유지: %s", e)

        # 이제 실제 채워진 데이터를 기준으로 결측치 검사 수행
        missing: list[str] = []
        if company.news is None:
            missing.append("news_data")
        if not company.financial:
            missing.append("financial_data")
        else:
            # 신규 재무 필드 체크
            if company.financial.operating_profit_margin is None:
                missing.append("operating_profit_margin")
            if company.financial.rd_expense_ratio is None:
                missing.append("rd_expense_ratio")

        if not company.bio_domain:
            missing.append("bio_domain_data")
        if not company.disclosure:
            missing.append("disclosure_data")

        if missing:
            logger.warning("[PlannerAgent] 누락 데이터 항목 감지: %s", missing)
            state.errors.append(f"PlannerAgent: 누락 데이터 항목 - {missing}")

        # 🌟 바이오 도메인 기반 맞춤형 분석 지시서(Directives) 동적 발행
        directives: list[str] = []
        if company.bio_domain:
            if company.bio_domain.clinical_stage in ["Phase 2", "Phase 3"]:
                directives.append(f"후기 임상({company.bio_domain.clinical_stage}) R&D 투자 버퍼 및 기술적 타당성 검증 계획 수립")
            if company.bio_domain.has_tech_export:
                directives.append("기술 수출(Tech Export) 이력에 따른 비재무 기술성 가점 심사 지시")
            if company.bio_domain.pipeline_count >= 5:
                directives.append(f"다중 파이프라인({company.bio_domain.pipeline_count}개) 보유에 따른 핵심 파이프라인 집중 위험 상쇄 평가")

        if directives:
            logger.info(
                "[PlannerAgent] 🌟 %s 맞춤형 여신 분석 지침 수립: %s",
                company.company_name,
                directives,
            )

        logger.info(
            "[PlannerAgent] 분석 계획 완료 | 필수항목=%s | 누락=%s",
            self.REQUIRED_DATA_ITEMS,
            missing,
        )
        return state
