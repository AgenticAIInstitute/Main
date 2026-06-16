"""Planner Agent - analysis setup and restart-safe state reset."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_RESET_KEYS = [
    "financial_result",
    "news_result",
    "bio_domain_result",
    "disclosure_result",
    "risk_score_result",
    "supervisory_result",
    "loan_decision_result",
    "report",
    "needs_human_review",
]

REQUIRED_DATA_ITEMS = [
    "financial_data",
    "news_data",
    "bio_domain_data",
    "disclosure_data",
]


def planner_node(state: dict) -> dict:
    """Prepare state for first analysis or clear derived results on restart."""
    company = state.get("company_data")
    company_name = getattr(company, "company_name", "") if company else ""
    restart_count = state.get("restart_count", 0)
    is_restart = state.get("restart_required", False)

    if is_restart:
        logger.warning(
            "[Planner] %s - restart detected (restart_count=%d); clearing derived results",
            company_name,
            restart_count,
        )
        reset_patch = {key: None for key in _RESET_KEYS}
        reset_patch["restart_required"] = False
        reset_patch["errors"] = list(state.get("errors", []))
        return reset_patch

    logger.info("[Planner] %s - analysis started", company_name)

    errors: list[str] = []
    missing: list[str] = []

    if company is None:
        errors.append("PlannerAgent: company_data 없음 - 분석 불가")
        logger.error("[Planner] company_data missing")
        return {
            "restart_required": False,
            "needs_human_review": False,
            "errors": errors,
        }

    if company.news is None:
        missing.append("news_data")
    if not company.financial:
        missing.append("financial_data")
    if not company.bio_domain:
        missing.append("bio_domain_data")
    if not company.disclosure_data:
        missing.append("disclosure_data")

    if missing:
        logger.warning("[Planner] %s - missing data: %s", company_name, missing)
        errors.append(f"PlannerAgent: 누락 데이터 항목 - {missing}")

    logger.info(
        "[Planner] %s - plan complete | required=%s | missing=%s",
        company_name,
        REQUIRED_DATA_ITEMS,
        missing,
    )

    return {
        "company_data": company,
        "restart_required": False,
        "needs_human_review": False,
        "errors": errors,
    }
