from __future__ import annotations

import logging
import os

from models.schemas import BioDomainData, CompanyData, DisclosureData, FinancialData
from services.dart_client import get_dart_client
from services.market_client import MarketCompany, get_market_client

logger = logging.getLogger(__name__)


def load_companies(limit: int | None = None) -> list[CompanyData]:
    limit = limit or int(os.getenv("KOSDAQ_TOP_LIMIT", "50"))
    market_companies = get_market_client().get_kosdaq_bio_top_by_market_cap(limit=limit)
    companies = [_to_company_data(item) for item in market_companies]
    logger.info("[CompanyLoader] loaded %d KOSDAQ bio companies", len(companies))
    return companies


def build_companies_by_id(companies: list[CompanyData]) -> dict[str, CompanyData]:
    return {company.company_id: company for company in companies}


def _to_company_data(item: MarketCompany) -> CompanyData:
    market_cap_eok = item.market_cap_krw / 100_000_000
    financial = _default_financial_data()
    disclosure = DisclosureData(risk_keywords=[])

    dart_client = get_dart_client()
    if dart_client.available:
        dart_data = dart_client.get_company_data(item.ticker_code)
        if dart_data.financial:
            financial = dart_data.financial
        else:
            logger.warning(
                "[CompanyLoader] DART financial fallback used for %s(%s): %s",
                item.company_name,
                item.ticker_code,
                dart_data.financial_source,
            )
        disclosure = dart_data.disclosure

    return CompanyData(
        company_id=item.ticker_code,
        company_name=item.company_name,
        ticker_code=item.ticker_code,
        industry_category=_industry_category(item),
        market_cap=round(market_cap_eok, 2),
        financial=financial,
        news=None,
        bio_domain=_default_bio_domain_data(),
        disclosure=disclosure,
    )


def _industry_category(item: MarketCompany) -> str:
    if item.department:
        return f"{item.market} / {item.department}"
    return item.market or "KOSDAQ"


def _default_financial_data() -> FinancialData:
    # DART financial loading is the next integration point. These conservative defaults
    # keep the existing pipeline runnable while the company universe comes from KOSDAQ.
    return FinancialData(
        current_ratio=1.5,
        debt_ratio=70.0,
        operating_cash_flow=0.0,
        cash_assets=100.0,
        cash_runway_months=12.0,
        operating_profit_margin=0.0,
        rd_expense_ratio=10.0,
    )


def _default_bio_domain_data() -> BioDomainData:
    return BioDomainData(
        clinical_stage="Preclinical",
        pipeline_count=0,
        has_tech_export=False,
        has_patent=False,
        core_pipeline_dependency=1.0,
    )
