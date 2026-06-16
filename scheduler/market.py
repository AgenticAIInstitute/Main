"""Market Agent — 바이오 산업 환경 분석 및 시장 보정값 산출.

역할:
  - 주 1회 독립 실행 (LangGraph 그래프 밖)
  - 바이오 산업 관련 뉴스 수집 → LLM 종합 판단 → JSON 파일에 저장
  - 기업 분석 시 저장된 값을 읽어서 산업/시장 보정 10%에 반영

구성:
  update_market_score() — 주 1회 실행, 산업 점수 갱신
  load_market_score()   — 기업 분석 시 호출, 저장된 점수 반환
  run_scheduler()       — 매주 월요일 자동 실행 스케줄러
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

CACHE_FILE    = "market_score_cache.json"
STALE_DAYS    = 7       # 이 기간 이상 미갱신이면 errors에 기록
DEFAULT_SCORE = 70.0    # 캐시 없거나 오류 시 기본값

# 산업 환경 분석용 검색 키워드
MARKET_KEYWORDS = [
    "바이오 산업",
    "제약 규제",
    "FDA 정책",
    "바이오 투자",
    "신약 허가",
    "식약처 정책",
]


# ──────────────────────────────────────────────
# 뉴스 수집
# ──────────────────────────────────────────────
def _collect_industry_news(
    client_id: str,
    client_secret: str,
    max_per_keyword: int = 20,
) -> List[Dict]:
    """키워드별로 바이오 산업 뉴스를 수집한다."""
    articles = []
    seen_titles = set()

    for keyword in MARKET_KEYWORDS:
        params = {
            "query":   keyword,
            "sort":    "date",
            "display": max_per_keyword,
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
            items = resp.json().get("items", [])

            for item in items:
                title = item.get("title", "")
                if title not in seen_titles:
                    seen_titles.add(title)
                    articles.append(item)

        except Exception as e:
            logger.warning("[Market] 뉴스 수집 실패 (키워드: %s): %s", keyword, e)

    logger.info("[Market] 산업 뉴스 %d건 수집", len(articles))
    return articles


# ──────────────────────────────────────────────
# LLM 산업 환경 분석
# ──────────────────────────────────────────────
def _llm_analyze_industry(
    articles: List[Dict],
    openai_api_key: str,
    openai_model: str,
) -> Tuple[Optional[float], str, List[str], List[str]]:
    """
    LLM으로 바이오 산업 환경을 분석한다.

    Returns:
        score    : 0~100 (100이 가장 우호적인 산업 환경)
        summary  : 2~3문장 요약
        positive : 긍정 요인 목록
        negative : 부정 요인 목록
    """
    if not articles or not openai_api_key:
        return None, "", [], []

    headlines = "\n".join(
        f"- [{art.get('pubDate', '')[:16]}] {art.get('title', '')}"
        for art in articles[:30]
    )

    prompt = (
        "당신은 바이오 산업 전문 애널리스트입니다.\n"
        "아래 바이오 산업 관련 뉴스를 읽고 현재 산업 환경을 평가하세요.\n\n"
        f"[수집된 뉴스]\n{headlines}\n\n"
        "여신 심사 관점에서 바이오 기업 전반의 대출 리스크를 평가하세요.\n"
        "개별 기업이 아닌 산업 전체 환경을 판단하세요.\n\n"
        "다른 텍스트 없이 JSON만 출력하세요:\n"
        "{\n"
        '  "score": 0~100 숫자 (100이 가장 우호적인 산업 환경),\n'
        '  "summary": "2~3문장 요약",\n'
        '  "positive": ["긍정 요인1", "긍정 요인2"],\n'
        '  "negative": ["부정 요인1", "부정 요인2"]\n'
        "}"
    )

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=openai_model,
            openai_api_key=openai_api_key,
            temperature=0.1,
        )
        result  = llm.invoke(prompt)
        content = result.content.strip()

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]

        parsed   = json.loads(content)
        score    = max(0.0, min(100.0, float(parsed["score"])))
        summary  = parsed.get("summary", "")
        positive = parsed.get("positive", [])
        negative = parsed.get("negative", [])

        return score, summary, positive, negative

    except Exception as e:
        logger.warning("[Market] LLM 분석 실패: %s", e)
        return None, "", [], []


# ──────────────────────────────────────────────
# 캐시 저장
# ──────────────────────────────────────────────
def _save_cache(
    score: float,
    summary: str,
    positive: List[str],
    negative: List[str],
) -> None:
    """분석 결과를 JSON 파일에 저장한다."""
    data = {
        "score":      score,
        "updated_at": datetime.now().isoformat(),
        "summary":    summary,
        "detail": {
            "positive": positive,
            "negative": negative,
        },
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("[Market] 캐시 저장 완료 — score: %.1f", score)


# ──────────────────────────────────────────────
# 산업 점수 갱신 (주 1회 실행)
# ──────────────────────────────────────────────
def update_market_score(
    naver_client_id: str     = "",
    naver_client_secret: str = "",
    openai_api_key: str      = "",
    openai_model: str        = "gpt-5.4-mini",
) -> None:
    """
    바이오 산업 환경을 분석하고 캐시를 갱신한다.
    주 1회 스케줄러에서 자동 호출.
    """
    # 환경변수 fallback
    naver_client_id = (
        naver_client_id
        or os.getenv("NAVER_CLIENT_ID", "")
        or os.getenv("NAVER_NEWS_API_Client_ID", "")
    )
    naver_client_secret = (
        naver_client_secret
        or os.getenv("NAVER_CLIENT_SECRET", "")
        or os.getenv("NAVER_NEWS_API_Client_Secret", "")
    )
    openai_api_key      = openai_api_key      or os.getenv("OPENAI_API_KEY", "")
    openai_model        = openai_model        or os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

    logger.info("[Market] 산업 환경 분석 시작 — %s", datetime.now().isoformat())

    # 1) 뉴스 수집
    articles = _collect_industry_news(naver_client_id, naver_client_secret)

    if not articles:
        logger.warning("[Market] 수집된 뉴스 없음 — 기본값 %.1f 사용", DEFAULT_SCORE)
        _save_cache(DEFAULT_SCORE, "뉴스 수집 실패 — 기본값 사용", [], [])
        return

    # 2) LLM 분석
    score, summary, positive, negative = _llm_analyze_industry(
        articles, openai_api_key, openai_model
    )

    if score is None:
        logger.warning("[Market] LLM 분석 실패 — 기본값 %.1f 사용", DEFAULT_SCORE)
        _save_cache(DEFAULT_SCORE, "LLM 분석 실패 — 기본값 사용", [], [])
        return

    # 3) 캐시 저장
    _save_cache(score, summary, positive, negative)
    logger.info("[Market] 갱신 완료 — score: %.1f", score)


# ──────────────────────────────────────────────
# 산업 점수 로드 (기업 분석 시 호출)
# ──────────────────────────────────────────────
def load_market_score(errors: list) -> float:
    """
    저장된 산업 점수를 읽어서 반환한다.
    Risk Scoring Agent에서 호출.

    7일 이상 미갱신이면 errors에 기록하고 기본값 반환.
    파일 없거나 오류 시 errors에 기록하고 기본값 반환.
    """
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        updated_at = datetime.fromisoformat(data["updated_at"])
        days_old   = (datetime.now() - updated_at).days

        # 7일 이상 미갱신
        if days_old > STALE_DAYS:
            errors.append(
                f"Market: 산업/시장 보정값이 {days_old}일째 미갱신 "
                f"(마지막 갱신: {data['updated_at']}) "
                f"— 기본값 {DEFAULT_SCORE} 사용"
            )
            logger.warning(
                "[Market] %d일째 미갱신 — 기본값 %.1f 사용", days_old, DEFAULT_SCORE
            )
            return DEFAULT_SCORE

        logger.info(
            "[Market] 캐시 로드 — score: %.1f (갱신: %s)",
            data["score"], data["updated_at"]
        )
        return float(data["score"])

    except FileNotFoundError:
        errors.append(
            f"Market: {CACHE_FILE} 없음 — Market Agent가 아직 실행되지 않았습니다 "
            f"— 기본값 {DEFAULT_SCORE} 사용"
        )
        logger.warning("[Market] 캐시 파일 없음 — 기본값 %.1f 사용", DEFAULT_SCORE)
        return DEFAULT_SCORE

    except Exception as e:
        errors.append(
            f"Market: 캐시 파일 읽기 오류 ({e}) "
            f"— 기본값 {DEFAULT_SCORE} 사용"
        )
        logger.warning("[Market] 캐시 읽기 오류: %s — 기본값 %.1f 사용", e, DEFAULT_SCORE)
        return DEFAULT_SCORE


# ──────────────────────────────────────────────
# 스케줄러 (별도 프로세스로 실행)
# ──────────────────────────────────────────────
def run_scheduler() -> None:
    """
    매주 월요일 오전 9시에 update_market_score를 자동 실행한다.
    별도 터미널에서 `python -m biocredit.agents.market` 으로 실행.
    """
    try:
        import schedule
        import time
    except ImportError:
        raise ImportError("schedule 라이브러리 필요: pip install schedule")

    logger.info("[Market] 스케줄러 시작 — 매주 월요일 09:00 실행")

    schedule.every().monday.at("09:00").do(update_market_score)

    # 시작 시 한 번 즉시 실행 (캐시 없을 때 대비)
    if not os.path.exists(CACHE_FILE):
        logger.info("[Market] 캐시 없음 — 즉시 실행")
        update_market_score()

    while True:
        schedule.run_pending()
        time.sleep(60)


# ──────────────────────────────────────────────
# 직접 실행
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_scheduler()
