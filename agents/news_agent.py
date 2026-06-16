"""News Agent — Naver 검색 API 뉴스 수집 및 리스크 점수 산출.

흐름:
  1. 네이버 뉴스 API로 기사 수집
  2. 키워드 매칭으로 1차 점수 계산 (Recency Decay 적용)
  3. LLM으로 맥락 기반 점수 계산
  4. 키워드 히트 수에 따라 가중 평균으로 최종 점수 산출
  5. State에 저장
"""
from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple

import requests
from models.schemas import NewsResult

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 키워드 사전
# ──────────────────────────────────────────────
NEG_HIGH: List[str] = [
    "임상 실패", "임상실패",
    "FDA 거절", "FDA거절",
    "식약처 제재",
    "감사의견 거절",
    "상장폐지",
    "횡령", "배임",
    "허가 취소", "허가취소",
]

NEG_MID: List[str] = [
    "임상 지연", "임상지연",
    "기술수출 해지", "계약 해지",
    "소송",
    "매출 감소",
    "영업 손실 확대",
]

POS: List[str] = [
    "FDA 승인", "FDA승인",
    "임상 성공", "임상성공",
    "기술수출",
    "특허 취득",
    "품목허가",
    "승인 완료",
]

CONFIRM: List[str] = [
    "임상 계획", "MOU", "투자 유치", "연구 발표",
]


