from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

logger = logging.getLogger(__name__)


STAGE_RANK = {
    "Preclinical": 0,
    "Phase 1": 1,
    "Phase 2": 2,
    "Phase 3": 3,
    "NDA": 4,
    "Approved": 5,
}


@dataclass
class ClinicalTrialSummary:
    source_available: bool
    trial_count: int = 0
    highest_stage: str = "Preclinical"
    active_count: int = 0
    completed_count: int = 0
    stopped_count: int = 0
    statuses: list[str] | None = None
    searched_terms: list[str] | None = None
    matched_terms: list[str] | None = None


class ClinicalTrialsClient:
    def __init__(self, timeout: int = 10) -> None:
        self._timeout = timeout
        self._base_url = "https://clinicaltrials.gov/api/v2/studies"

    def search_company(
        self,
        company_name: str,
        aliases: list[str] | None = None,
        page_size: int = 50,
    ) -> ClinicalTrialSummary:
        if not company_name:
            return ClinicalTrialSummary(source_available=False)

        searched_terms = self._search_terms(company_name, aliases)
        all_studies: dict[str, dict] = {}
        source_available = False
        matched_terms: list[str] = []

        for term in searched_terms:
            studies = self._fetch_studies(term, page_size)
            if studies is None:
                continue
            source_available = True
            filtered = self._filter_related(studies, searched_terms)
            if filtered:
                matched_terms.append(term)
            for study in filtered:
                protocol = study.get("protocolSection", {})
                identification = protocol.get("identificationModule", {})
                key = (
                    identification.get("nctId")
                    or identification.get("orgStudyIdInfo", {}).get("id")
                    or str(study)
                )
                all_studies[str(key)] = study

        if not source_available:
            return ClinicalTrialSummary(source_available=False, searched_terms=searched_terms)

        return self._summarize(list(all_studies.values()), searched_terms, matched_terms)

    def _fetch_studies(self, term: str, page_size: int) -> list[dict] | None:
        try:
            response = requests.get(
                self._base_url,
                params={"query.term": term, "pageSize": page_size, "format": "json"},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            logger.warning("[ClinicalTrials] search failed for %s: %s", term, exc)
            return None

        return payload.get("studies", []) or []

    def _summarize(
        self,
        studies: list[dict],
        searched_terms: list[str],
        matched_terms: list[str],
    ) -> ClinicalTrialSummary:
        statuses: list[str] = []
        highest_stage = "Preclinical"
        active_count = 0
        completed_count = 0
        stopped_count = 0

        for study in studies:
            protocol = study.get("protocolSection", {})
            design = protocol.get("designModule", {})
            status = protocol.get("statusModule", {}).get("overallStatus", "")
            stage = self._stage_from_phases(design.get("phases", []))

            if STAGE_RANK.get(stage, 0) > STAGE_RANK.get(highest_stage, 0):
                highest_stage = stage

            if status:
                statuses.append(status)
                normalized = status.upper()
                if normalized in {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}:
                    active_count += 1
                elif normalized == "COMPLETED":
                    completed_count += 1
                elif normalized in {"TERMINATED", "WITHDRAWN", "SUSPENDED"}:
                    stopped_count += 1

        return ClinicalTrialSummary(
            source_available=True,
            trial_count=len(studies),
            highest_stage=highest_stage,
            active_count=active_count,
            completed_count=completed_count,
            stopped_count=stopped_count,
            statuses=statuses,
            searched_terms=searched_terms,
            matched_terms=matched_terms,
        )

    @staticmethod
    def _search_terms(company_name: str, aliases: list[str] | None) -> list[str]:
        values = [company_name, *(aliases or [])]
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            term = value.strip()
            if not term:
                continue
            key = term.lower()
            if key not in seen:
                seen.add(key)
                result.append(term)
        return result

    @staticmethod
    def _filter_related(studies: list[dict], aliases: list[str]) -> list[dict]:
        filtered: list[dict] = []
        alias_terms = [alias.lower() for alias in aliases if len(alias.strip()) >= 3]
        for study in studies:
            haystack = ClinicalTrialsClient._study_match_text(study)
            if any(term.lower() in haystack for term in alias_terms):
                filtered.append(study)
        return filtered

    @staticmethod
    def _study_match_text(study: dict) -> str:
        protocol = study.get("protocolSection", {})
        sponsor = protocol.get("sponsorCollaboratorsModule", {})
        arms = protocol.get("armsInterventionsModule", {})
        identification = protocol.get("identificationModule", {})
        conditions = protocol.get("conditionsModule", {})
        pieces = [
            sponsor,
            arms,
            identification,
            conditions,
            protocol.get("descriptionModule", {}),
        ]
        return " ".join(str(piece).lower() for piece in pieces)

    @staticmethod
    def _stage_from_phases(phases: Any) -> str:
        if not phases:
            return "Preclinical"

        phase_text = " ".join(str(phase).upper() for phase in phases)
        if "PHASE3" in phase_text or "PHASE 3" in phase_text:
            return "Phase 3"
        if "PHASE2" in phase_text or "PHASE 2" in phase_text:
            return "Phase 2"
        if "PHASE1" in phase_text or "PHASE 1" in phase_text:
            return "Phase 1"
        return "Preclinical"


_clinical_trials_client: ClinicalTrialsClient | None = None


def get_clinical_trials_client() -> ClinicalTrialsClient:
    global _clinical_trials_client
    if _clinical_trials_client is None:
        _clinical_trials_client = ClinicalTrialsClient()
    return _clinical_trials_client
