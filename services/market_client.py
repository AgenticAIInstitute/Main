from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


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
            return self._get_kosdaq_top_by_pykrx(limit)

        required = {"Code", "Name", "Market", "Marcap"}
        missing = required - set(df.columns)
        if missing:
            logger.error("[MarketClient] KOSDAQ listing missing columns: %s", sorted(missing))
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
                    department=str(row.get("Dept", "")).strip(),
                    market_cap_krw=int(row["Marcap"]),
                )
            )

        logger.info("[MarketClient] loaded KOSDAQ top %d by market cap", len(companies))
        return companies

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


_market_client: MarketClient | None = None


def get_market_client() -> MarketClient:
    global _market_client
    if _market_client is None:
        _market_client = MarketClient()
    return _market_client