# ──────────────────────────────────────────────
# 네이버 뉴스 API 수집
# ──────────────────────────────────────────────
def search_naver_news(
    company_name: str,
    client_id: str,
    client_secret: str,
    max_articles: int = 30,
) -> List[Dict]:
    """네이버 검색 API로 기업 관련 뉴스를 수집한다."""
    articles: List[Dict] = []
    start = 1
    per_page = 100  # API 최대값

    while len(articles) < max_articles:
        params = {
            "query": f"{company_name} 바이오 임상",
            "sort":  "date",
            "display": min(per_page, max_articles - len(articles)),
            "start": start,
        }
        headers = {
            "X-Naver-Client-Id":     client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        try:
            resp = requests.get(
                "https://openapi.naver.com/v1/search/news.json",
                params=params,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning("[News] 네이버 API 요청 실패: %s", e)
            break

        items = data.get("items", [])
        if not items:
            break

        articles.extend(items)
        start += len(items)

        # 네이버 API 최대 1000건 제한
        if start > 1000 or len(items) < per_page:
            break

    logger.info("[News] %s — %d건 수집", company_name, len(articles))
    return articles[:max_articles]


# ──────────────────────────────────────────────
# Recency Decay 계산
# ──────────────────────────────────────────────
def _days_ago(pub_date_str: str) -> float:
    """네이버 API pubDate 문자열을 파싱해 오늘과의 일수 차이를 반환."""
    if not pub_date_str:
        return 30.0  # 날짜 없으면 30일 전으로 간주
    try:
        dt = parsedate_to_datetime(pub_date_str)
        delta = datetime.now(tz=dt.tzinfo) - dt
        return max(0.0, delta.days)
    except Exception:
        return 30.0


def _recency_weight(pub_date_str: str) -> float:
    """발행일 기반 지수 감쇠 가중치 (30일 지나면 약 0.4배)."""
    days = _days_ago(pub_date_str)
    return math.exp(-0.03 * days)


# ──────────────────────────────────────────────
# 1단계 — 키워드 매칭 점수
# ──────────────────────────────────────────────
def _keyword_score(
    articles: List[Dict],
) -> Tuple[float, int, Dict]:
    """
    키워드 매칭 기반 점수 계산.

    Returns:
        score      : 0~100
        hits       : 키워드 히트 총 횟수
        detail     : 히트된 키워드 목록
    """
    score = 55.0
    hits  = 0
    detail: Dict = {
        "neg_high":  [],
        "neg_mid":   [],
        "positives": [],
        "confirms":  [],
    }

    for art in articles:
        text   = art.get("title", "") + " " + art.get("description", "")
        weight = _recency_weight(art.get("pubDate", ""))

        for kw in NEG_HIGH:
            if kw in text:
                score -= 15 * weight
                hits  += 1
                detail["neg_high"].append(kw)

        for kw in NEG_MID:
            if kw in text:
                score -= 8 * weight
                hits  += 1
                detail["neg_mid"].append(kw)

        for kw in POS:
            if kw in text:
                score += 10 * weight
                hits  += 1
                detail["positives"].append(kw)

        for kw in CONFIRM:
            if kw in text:
                score += 3 * weight
                detail["confirms"].append(kw)

    # 중복 제거
    for k in detail:
        detail[k] = list(set(detail[k]))

    return max(0.0, min(100.0, score)), hits, detail


# ──────────────────────────────────────────────
# 2단계 — LLM 맥락 분석 점수
# ──────────────────────────────────────────────
def _llm_score(
    articles: List[Dict],
    company_name: str,
    openai_api_key: str,
    openai_model: str,
) -> Tuple[Optional[float], str]:
    """
    LLM 기반 맥락 분석 점수.

    Returns:
        score   : 0~100 또는 None (실패 시)
        summary : 분석 요약 문장
    """
    if not articles or not openai_api_key:
        return None, ""

    headlines = "\n".join(
        f"- [{art.get('pubDate', '')[:16]}] {art.get('title', '')}"
        for art in articles[:15]
    )

    prompt = (
        f"다음은 '{company_name}'의 최근 뉴스 헤드라인입니다:\n"
        f"{headlines}\n\n"
        "은행 여신 심사 담당자 관점에서 이 기업의 대출 리스크를 분석하세요.\n"
        "키워드가 아닌 전체 맥락을 바탕으로 판단하세요.\n\n"
        "다른 텍스트 없이 JSON만 출력하세요:\n"
        "{\n"
        '  "score": 0에서 100 사이 숫자 (100이 가장 안전),\n'
        '  "summary": "주요 리스크와 긍정 요인을 2~3문장으로 요약"\n'
        "}"
    )

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=openai_model,
            openai_api_key=openai_api_key,
            temperature=0.1,
            streaming=True,
        )

        print(f"\n[News LLM Streaming] {company_name} analysis start", flush=True)
        content_parts: List[str] = []
        for chunk in llm.stream(prompt):
            token = chunk.content or ""
            if token:
                print(token, end="", flush=True)
                content_parts.append(token)
        print(f"\n[News LLM Streaming] {company_name} analysis end\n", flush=True)

        content = "".join(content_parts).strip()

        # ```json ... ``` 형식 대응
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        parsed  = json.loads(content)
        score   = float(parsed["score"])
        summary = parsed.get("summary", "")

        return max(0.0, min(100.0, score)), summary

    except Exception as e:
        logger.warning("[News] LLM 분석 실패: %s", e)
        return None, ""


# ──────────────────────────────────────────────
# 3단계 — 가중 평균 병합
# ──────────────────────────────────────────────
def _merge_scores(
    keyword_score: float,
    llm_score: Optional[float],
    keyword_hits: int,
) -> float:
    """
    키워드 히트 수에 따라 키워드 점수와 LLM 점수를 가중 평균으로 병합.

    - 키워드 히트 3건 이상 : 키워드 신뢰 (7:3)
    - 키워드 히트 1~2건    : 반반 (5:5)
    - 키워드 히트 없음     : LLM 신뢰 (3:7)
    - LLM 실패             : 키워드 점수만 사용
    """
    if llm_score is None:
        return keyword_score

    if keyword_hits >= 3:
        w_kw, w_llm = 0.7, 0.3
    elif keyword_hits >= 1:
        w_kw, w_llm = 0.5, 0.5
    else:
        w_kw, w_llm = 0.3, 0.7

    return round(keyword_score * w_kw + llm_score * w_llm, 2)


# ──────────────────────────────────────────────
# 메인 점수 계산
# ──────────────────────────────────────────────
def calculate_news_score(
    articles: List[Dict],
    company_name: str,
    openai_api_key: str = "",
    openai_model: str   = "gpt-5.4-mini",
) -> Tuple[float, Dict, str]:
    """
    전체 뉴스 점수 계산 파이프라인.

    Returns:
        final_score : 0~100
        detail      : 키워드 히트 상세 정보
        llm_summary : LLM 분석 요약 문장
    """
    keyword_score, keyword_hits, detail = _keyword_score(articles)
    llm_score_val, llm_summary          = _llm_score(
        articles, company_name, openai_api_key, openai_model
    )
    final_score = _merge_scores(keyword_score, llm_score_val, keyword_hits)

    detail["article_count"]   = len(articles)
    detail["keyword_score"]   = round(keyword_score, 2)
    detail["llm_score"]       = llm_score_val
    detail["keyword_hits"]    = keyword_hits
    detail["merge_weights"]   = (
        "7:3" if keyword_hits >= 3 else
        "5:5" if keyword_hits >= 1 else
        "3:7"
    )

    logger.info(
        "[News] %s — 키워드: %.1f (히트 %d) | LLM: %s | 최종: %.1f",
        company_name, keyword_score, keyword_hits,
        f"{llm_score_val:.1f}" if llm_score_val is not None else "N/A",
        final_score,
    )

    return final_score, detail, llm_summary


# ──────────────────────────────────────────────
# LangGraph 노드
# ──────────────────────────────────────────────
def news_node(state: dict) -> dict:
    """LangGraph 노드 — State에서 읽고 결과를 State에 저장."""
    company_name    = state["company_name"]
    naver_id        = state.get("naver_client_id", "") or os.environ.get("NAVER_NEWS_API_Client_ID", "").strip()
    naver_secret    = state.get("naver_client_secret", "") or os.environ.get("NAVER_NEWS_API_Client_Secret", "").strip()
    openai_api_key  = state.get("openai_api_key", "") or os.environ.get("OPENAI_API_KEY", "")
    openai_model    = state.get("openai_model", "") or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    errors          = list(state.get("errors", []))

    logger.info("[News] %s 분석 시작", company_name)

    # ── 뉴스 수집 ──────────────────────────────
    news_data: List[Dict] = []

    if naver_id and naver_secret:
        try:
            news_data = search_naver_news(
                company_name, naver_id, naver_secret, max_articles=30
            )
        except Exception as e:
            errors.append(f"News: 네이버 API 오류 — {e}")
    else:
        errors.append("News: NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정")

    # ── 뉴스 0건 처리 ─────────────────────────
    if not news_data:
        logger.warning("[News] %s — 수집된 뉴스 없음", company_name)
        return {
            "news_result":  NewsResult(
                news_score=None,
                positive_keywords=[],
                negative_keywords=[],
                negative_critical_event=False,
                missing_news=True,
                keyword_score=None,
                keyword_hits=0,
                llm_score=None,
                llm_summary="",
                merge_weights="",
            ),
            "news_data":    [],
            "news_score":   None,   # SupervisoryReviewAgent가 news_data_missing으로 처리
            "news_detail":  {"article_count": 0},
            "news_summary": "",
            "errors":       errors + ["News: 수집된 뉴스 없음"],
        }

    # ── 점수 계산 ─────────────────────────────
    final_score, detail, llm_summary = calculate_news_score(
        news_data, company_name, openai_api_key, openai_model
    )

    negative_keywords = list({*detail.get("neg_high", []), *detail.get("neg_mid", [])})
    news_result = NewsResult(
        news_score=final_score,
        positive_keywords=detail.get("positives", []),
        negative_keywords=negative_keywords,
        negative_critical_event=bool(detail.get("neg_high", [])),
        missing_news=False,
        keyword_score=detail.get("keyword_score"),
        keyword_hits=detail.get("keyword_hits", 0),
        llm_score=detail.get("llm_score"),
        llm_summary=llm_summary,
        merge_weights=detail.get("merge_weights", ""),
    )

    return {
        "news_result":  news_result,
        "news_data":    news_data,
        "news_score":   final_score,
        "news_detail":  detail,
        "news_summary": llm_summary,
        "errors":       errors,
    }
