"""SupervisoryReviewAgent — B/C 등급 재평가 에이전트.

흐름:
  1. 등급 확인 — B 또는 C가 아니면 패스
  2. 규칙 기반 special_case 감지
  3. special_case 없으면
       - B → 자동 승인 (B 유지)
       - C → Human Review로 전달
  4. special_case 있으면 LLM 종합 판단 (최대 MAX_RETRY회)
       - B 허용 이동 범위: A, B, C, D
       - C 허용 이동 범위: B, C, D, E
  5. LLM이 허용 범위 밖 등급 반환 시
       - 전체 분석 재시도 후 LLM 재호출
       - MAX_RETRY 초과 시 오류로 처리 → Human Review 강제 전달
  6. 조정 근거 State에 저장

등급별 최종 처리:
  A      → 자동 승인
  B      → SupervisoryReviewAgent → 자동 처리
  C      → SupervisoryReviewAgent → 단순 케이스는 Human Review, LLM 판단 후 B면 자동 승인 / D,E면 자동 거절
  D / E  → 자동 거절
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

# 등급별 허용 이동 범위
ALLOWED_TRANSITIONS: Dict[str, List[str]] = {
    "B": ["A", "B", "C", "D"],
    "C": ["B", "C", "D", "E"],
}

# 점수 모순 감지 임계값 (두 점수 차이가 이 값 이상이면 모순으로 판단)
CONFLICT_THRESHOLD = 30

# 치명적 리스크 키워드 (News Agent neg_high 기반)
FATAL_KEYWORDS = ["횡령", "배임", "상장폐지", "감사의견 거절", "FDA 거절", "허가 취소"]

# LLM 요약에서 치명적 표현 감지 키워드
LLM_FATAL_EXPRESSIONS = [
    "치명적", "심각한 리스크", "대출 불가", "즉각적인 위험",
    "회생 불가", "파산", "상폐 우려", "존폐 위기",
]

# news_score 이 값 이하이면 치명적 리스크로 판단
FATAL_SCORE_THRESHOLD = 30

# LLM 허용 범위 밖 등급 반환 시 최대 재시도 횟수
MAX_RETRY = 2


# ──────────────────────────────────────────────
# 2단계 — 규칙 기반 special_case 감지
# ──────────────────────────────────────────────
def _detect_special_cases(state: dict) -> List[str]:
    """
    State에서 점수를 읽어 special_case 목록을 반환.

    감지 항목:
      - 데이터 누락      : news_data_missing, bio_data_missing
      - 점수 간 모순     : financial_news_conflict, bio_financial_conflict
      - 치명적 리스크    : fatal_risk_detected
    """
    cases: List[str] = []

    financial_score  = state.get("financial_score")
    news_score       = state.get("news_score")
    bio_score        = state.get("bio_score")
    disclosure_score = state.get("disclosure_score")
    news_detail      = state.get("news_detail", {})

    # ── 데이터 누락 ───────────────────────────
    if news_score is None:
        cases.append("news_data_missing")
    if bio_score is None:
        cases.append("bio_data_missing")

    # ── 점수 간 모순 ──────────────────────────
    if (
        financial_score is not None
        and news_score is not None
        and abs(financial_score - news_score) >= CONFLICT_THRESHOLD
    ):
        cases.append("financial_news_conflict")

    if (
        bio_score is not None
        and financial_score is not None
        and abs(bio_score - financial_score) >= CONFLICT_THRESHOLD
    ):
        cases.append("bio_financial_conflict")

    # ── 치명적 리스크 (3가지 방식 중 하나라도 해당하면 감지) ────
    fatal_detected = False
    fatal_sources  = []

    # 1) 키워드 매칭 — neg_high에 치명적 키워드 있는지
    neg_high = news_detail.get("neg_high", [])
    if any(kw in neg_high for kw in FATAL_KEYWORDS):
        fatal_detected = True
        fatal_sources.append("keyword")

    # 2) LLM 요약에서 치명적 표현 감지
    news_summary = state.get("news_summary", "")
    if any(expr in news_summary for expr in LLM_FATAL_EXPRESSIONS):
        fatal_detected = True
        fatal_sources.append("llm_summary")

    # 3) news_score 자체가 임계값 이하
    if news_score is not None and news_score <= FATAL_SCORE_THRESHOLD:
        fatal_detected = True
        fatal_sources.append("low_score")

    if fatal_detected:
        cases.append(f"fatal_risk_detected({', '.join(fatal_sources)})")

    return cases


# ──────────────────────────────────────────────
# 3단계 — LLM 종합 판단
# ──────────────────────────────────────────────
def _llm_judge(
    state: dict,
    current_grade: str,
    special_cases: List[str],
    gemini_api_key: str,
    gemini_model: str,
) -> Tuple[Optional[str], str]:
    """
    LLM에게 등급 조정 여부를 판단하게 한다.

    Returns:
        adjusted_grade : 조정된 등급 (None이면 호출 실패)
        reason         : 조정 근거 (비어있으면 신뢰 불가)
    """
    allowed = ALLOWED_TRANSITIONS[current_grade]

    scores_text = (
        f"재무 점수: {state.get('financial_score', 'N/A')}\n"
        f"뉴스 점수: {state.get('news_score', 'N/A')}\n"
        f"바이오 점수: {state.get('bio_score', 'N/A')}\n"
        f"공시 점수: {state.get('disclosure_score', 'N/A')}"
    )

    news_detail  = state.get("news_detail", {})
    news_events  = (
        f"강한 부정 키워드: {news_detail.get('neg_high', [])}\n"
        f"중간 부정 키워드: {news_detail.get('neg_mid', [])}\n"
        f"긍정 키워드: {news_detail.get('positives', [])}"
    )
    news_summary = state.get("news_summary", "")

    prompt = (
        f"당신은 바이오 기업 여신 심사 수석 심사역입니다.\n"
        f"현재 등급 {current_grade}인 기업의 분석 결과를 검토하고 최종 등급을 판정하세요.\n\n"
        f"[분석 점수]\n{scores_text}\n\n"
        f"[감지된 특이사항]\n{', '.join(special_cases) if special_cases else '없음'}\n\n"
        f"[주요 뉴스 이벤트]\n{news_events}\n\n"
        f"[뉴스 종합 요약]\n{news_summary if news_summary else '없음'}\n\n"
        f"허용 이동 범위: {allowed} 중 하나만 선택하세요.\n\n"
        f"판단 기준:\n"
        f"- 특이사항이 일시적 이슈라면 현재 등급 유지\n"
        f"- 모든 지표가 실제로 양호하면 상향\n"
        f"- 구조적 문제 또는 치명적 리스크가 확인되면 하향\n\n"
        f"다른 텍스트 없이 JSON만 출력하세요:\n"
        f"{{\n"
        f'  "adjusted_grade": "{allowed[0]}~{allowed[-1]} 중 하나",\n'
        f'  "reason": "판단 근거를 2~3문장으로 구체적으로 작성"\n'
        f"}}"
    )

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=gemini_model,
            google_api_key=gemini_api_key,
            temperature=0.1,
           
        )
        result  = llm.invoke(prompt)
        content = result.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        parsed         = json.loads(content)
        adjusted_grade = parsed.get("adjusted_grade", "").strip().upper()
        reason         = parsed.get("reason", "").strip()

        return adjusted_grade, reason

    except Exception as e:
        logger.warning("[Supervisory] LLM 호출 실패: %s", e)
        return None, f"LLM 호출 실패 — {e}"


# ──────────────────────────────────────────────
# 재시도 포함 LLM 판단
# ──────────────────────────────────────────────
def _llm_judge_with_retry(
    state: dict,
    current_grade: str,
    special_cases: List[str],
    gemini_api_key: str,
    gemini_model: str,
    errors: List[str],
) -> Tuple[Optional[str], str, bool]:
    """
    LLM 판단 + 허용 범위 밖 등급 반환 시 재시도 로직.

    Returns:
        adjusted_grade  : 최종 등급 (None이면 오류)
        reason          : 판단 근거
        is_error        : True면 오류로 처리 → Human Review 강제 전달
    """
    allowed = ALLOWED_TRANSITIONS[current_grade]

    for retry in range(1, MAX_RETRY + 1):
        adjusted_grade, reason = _llm_judge(
            state, current_grade, special_cases, gemini_api_key, gemini_model
        )

        # LLM 호출 자체 실패
        if adjusted_grade is None:
            errors.append(
                f"Supervisory: LLM 호출 실패 (시도 {retry}/{MAX_RETRY}) — {reason}"
            )
            continue

        # reason 비어있음
        if not reason:
            errors.append(
                f"Supervisory: LLM reason 비어있음 (시도 {retry}/{MAX_RETRY}) — 재시도"
            )
            logger.warning("[Supervisory] reason 비어있음 — 재시도 %d/%d", retry, MAX_RETRY)
            continue

        # 허용 범위 안 → 정상 반환
        if adjusted_grade in allowed:
            return adjusted_grade, reason, False

        # 허용 범위 밖
        errors.append(
            f"Supervisory: LLM이 허용 범위 밖 등급 반환 "
            f"({current_grade} → {adjusted_grade}, 허용: {allowed}) "
            f"— 재시도 {retry}/{MAX_RETRY}"
        )
        logger.warning(
            "[Supervisory] 허용 범위 밖 등급 (%s → %s) — 재시도 %d/%d",
            current_grade, adjusted_grade, retry, MAX_RETRY,
        )

    # MAX_RETRY 초과 → 오류 처리
    error_msg = (
        f"Supervisory: {MAX_RETRY}회 재시도 후에도 유효한 등급 반환 실패 "
        f"— Human Review 강제 전달"
    )
    errors.append(error_msg)
    logger.error("[Supervisory] %s", error_msg)
    return None, error_msg, True


# ──────────────────────────────────────────────
# Human Review 여부 결정
# ──────────────────────────────────────────────
def _needs_human_review(
    current_grade: str,
    adjusted_grade: str,
    special_cases: List[str],
    llm_called: bool,
) -> bool:
    """
    Human Review가 필요한지 판단.

    Human Review로 가는 경우:
      - C등급이고 special_case 없음 (LLM 호출 안 된 경우)
      - C등급이고 LLM이 C 유지로 판단한 경우
    """
    if current_grade == "C":
        if not llm_called:
            return True
        if adjusted_grade == "C":
            return True
    return False


# ──────────────────────────────────────────────
# LangGraph 노드
# ──────────────────────────────────────────────
def supervisory_review_node(state: dict) -> dict:
    """LangGraph 노드 — B/C 등급만 처리하고 나머지는 패스."""
    current_grade  = state.get("loan_grade", "")
    gemini_api_key = state.get("gemini_api_key", "") or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    gemini_model   = state.get("gemini_model", "") or os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    company_name   = state.get("company_name", "")
    errors         = list(state.get("errors", []))

    # ── B, C 아니면 패스 ─────────────────────
    if current_grade not in ("B", "C"):
        logger.info("[Supervisory] %s — %s등급 패스", company_name, current_grade)
        return {
            "supervisory_result": {
                "original_grade": current_grade,
                "special_cases":  [],
                "llm_called":     False,
                "adjusted_grade": current_grade,
                "reason":         "B/C 등급 아님 — 검토 생략",
            },
            "needs_human_review": False,
            "errors": errors,
        }

    logger.info("[Supervisory] %s — %s등급 검토 시작", company_name, current_grade)

    # ── special_case 감지 ────────────────────
    special_cases = _detect_special_cases(state)
    logger.info("[Supervisory] %s — 감지된 특이사항: %s", company_name, special_cases)

    # ── special_case 없는 경우 ───────────────
    if not special_cases:
        needs_review = current_grade == "C"  # C는 Human Review, B는 자동 승인
        reason       = (
            "특이사항 없음 — Human Review 전달" if needs_review
            else "특이사항 없음 — 자동 승인"
        )
        logger.info("[Supervisory] %s — %s", company_name, reason)
        return {
            "supervisory_result": {
                "original_grade": current_grade,
                "special_cases":  [],
                "llm_called":     False,
                "adjusted_grade": current_grade,
                "reason":         reason,
            },
            "needs_human_review": needs_review,
            "errors": errors,
        }

    # ── special_case 있는 경우 → LLM 판단 (재시도 포함) ───
    adjusted_grade, reason, is_error = _llm_judge_with_retry(
        state, current_grade, special_cases,
        gemini_api_key, gemini_model, errors,
    )

    # 오류 발생 시 → 재시작 또는 Human Review 강제 전달
    if is_error:
        restart_count = state.get("restart_count", 0)

        # 재시작 횟수 1회 미만 → 전체 재분석 요청
        if restart_count < 1:
            logger.warning(
                "[Supervisory] %s — 오류 발생, 전체 재분석 요청 (restart_count: %d)",
                company_name, restart_count,
            )
            errors.append(
                f"Supervisory: LLM 판단 실패 — 전체 재분석 요청 "
                f"(restart_count: {restart_count})"
            )
            return {
                "supervisory_result": {
                    "original_grade": current_grade,
                    "special_cases":  special_cases,
                    "llm_called":     True,
                    "adjusted_grade": current_grade,
                    "reason":         reason,
                    "is_error":       True,
                },
                "restart_required": True,        # 그래프 엣지가 planner로 이동
                "restart_count":    restart_count + 1,
                "needs_human_review": False,
                "errors": errors,
            }

        # 재시작 횟수 1회 이상 → 진짜 오류, Human Review 강제 전달
        logger.error(
            "[Supervisory] %s — 재시작 후에도 오류, Human Review 강제 전달", company_name
        )
        errors.append(
            f"Supervisory: 재시작 후에도 LLM 판단 실패 — Human Review 강제 전달"
        )
        return {
            "supervisory_result": {
                "original_grade": current_grade,
                "special_cases":  special_cases,
                "llm_called":     True,
                "adjusted_grade": current_grade,
                "reason":         reason,
                "is_error":       True,
            },
            "restart_required":   False,
            "needs_human_review": True,    # 강제 Human Review
            "errors": errors,
        }

    needs_review = _needs_human_review(
        current_grade, adjusted_grade,
        special_cases, llm_called=True,
    )

    logger.info(
        "[Supervisory] %s — %s → %s | Human Review: %s | 근거: %s",
        company_name, current_grade, adjusted_grade, needs_review, reason,
    )

    return {
        "loan_grade": adjusted_grade,
        "supervisory_result": {
            "original_grade": current_grade,
            "special_cases":  special_cases,
            "llm_called":     True,
            "adjusted_grade": adjusted_grade,
            "reason":         reason,
            "is_error":       False,
        },
        "needs_human_review": needs_review,
        "errors": errors,
    }