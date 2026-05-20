"""Planner Agent — 분석 기업 설정 및 재시작 시 State 초기화.

역할:
  1. 최초 실행 시 누락 데이터 확인 및 분석 계획 수립하고, Open DART 실시간 재무 데이터 수집 및 연동
  2. 재시작(restart_required: True) 시 이전 분석 결과를 초기화하고 재분석 준비

재시작 시 초기화 항목:
  - 분석 점수 (financial_score, news_score, bio_score, disclosure_score)
  - 분석 상세 (news_detail, news_summary, news_data)
  - 등급 (loan_grade, loan_decision)
  - risk_score, supervisory_result
  - restart_required (False로 리셋)
  - errors (재시작 이전 오류는 유지)

절대 초기화하면 안 되는 항목:
  - restart_count  : 재시작 횟수 카운터 (무한루프 방지)
  - company_data   : 재분석에 필요한 입력값
  - gemini_api_key : 재분석에 필요한 API 키
  - gemini_model   : 재분석에 필요한 모델 설정
"""
from __future__ import annotations

import logging
from typing import Any
from models.schemas import BioAgentState, CompanyData

logger = logging.getLogger(__name__)

# 재시작 시 초기화할 State 키 목록
# restart_count, company_data, API 키는 절대 포함하면 안 됨
_RESET_KEYS = [
    "financial_score",
    "financial_detail",
    "news_score",
    "news_detail",
    "news_summary",
    "news_data",
    "bio_score",
    "bio_detail",
    "disclosure_score",
    "disclosure_detail",
    "risk_score",
    "loan_grade",
    "loan_decision",
    "supervisory_result",
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
            "restart_count":      0,
            "needs_human_review": False,
            "errors":             errors,
        }

    ticker_code = getattr(company, "ticker_code", "")

    # 🌟 Open DART 실시간 재무 데이터 수집 및 연동 시도 (결측치 검사 전 실행)
    from services.dart_client import get_dart_client
    dart = get_dart_client()
    if ticker_code and dart.is_available():
        try:
            live_fin = dart.fetch_financials(ticker_code)
            if live_fin:
                logger.info(
                    "[Planner] %s (%s) DART 실시간 재무 수집 성공: %s",
                    company_name,
                    ticker_code,
                    live_fin,
                )
                
                if company.financial:
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
            logger.warning("[Planner] DART 실시간 재무 수집 실패로 baseline 모의 데이터 유지: %s", e)

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
            "[Planner] 🌟 %s 맞춤형 여신 분석 지침 수립: %s",
            company.company_name,
            directives,
        )

    # 누락 데이터 확인
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
        logger.warning("[Planner] %s — 누락 데이터: %s", company_name, missing)
        errors.append(f"PlannerAgent: 누락 데이터 항목 — {missing}")

    logger.info(
        "[Planner] %s — 분석 계획 완료 | 필수항목=%s | 누락=%s",
        company_name, REQUIRED_DATA_ITEMS, missing,
    )

    return {
        "restart_required":   False,
        "restart_count":      0,
        "needs_human_review": False,
        "errors":             errors,
    }

