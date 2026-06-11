"""Planner Agent — 분석 기업 설정 및 재시작 시 State 초기화.

역할:
  1. 최초 실행 시 누락 데이터 확인 및 분석 계획 수립
  2. 재시작(restart_required: True) 시 이전 분석 결과를 초기화하고 재분석 준비

재시작 시 초기화 항목 (BioAgentState 실제 필드명 기준):
  - financial_result, news_result, bio_domain_result, disclosure_result
  - risk_score_result, supervisory_result, loan_decision_result, report
  - needs_human_review
  - restart_required (False로 리셋)
  - errors (재시작 이전 오류는 유지)

절대 초기화하면 안 되는 항목:
  - restart_count   : 재시작 횟수 카운터 (무한루프 방지)
  - company_data    : 재분석에 필요한 입력값
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 재시작 시 초기화할 State 키 목록 (BioAgentState 실제 필드명 사용)
# restart_count, company_data 는 절대 포함하면 안 됨
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
    """
    LangGraph 노드 — 최초 실행 또는 재시작 시 State 준비.

    재시작 감지 기준: restart_required == True
    """
    company      = state.get("company_data")
    company_name = getattr(company, "company_name", "") if company else ""
    restart_count = state.get("restart_count", 0)
    is_restart    = state.get("restart_required", False)

    # ── 재시작 시 → State 초기화 후 재분석 ──────
    if is_restart:
        logger.warning(
            "[Planner] %s — 재시작 감지 (restart_count: %d), State 초기화 후 재분석",
            company_name, restart_count,
        )

        reset_patch = {key: None for key in _RESET_KEYS}
        reset_patch["restart_required"] = False          # 재시작 플래그 리셋 (무한루프 방지)
        reset_patch["errors"]           = list(state.get("errors", []))  # 기존 오류 유지
        # restart_count는 절대 건드리지 않음

        logger.info("[Planner] %s — State 초기화 완료, 재분석 시작", company_name)
        return reset_patch

    # ── 최초 실행 시 → 누락 데이터 확인 ────────
    logger.info("[Planner] %s — 분석 시작", company_name)

    errors: list[str] = []
    missing: list[str] = []

    if company is None:
        errors.append("PlannerAgent: company_data 없음 — 분석 불가")
        logger.error("[Planner] company_data 없음")
        return {
            "restart_required":   False,
            "needs_human_review": False,
            "errors":             errors,
        }

    # 누락 데이터 확인
    if company.news is None:
        missing.append("news_data")
    if not company.financial:
        missing.append("financial_data")
    if not company.bio_domain:
        missing.append("bio_domain_data")
    if not company.disclosure:
        missing.append("disclosure_data")

    # 들여쓰기 및 함수 내부 포함 구조 정상화 완료
    if missing:
        logger.warning("[Planner] %s — 누락 데이터: %s", company_name, missing)
        errors.append(f"PlannerAgent: 누락 데이터 항목 — {missing}")

    logger.info(
        "[Planner] %s — 분석 계획 완료 | 필수항목=%s | 누락=%s",
        company_name, REQUIRED_DATA_ITEMS, missing,
    )

    return {
        "restart_required":   False,
        "needs_human_review": False,
        "errors":             errors,
    }