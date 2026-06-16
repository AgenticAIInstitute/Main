from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree

import requests

logger = logging.getLogger(__name__)


@dataclass
class PatentSummary:
    source_available: bool
    patent_count: int = 0
    registered_count: int = 0
    applied_count: int = 0
    message: str = ""
    matched_terms: list[str] | None = None
    searched_terms: list[str] | None = None


class PatentClient:
    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout
        self._api_key = os.getenv("KIPRIS_API_KEY", "").strip()
        self._api_url = os.getenv("KIPRIS_API_URL", "").strip()

    def search_company(self, company_name: str, aliases: list[str] | None = None) -> PatentSummary:
        if not self._api_key:
            return PatentSummary(source_available=False, message="KIPRIS_API_KEY is not set")
        if not self._api_url:
            return PatentSummary(source_available=False, message="KIPRIS_API_URL is not set")
        if not company_name:
            return PatentSummary(source_available=False, message="company_name is empty")

        searched_terms = self._applicant_terms(company_name, aliases)
        summaries = [self._search_applicant(term) for term in searched_terms]
        available = [summary for summary in summaries if summary.source_available]
        if not available:
            message = "; ".join(summary.message for summary in summaries if summary.message)
            return PatentSummary(
                source_available=False,
                message=message or "KIPRIS search failed",
                searched_terms=searched_terms,
            )

        matched_terms = [
            term
            for term, summary in zip(searched_terms, summaries)
            if summary.source_available and summary.patent_count > 0
        ]
        return PatentSummary(
            source_available=True,
            patent_count=sum(summary.patent_count for summary in available),
            registered_count=sum(summary.registered_count for summary in available),
            applied_count=sum(summary.applied_count for summary in available),
            matched_terms=matched_terms,
            searched_terms=searched_terms,
        )

    def _search_applicant(self, applicant_name: str) -> PatentSummary:
        params = {
            "accessKey": self._api_key,
            "serviceKey": self._api_key,
            "applicantName": applicant_name,
            "applicant": applicant_name,
            "query": applicant_name,
            "word": applicant_name,
        }

        try:
            response = requests.get(self._api_url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("[Patent] KIPRIS search failed for applicant=%s: %s", applicant_name, exc)
            return PatentSummary(source_available=False, message=str(exc))

        text = response.text
        content_type = response.headers.get("content-type", "")
        if "json" in content_type.lower():
            try:
                return self._from_json(response.json())
            except Exception as exc:
                logger.warning("[Patent] JSON parse failed for applicant=%s: %s", applicant_name, exc)
                return PatentSummary(source_available=False, message=str(exc))

        return self._from_xml_or_text(text)

    @staticmethod
    def _applicant_terms(company_name: str, aliases: list[str] | None = None) -> list[str]:
        raw_terms = [company_name, *(aliases or [])]
        terms: list[str] = []
        corporate_prefixes = ("주식회사", "(주)", "㈜")
        corporate_suffixes = ("주식회사", "(주)", "㈜", "Co., Ltd.", "CO., LTD.", "Inc.", "INC.")

        for raw in raw_terms:
            term = raw.strip()
            if not term:
                continue
            terms.append(term)

            simplified = term
            for prefix in corporate_prefixes:
                simplified = simplified.replace(prefix, "")
            for suffix in corporate_suffixes:
                simplified = simplified.replace(suffix, "")
            simplified = simplified.strip(" ,")
            if simplified and simplified != term:
                terms.append(simplified)

            if term.isascii():
                terms.append(term.upper())

        deduped: list[str] = []
        seen: set[str] = set()
        for term in terms:
            key = term.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(term)
        return deduped

    def _from_json(self, payload: Any) -> PatentSummary:
        values = list(self._walk(payload))
        patent_count = self._first_int(values, ("totalCount", "count", "patentCount", "numOfRows"))
        status_text = " ".join(str(value) for _, value in values)
        registered_count = self._count_status(status_text, ("registration", "registered", "등록"))
        applied_count = self._count_status(status_text, ("application", "applied", "출원", "공개"))
        return PatentSummary(
            source_available=True,
            patent_count=patent_count or max(registered_count + applied_count, 0),
            registered_count=registered_count,
            applied_count=applied_count,
        )

    def _from_xml_or_text(self, text: str) -> PatentSummary:
        try:
            root = ElementTree.fromstring(text)
            values = [(elem.tag, elem.text or "") for elem in root.iter()]
            patent_count = self._first_int(values, ("totalCount", "count", "patentCount", "numOfRows"))
            status_text = " ".join(value for _, value in values)
        except Exception:
            patent_count = 1 if text.strip() else 0
            status_text = text

        registered_count = self._count_status(status_text, ("registration", "registered", "등록"))
        applied_count = self._count_status(status_text, ("application", "applied", "출원", "공개"))
        return PatentSummary(
            source_available=True,
            patent_count=patent_count or max(registered_count + applied_count, 0),
            registered_count=registered_count,
            applied_count=applied_count,
        )

    @staticmethod
    def _walk(payload: Any) -> list[tuple[str, Any]]:
        items: list[tuple[str, Any]] = []
        if isinstance(payload, dict):
            for key, value in payload.items():
                items.append((str(key), value))
                items.extend(PatentClient._walk(value))
        elif isinstance(payload, list):
            for value in payload:
                items.extend(PatentClient._walk(value))
        return items

    @staticmethod
    def _first_int(values: list[tuple[str, Any]], names: tuple[str, ...]) -> int:
        lowered = {name.lower() for name in names}
        for key, value in values:
            if key.lower() in lowered:
                try:
                    return int(str(value).replace(",", "").strip())
                except ValueError:
                    continue
        return 0

    @staticmethod
    def _count_status(text: str, needles: tuple[str, ...]) -> int:
        normalized = text.lower()
        return sum(normalized.count(needle.lower()) for needle in needles)


_patent_client: PatentClient | None = None


def get_patent_client() -> PatentClient:
    global _patent_client
    if _patent_client is None:
        _patent_client = PatentClient()
    return _patent_client
