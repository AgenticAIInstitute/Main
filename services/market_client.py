from __future__ import annotations

import logging
from dataclasses import dataclass

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

            df = fdr.StockListing("KOSDAQ")
        except Exception as exc:
            logger.error("[MarketClient] KOSDAQ listing load failed: %s", exc)
            return []

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


_market_client: MarketClient | None = None


def get_market_client() -> MarketClient:
    global _market_client
    if _market_client is None:
        _market_client = MarketClient()
    return _market_client
