from __future__ import annotations

import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from xml.etree import ElementTree

import requests

from models.schemas import DisclosureData, FinancialData

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DartCompanyData:
    financial: FinancialData | None
    disclosure: DisclosureData
    financial_source: str
    disclosure_source: str


class DartClient:
    def __init__(self, timeout: int = 15) -> None:
        self._api_key = (
            os.getenv("DART_API_KEY", "")
            or os.getenv("OPEN_DART_API_KEY", "")
            or os.getenv("DART_KEY", "")
        ).strip()
        self._timeout = timeout
        self._corp_codes: dict[str, str] | None = None
        self._base_url = "https://opendart.fss.or.kr/api"

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    def get_financial_data(
        self,
        ticker_code: str,
        fallback_data: FinancialData | None = None,
    ) -> FinancialData | None:
        company_data = self.get_company_data(ticker_code)
        return company_data.financial or fallback_data

    def get_company_data(self, ticker_code: str) -> DartCompanyData:
        corp_code = self.get_corp_code(ticker_code)
        if not corp_code:
            return DartCompanyData(
                financial=None,
                disclosure=DisclosureData(risk_keywords=["DART corp_code unavailable"]),
                financial_source="DART corp_code unavailable",
                disclosure_source="DART corp_code unavailable",
            )

        financial, financial_source = self.get_latest_financial_data(corp_code)
        disclosure = self.get_recent_disclosure_data(corp_code)
        return DartCompanyData(
            financial=financial,
            disclosure=disclosure,
            financial_source=financial_source,
            disclosure_source="DART recent disclosures",
        )

    def get_corp_code(self, ticker_code: str) -> str | None:
        if not self.available:
            return None
        if self._corp_codes is None:
            self._corp_codes = self._load_corp_codes()
        return self._corp_codes.get(str(ticker_code).zfill(6))

    def _load_corp_codes(self) -> dict[str, str]:
        try:
            response = requests.get(
                f"{self._base_url}/corpCode.xml",
                params={"crtfc_key": self._api_key},
                timeout=self._timeout,
            )
            response.raise_for_status()
            with zipfile.ZipFile(BytesIO(response.content)) as archive:
                xml_bytes = archive.read("CORPCODE.xml")
            root = ElementTree.fromstring(xml_bytes)
        except Exception as exc:
            logger.warning("[DART] corpCode load failed: %s", exc)
            return {}

        mapping: dict[str, str] = {}
        for item in root.findall("list"):
            corp_code = (item.findtext("corp_code") or "").strip()
            stock_code = (item.findtext("stock_code") or "").strip()
            if corp_code and stock_code:
                mapping[stock_code.zfill(6)] = corp_code
        logger.info("[DART] loaded %d stock corp codes", len(mapping))
        return mapping

    def get_latest_financial_data(self, corp_code: str) -> tuple[FinancialData | None, str]:
        current_year = datetime.now().year
        for year in range(current_year - 1, current_year - 4, -1):
            for fs_div in ("CFS", "OFS"):
                rows = self._financial_rows(corp_code, year, fs_div)
                if not rows:
                    continue
                financial = self._to_financial_data(rows)
                if financial:
                    return financial, f"DART {year} annual {fs_div}"
        return None, "DART financial statements unavailable"

    def _financial_rows(self, corp_code: str, year: int, fs_div: str) -> list[dict]:
        try:
            response = requests.get(
                f"{self._base_url}/fnlttSinglAcntAll.json",
                params={
                    "crtfc_key": self._api_key,
                    "corp_code": corp_code,
                    "bsns_year": str(year),
                    "reprt_code": "11011",
                    "fs_div": fs_div,
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("[DART] financial request failed corp=%s year=%s %s: %s", corp_code, year, fs_div, exc)
            return []

        if payload.get("status") != "000":
            return []
        return payload.get("list", []) or []

    def _to_financial_data(self, rows: list[dict]) -> FinancialData | None:
        current_assets = self._find_amount(rows, ("유동자산",))
        current_liabilities = self._find_amount(rows, ("유동부채",))
        total_liabilities = self._find_amount(rows, ("부채총계",))
        total_equity = self._find_amount(rows, ("자본총계",))
        revenue = self._find_amount(rows, ("매출액", "영업수익", "수익(매출액)"))
        operating_income = self._find_amount(rows, ("영업이익",))
        operating_cash_flow = self._find_amount(rows, ("영업활동현금흐름", "영업활동으로 인한 현금흐름"))
        cash_assets = self._find_amount(rows, ("현금및현금성자산", "현금 및 현금성자산"))
        rd_expense = self._find_amount(rows, ("연구개발비", "경상연구개발비"))

        if not any((current_assets, total_liabilities, revenue, operating_income, cash_assets)):
            return None

        current_ratio = self._ratio(current_assets, current_liabilities, multiplier=1.0, default=1.0)
        debt_ratio = self._ratio(total_liabilities, total_equity, multiplier=100.0, default=100.0)
        operating_profit_margin = self._ratio(operating_income, revenue, multiplier=100.0, default=0.0)
        rd_expense_ratio = self._ratio(rd_expense, revenue, multiplier=100.0, default=10.0)

        ocf_eok = (operating_cash_flow or 0.0) / 100_000_000
        cash_eok = (cash_assets or 0.0) / 100_000_000
        if ocf_eok < 0:
            monthly_burn = abs(ocf_eok) / 12
            runway = cash_eok / monthly_burn if monthly_burn > 0 else 24.0
        else:
            runway = 24.0

        return FinancialData(
            current_ratio=round(current_ratio, 2),
            debt_ratio=round(debt_ratio, 2),
            operating_cash_flow=round(ocf_eok, 2),
            cash_assets=round(cash_eok, 2),
            cash_runway_months=round(min(runway, 60.0), 1),
            operating_profit_margin=round(operating_profit_margin, 2),
            rd_expense_ratio=round(rd_expense_ratio, 2),
        )

    def get_recent_disclosure_data(self, corp_code: str, days: int = 365) -> DisclosureData:
        end = datetime.now()
        start = end - timedelta(days=days)
        try:
            response = requests.get(
                f"{self._base_url}/list.json",
                params={
                    "crtfc_key": self._api_key,
                    "corp_code": corp_code,
                    "bgn_de": start.strftime("%Y%m%d"),
                    "end_de": end.strftime("%Y%m%d"),
                    "page_count": "100",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("[DART] disclosure request failed corp=%s: %s", corp_code, exc)
            return DisclosureData(risk_keywords=["DART disclosure unavailable"])

        if payload.get("status") not in {"000", "013"}:
            return DisclosureData(risk_keywords=["DART disclosure unavailable"])

        text = " ".join(str(item.get("report_nm", "")) for item in payload.get("list", []) or [])
        return DisclosureData(risk_keywords=self._risk_keywords(text))

    @staticmethod
    def _risk_keywords(text: str) -> list[str]:
        keyword_map = {
            "관리종목": "관리종목",
            "상장폐지": "상장폐지",
            "거래정지": "거래정지",
            "감사의견": "감사의견 관련",
            "횡령": "횡령",
            "배임": "배임",
            "회생": "회생절차",
            "불성실공시": "불성실공시",
            "유상증자": "유상증자 반복",
            "최대주주 변경": "최대주주 변경",
            "소송": "소송",
            "영업정지": "영업정지",
        }
        found: list[str] = []
        for needle, label in keyword_map.items():
            if needle in text and label not in found:
                found.append(label)
        return found

    @staticmethod
    def _find_amount(rows: list[dict], names: tuple[str, ...]) -> float | None:
        candidates: list[tuple[int, float]] = []
        for row in rows:
            account = str(row.get("account_nm", ""))
            if not any(name in account for name in names):
                continue
            amount = DartClient._parse_amount(row.get("thstrm_amount"))
            if amount is None:
                continue
            sj_div = str(row.get("sj_div", ""))
            priority = 0 if sj_div in {"BS", "IS", "CIS", "CF"} else 1
            candidates.append((priority, amount))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    @staticmethod
    def _parse_amount(value: object) -> float | None:
        if value is None:
            return None
        text = str(value).replace(",", "").strip()
        if not text or text == "-":
            return None
        negative = text.startswith("(") and text.endswith(")")
        text = text.strip("()")
        try:
            amount = float(text)
        except ValueError:
            return None
        return -amount if negative else amount

    @staticmethod
    def _ratio(numerator: float | None, denominator: float | None, multiplier: float, default: float) -> float:
        if numerator is None or denominator in (None, 0):
            return default
        return numerator / denominator * multiplier


_dart_client: DartClient | None = None


def get_dart_client() -> DartClient:
    global _dart_client
    if _dart_client is None:
        _dart_client = DartClient()
    return _dart_client
