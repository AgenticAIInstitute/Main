from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BIO_STRICT_INDUSTRIES = (
    "의약품 제조업",
    "기초 의약물질",
)

BIO_RESEARCH_INDUSTRIES = (
    "자연과학 및 공학 연구개발",
)

BIO_EXCLUDE_INDUSTRIES = (
    "의료용 기기",
    "의료기기",
    "의료용품",
    "소프트웨어",
    "도매업",
    "화학물질",
    "화학제품",
)

BIO_FORCE_INCLUDE_TICKERS = {
    "028300",  # HLB
    "067630",  # HLB생명과학
}

BIO_NAME_KEYWORDS = (
    "바이오",
    "제약",
    "테라퓨틱스",
    "파마",
    "생명과학",
)

BIO_PRODUCT_KEYWORDS = BIO_NAME_KEYWORDS + (
    "신약",
    "치료제",
    "항체",
    "단백질",
    "펩타이드",
    "세포치료",
    "유전자치료",
    "항암",
    "면역",
    "의약품",
)


@dataclass(frozen=True)
class MarketCompany:
    rank: int
    ticker_code: str
    company_name: str
    market: str
    department: str
    market_cap_krw: int


class MarketClient:
    def get_kosdaq_top_by_market_cap(self, limit: int = 50) -> list[MarketCompany]:
        df = self._load_kosdaq_listing()
        if df is None:
            return self._get_kosdaq_top_by_pykrx(limit)

        return self._companies_from_listing(df, limit, "KOSDAQ top")

    def get_kosdaq_bio_top_by_market_cap(self, limit: int = 50) -> list[MarketCompany]:
        df = self._load_kosdaq_listing()
        if df is None:
            logger.warning("[MarketClient] falling back to pykrx name-keyword KOSDAQ bio filter")
            return self._get_kosdaq_bio_top_by_pykrx(limit)

        df = self._enrich_listing_description(df)
        bio_df = self._filter_bio_listing(df)
        if bio_df.empty:
            logger.error("[MarketClient] KOSDAQ bio listing is empty after industry/name filtering")
            return []

        return self._companies_from_listing(bio_df, limit, "KOSDAQ bio top")

    def _load_kosdaq_listing(self):
        try:
            import FinanceDataReader as fdr

            try:
                df = fdr.StockListing("KOSDAQ")
            except Exception as exc:
                logger.warning("[MarketClient] direct KOSDAQ listing failed, trying KRX: %s", exc)
                df = fdr.StockListing("KRX")
                if "Market" in df.columns:
                    df = df[df["Market"].astype(str).str.upper() == "KOSDAQ"]
        except Exception as exc:
            logger.error("[MarketClient] KOSDAQ listing load failed: %s", exc)
            return None

        return df

    def _enrich_listing_description(self, df):
        try:
            import FinanceDataReader as fdr

            desc = fdr.StockListing("KRX-DESC")
        except Exception as exc:
            logger.warning("[MarketClient] KRX description load failed, using listing columns only: %s", exc)
            return df

        if desc is None or desc.empty or "Code" not in desc.columns:
            return df

        desc_columns = ["Code"] + [
            col
            for col in ("Sector", "Industry", "Products", "Dept")
            if col in desc.columns and col not in df.columns
        ]
        if len(desc_columns) == 1:
            return df

        df = df.copy()
        desc = desc[desc_columns].copy()
        df["Code"] = df["Code"].astype(str).str.zfill(6)
        desc["Code"] = desc["Code"].astype(str).str.zfill(6)
        return df.merge(desc, on="Code", how="left")

    def _filter_bio_listing(self, df):
        import pandas as pd

        industry_columns = [col for col in ("Industry", "Sector") if col in df.columns]
        product_columns = [col for col in ("Products",) if col in df.columns]
        strict_industry_mask = pd.Series(False, index=df.index)
        research_industry_mask = pd.Series(False, index=df.index)
        exclude_industry_mask = pd.Series(False, index=df.index)
        product_mask = pd.Series(False, index=df.index)
        name_mask = pd.Series(False, index=df.index)

        for col in industry_columns:
            text = df[col].fillna("").astype(str)
            for industry in BIO_STRICT_INDUSTRIES:
                strict_industry_mask = strict_industry_mask | text.str.contains(
                    industry,
                    case=False,
                    regex=False,
                )
            for industry in BIO_RESEARCH_INDUSTRIES:
                research_industry_mask = research_industry_mask | text.str.contains(
                    industry,
                    case=False,
                    regex=False,
                )
            for industry in BIO_EXCLUDE_INDUSTRIES:
                exclude_industry_mask = exclude_industry_mask | text.str.contains(
                    industry,
                    case=False,
                    regex=False,
                )

        for col in product_columns:
            text = df[col].fillna("").astype(str)
            for keyword in BIO_PRODUCT_KEYWORDS:
                product_mask = product_mask | text.str.contains(keyword, case=False, regex=False)

        if "Name" in df.columns:
            names = df["Name"].fillna("").astype(str)
            for keyword in BIO_NAME_KEYWORDS:
                name_mask = name_mask | names.str.contains(keyword, case=False, regex=False)

        force_include_mask = df["Code"].astype(str).str.zfill(6).isin(BIO_FORCE_INCLUDE_TICKERS)
        mask = (
            strict_industry_mask
            | (research_industry_mask & (name_mask | product_mask))
            | (name_mask & product_mask)
            | force_include_mask
        ) & (~exclude_industry_mask | force_include_mask)

        filtered = df[mask].copy()
        logger.info(
            "[MarketClient] KOSDAQ bio filter matched %d/%d companies using columns=%s",
            len(filtered),
            len(df),
            [*industry_columns, *product_columns, "Name"],
        )
        return filtered

    def _companies_from_listing(self, df, limit: int, label: str) -> list[MarketCompany]:

        required = {"Code", "Name", "Market", "Marcap"}
        missing = required - set(df.columns)
        if missing:
            logger.error("[MarketClient] %s listing missing columns: %s", label, sorted(missing))
            return []

        df = df.copy()
        df["Marcap"] = df["Marcap"].fillna(0).astype("int64")
        df = df.sort_values("Marcap", ascending=False).head(limit)

        companies: list[MarketCompany] = []
        for rank, (_, row) in enumerate(df.iterrows(), start=1):
            companies.append(
                MarketCompany(
                    rank=rank,
                    ticker_code=str(row["Code"]).zfill(6),
                    company_name=str(row["Name"]).strip(),
                    market=str(row.get("Market", "KOSDAQ")).strip(),
                    department=self._department_from_row(row),
                    market_cap_krw=int(row["Marcap"]),
                )
            )

        logger.info("[MarketClient] loaded %s %d by market cap", label, len(companies))
        return companies

    def _department_from_row(self, row) -> str:
        for column in ("Industry", "Products", "Sector", "Dept"):
            value = str(row.get(column, "")).strip()
            if value and value.lower() != "nan":
                return value
        return ""

    def _get_kosdaq_top_by_pykrx(self, limit: int) -> list[MarketCompany]:
        try:
            from pykrx import stock

            df = None
            used_date = ""
            for offset in range(0, 30):
                date = (datetime.now() - timedelta(days=offset)).strftime("%Y%m%d")
                candidate = stock.get_market_cap_by_ticker(date, market="KOSDAQ")
                if candidate is not None and not candidate.empty:
                    df = candidate
                    used_date = date
                    break

            if df is None or df.empty:
                logger.error("[MarketClient] pykrx KOSDAQ market cap data is empty")
                return []

            if "시가총액" not in df.columns:
                logger.error("[MarketClient] pykrx data missing market cap column: %s", list(df.columns))
                return []

            df = df.copy()
            df["시가총액"] = df["시가총액"].fillna(0).astype("int64")
            df = df.sort_values("시가총액", ascending=False).head(limit)

            companies: list[MarketCompany] = []
            for rank, (ticker, row) in enumerate(df.iterrows(), start=1):
                ticker_code = str(ticker).zfill(6)
                companies.append(
                    MarketCompany(
                        rank=rank,
                        ticker_code=ticker_code,
                        company_name=str(stock.get_market_ticker_name(ticker_code)).strip(),
                        market="KOSDAQ",
                        department="",
                        market_cap_krw=int(row["시가총액"]),
                    )
                )

            logger.info(
                "[MarketClient] loaded KOSDAQ top %d by pykrx market cap date=%s",
                len(companies),
                used_date,
            )
            return companies
        except Exception as exc:
            logger.error("[MarketClient] pykrx KOSDAQ listing load failed: %s", exc)
            return []

    def _get_kosdaq_bio_top_by_pykrx(self, limit: int) -> list[MarketCompany]:
        companies = self._get_kosdaq_top_by_pykrx(limit=500)
        filtered = [
            company
            for company in companies
            if any(keyword.lower() in company.company_name.lower() for keyword in BIO_NAME_KEYWORDS)
        ]
        logger.info("[MarketClient] pykrx KOSDAQ bio name filter matched %d companies", len(filtered))
        return [
            MarketCompany(
                rank=rank,
                ticker_code=company.ticker_code,
                company_name=company.company_name,
                market=company.market,
                department=company.department or "바이오 후보",
                market_cap_krw=company.market_cap_krw,
            )
            for rank, company in enumerate(filtered[:limit], start=1)
        ]


_market_client: MarketClient | None = None


def get_market_client() -> MarketClient:
    global _market_client
    if _market_client is None:
        _market_client = MarketClient()
    return _market_client
