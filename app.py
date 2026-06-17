from __future__ import annotations

import asyncio
import logging
import os
import sys
from html import escape
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from langgraph.graph import END, StateGraph

from agents import (
    BioDomainAgent,
    DisclosureAgent,
    FinancialAgent,
    LoanDecisionAgent,
    ReportWriterAgent,
    RiskScoringAgent,
    news_node as _news_node_fn,
    planner_node as _planner_node_fn,
    supervisory_review_node,
)
from data.company_loader import build_companies_by_id, load_companies
from models.schemas import BioAgentState, CompanyReport, GradeEnum, NewsResult, SupervisoryResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

_financial = FinancialAgent()
_bio = BioDomainAgent()
_disclosure = DisclosureAgent()
_risk = RiskScoringAgent()
_loan = LoanDecisionAgent()
_report = ReportWriterAgent()


def planner_node(state: dict) -> dict:
    s = BioAgentState(**state)
    adapted = dict(state)
    adapted["company_data"] = s.company_data
    result = _planner_node_fn(adapted)

    if state.get("restart_required", False):
        s.financial_result = None
        s.news_result = None
        s.bio_domain_result = None
        s.disclosure_result = None
        s.risk_score_result = None
        s.supervisory_result = None
        s.loan_decision_result = None
        s.report = None

    s.restart_required = result.get("restart_required") or False
    s.restart_count = result.get("restart_count") or s.restart_count
    s.needs_human_review = result.get("needs_human_review") or False
    s.errors = result.get("errors") or list(s.errors)
    return s.model_dump()


def financial_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _financial.run(s).model_dump()


def news_node(state: dict) -> dict:
    s = BioAgentState(**state)
    flat = {
        "company_name": s.company_data.company_name,
        "naver_client_id": os.environ.get("NAVER_CLIENT_ID", "").strip()
        or os.environ.get("NAVER_NEWS_API_Client_ID", "").strip(),
        "naver_client_secret": os.environ.get("NAVER_CLIENT_SECRET", "").strip()
        or os.environ.get("NAVER_NEWS_API_Client_Secret", "").strip(),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", "").strip(),
        "openai_model": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini").strip(),
        "errors": list(s.errors),
    }
    result = _news_node_fn(flat)
    news_result = result.get("news_result")
    if isinstance(news_result, dict):
        news_result = NewsResult(**news_result)

    detail = result.get("news_detail", {})
    negative_keywords = list({*detail.get("neg_high", []), *detail.get("neg_mid", [])})
    s.news_result = news_result or NewsResult(
        news_score=result.get("news_score"),
        positive_keywords=detail.get("positives", []),
        negative_keywords=negative_keywords,
        negative_critical_event=bool(detail.get("neg_high", [])),
        missing_news=result.get("news_score") is None,
        keyword_score=detail.get("keyword_score"),
        keyword_hits=detail.get("keyword_hits", 0),
        llm_score=detail.get("llm_score"),
        llm_summary=result.get("news_summary", ""),
        merge_weights=detail.get("merge_weights", ""),
    )
    s.errors = result.get("errors", list(s.errors))
    return s.model_dump()


def bio_domain_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _bio.run(s).model_dump()


def disclosure_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _disclosure.run(s).model_dump()


def risk_scoring_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _risk.run(s).model_dump()


def supervisory_node(state: dict) -> dict:
    s = BioAgentState(**state)
    disc_score_map = {"LOW": 100.0, "MEDIUM": 60.0, "HIGH": 20.0}
    disc_level = s.disclosure_result.disclosure_risk_level.value if s.disclosure_result else "MEDIUM"
    flat = {
        "company_name": s.company_data.company_name,
        "openai_api_key": os.environ.get("OPENAI_API_KEY", "").strip(),
        "openai_model": os.environ.get("OPENAI_MODEL", "gpt-5.4-mini").strip(),
        "loan_grade": s.risk_score_result.grade.value if s.risk_score_result else "",
        "financial_score": s.financial_result.financial_score if s.financial_result else None,
        "news_score": s.news_result.news_score if s.news_result else None,
        "bio_domain_score": s.bio_domain_result.bio_domain_score if s.bio_domain_result else None,
        "bio_score": s.bio_domain_result.bio_domain_score if s.bio_domain_result else None,
        "disclosure_score": disc_score_map.get(disc_level, 60.0),
        "news_detail": {"neg_high": s.news_result.negative_keywords if s.news_result else []},
        "news_summary": s.news_result.llm_summary if s.news_result else "",
        "restart_count": s.restart_count,
        "errors": list(s.errors),
    }
    result = supervisory_review_node(flat)
    s.restart_required = result.get("restart_required", False)
    s.restart_count = result.get("restart_count", s.restart_count)
    s.needs_human_review = result.get("needs_human_review", False)
    s.errors = result.get("errors", list(s.errors))
    sup = result.get("supervisory_result", {})
    if sup:
        s.supervisory_result = SupervisoryResult(
            special_case=bool(sup.get("special_cases", [])),
            special_case_reason=sup.get("reason", ""),
            flags=sup.get("special_cases", []),
            original_grade=sup.get("original_grade"),
            adjusted_grade=sup.get("adjusted_grade"),
            llm_called=sup.get("llm_called", False),
            is_error=sup.get("is_error", False),
        )
    adjusted = result.get("loan_grade")
    if adjusted and s.risk_score_result:
        s.risk_score_result.grade = GradeEnum(adjusted)
    return s.model_dump()


def loan_decision_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _loan.run(s).model_dump()


def report_writer_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _report.run(s).model_dump()


def _route_after_supervisory(state: dict) -> str:
    if state.get("restart_required", False):
        return "planner"
    return "loan_decision"


def _build_graph() -> Any:
    graph = StateGraph(dict)
    graph.add_node("planner", planner_node)
    graph.add_node("financial", financial_node)
    graph.add_node("news", news_node)
    graph.add_node("bio_domain", bio_domain_node)
    graph.add_node("disclosure", disclosure_node)
    graph.add_node("risk_scoring", risk_scoring_node)
    graph.add_node("supervisory", supervisory_node)
    graph.add_node("loan_decision", loan_decision_node)
    graph.add_node("report_writer", report_writer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "financial")
    graph.add_edge("financial", "news")
    graph.add_edge("news", "bio_domain")
    graph.add_edge("bio_domain", "disclosure")
    graph.add_edge("disclosure", "risk_scoring")
    graph.add_edge("risk_scoring", "supervisory")
    graph.add_conditional_edges(
        "supervisory",
        _route_after_supervisory,
        {"planner": "planner", "loan_decision": "loan_decision"},
    )
    graph.add_edge("loan_decision", "report_writer")
    graph.add_edge("report_writer", END)
    return graph.compile()


_pipeline = _build_graph()
_REPORTS: dict[str, CompanyReport] = {}
_COMPANIES = []
COMPANIES_BY_ID = {}
_analysis_started = False
_analysis_task_generation = 0


def analyze_company(company_data: Any) -> CompanyReport:
    initial_state = BioAgentState(company_data=company_data).model_dump()
    final_state = _pipeline.invoke(initial_state)
    result = BioAgentState(**final_state)
    if result.report is None:
        raise RuntimeError(f"analysis failed: {company_data.company_id}")
    return result.report


def _run_all_analyses(generation: int) -> None:
    global _COMPANIES, COMPANIES_BY_ID, _analysis_started, _analysis_task_generation
    _COMPANIES = load_companies()
    COMPANIES_BY_ID = build_companies_by_id(_COMPANIES)
    _REPORTS.clear()

    logger.info("KOSDAQ bio top company analysis started (%d companies)", len(_COMPANIES))
    try:
        for company in _COMPANIES:
            if generation != _analysis_task_generation:
                logger.info("KOSDAQ bio analysis superseded by new run (%d/%d complete)", len(_REPORTS), len(_COMPANIES))
                break
            try:
                report = analyze_company(company)
                _REPORTS[company.company_id] = report
                logger.info(
                    "analysis complete: %s -> %s (%s)",
                    company.company_name,
                    report.grade,
                    report.final_decision,
                )
            except Exception as exc:
                logger.error("analysis failed [%s]: %s", company.company_id, exc)
    finally:
        if generation == _analysis_task_generation:
            _analysis_started = False


app = FastAPI(title="BioCredit Agent", version="1.0.0")


@app.on_event("startup")
async def startup_analyses() -> None:
    logger.info("[Startup] server ready; analysis waits for the dashboard start button")


def _start_analysis_task() -> bool:
    global _analysis_started, _analysis_task_generation
    _analysis_task_generation += 1
    _analysis_started = True
    asyncio.create_task(asyncio.to_thread(_run_all_analyses, _analysis_task_generation))
    return True


DECISION_COLOR = {
    "APPROVED": "#27ae60",
    "REJECTED": "#e74c3c",
    "HUMAN_IN_THE_LOOP": "#e67e22",
}
DECISION_LABEL = {
    "APPROVED": "승인",
    "REJECTED": "부결",
    "HUMAN_IN_THE_LOOP": "전문가 검토",
}
GRADE_COLOR = {
    "A": "#1f7a4f",
    "B": "#2f80c7",
    "C": "#e09f2f",
    "D": "#d95f3d",
    "E": "#8f2d2d",
}


def _fmt_score(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "없음"


def _safe_join(items: list[str]) -> str:
    return ", ".join(items) if items else "없음"


def _market_cap_text(value: float | None) -> str:
    return f"{value:,.0f}억원" if value else "N/A"



@app.get("/", response_class=HTMLResponse)
async def main_page() -> HTMLResponse:
    reports = sorted(_REPORTS.values(), key=lambda report: report.final_score, reverse=True)
    main_reports = [
        report
        for report in reports
        if report.grade.value in {"A", "B", "C"} and report.final_decision.value != "REJECTED"
    ]
    rejected_reports = [
        report
        for report in reports
        if report.grade.value not in {"A", "B", "C"} or report.final_decision.value == "REJECTED"
    ]
    rows = ""
    rejected_rows = ""
    panels = ""

    def render_row(report: CompanyReport, compact: bool = False) -> str:
        company = COMPANIES_BY_ID.get(report.company_id)
        ticker = escape(company.ticker_code if company else report.company_id)
        industry = escape(company.industry_category if company else "N/A")
        market_cap = _market_cap_text(company.market_cap if company else None)
        news_str = _fmt_score(report.news_score)
        decision_label = DECISION_LABEL.get(report.final_decision.value, report.final_decision.value)
        decision_color = DECISION_COLOR.get(report.final_decision.value, "#555")
        grade_color = GRADE_COLOR.get(report.grade.value, "#555")
        special_text = "있음" if report.special_case else "없음"
        panel_id = f"news-{report.company_id}"

        if compact:
            return f'''
        <tr>
          <td><strong>{escape(report.company_name)}</strong><div class="muted mono">{ticker}</div></td>
          <td><span class="grade" style="background:{grade_color}">{report.grade.value}</span></td>
          <td class="num"><strong>{report.final_score:.1f}</strong></td>
          <td><span class="decision" style="background:{decision_color}">{decision_label}</span></td>
          <td><a class="btn-detail" href="/companies/{report.company_id}">상세</a></td>
        </tr>'''

        return f'''
        <tr>
          <td><strong>{escape(report.company_name)}</strong></td>
          <td class="mono">{ticker}</td>
          <td>{industry}</td>
          <td class="num">{market_cap}</td>
          <td class="num"><strong>{report.final_score:.1f}</strong></td>
          <td><span class="grade" style="background:{grade_color}">{report.grade.value}</span></td>
          <td class="num">{report.financial_score:.1f}</td>
          <td class="num"><button class="score-btn" type="button" data-panel="{panel_id}">{news_str}</button></td>
          <td class="num">{report.bio_score:.1f}</td>
          <td>{escape(report.disclosure_risk_level.value)}</td>
          <td>{special_text}</td>
          <td><span class="decision" style="background:{decision_color}">{decision_label}</span></td>
          <td><a class="btn-detail" href="/companies/{report.company_id}">상세보기</a></td>
        </tr>'''

    for report in main_reports:
        rows += render_row(report)
        panel_id = f"news-{report.company_id}"
        news_str = _fmt_score(report.news_score)
        positive = escape(_safe_join(report.news_positive_keywords))
        negative = escape(_safe_join(report.news_negative_keywords))
        llm_summary = escape(report.news_llm_summary or "없음")
        merge_weights = escape(report.news_merge_weights or "없음")
        critical = "감지됨" if report.news_negative_critical_event else "없음"
        panels += f'''
        <section id="{panel_id}" class="reason-panel">
          <div class="reason-title">{escape(report.company_name)} 뉴스 분석 해석</div>
          <div class="reason-grid">
            <div><span>뉴스 최종 점수</span><strong>{news_str}</strong></div>
            <div><span>키워드 점수</span><strong>{_fmt_score(report.news_keyword_score)}</strong></div>
            <div><span>LLM 점수</span><strong>{_fmt_score(report.news_llm_score)}</strong></div>
            <div><span>키워드 적중</span><strong>{report.news_keyword_hits}</strong></div>
          </div>
          <ul>
            <li><strong>긍정 키워드:</strong> {positive}</li>
            <li><strong>부정 키워드:</strong> {negative}</li>
            <li><strong>중대 부정 이벤트:</strong> {critical}</li>
            <li><strong>병합 가중치:</strong> {merge_weights}</li>
            <li><strong>LLM 요약:</strong> {llm_summary}</li>
          </ul>
        </section>'''

    for report in rejected_reports:
        rejected_rows += render_row(report, compact=True)

    if not rows:
        rows = '<tr><td colspan="13" class="empty">A/B/C 등급 기업이 아직 없습니다.</td></tr>'
    if not rejected_rows:
        rejected_rows = '<tr><td colspan="5" class="empty">부결 또는 D/E 등급 기업이 없습니다.</td></tr>'

    approved_count = sum(1 for report in reports if report.final_decision.value == "APPROVED")
    review_count = sum(1 for report in reports if report.final_decision.value == "HUMAN_IN_THE_LOOP")
    rejected_count = sum(1 for report in reports if report.final_decision.value == "REJECTED")
    total_companies = len(_COMPANIES) or int(os.getenv("KOSDAQ_TOP_LIMIT", "50"))

    html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BioCredit Agent - KOSDAQ Bio Top 50</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:'Segoe UI', Arial, sans-serif; background:#eef3f8; color:#253044; }}
  header {{ background:linear-gradient(135deg,#16345b 0%,#245c88 62%,#2d7c8f 100%); color:white; padding:28px 42px; box-shadow:0 3px 14px rgba(15,35,65,.18); }}
  header h1 {{ margin:0; font-size:1.9rem; letter-spacing:0; }}
  header p {{ margin:8px 0 0; opacity:.9; }}
  .action-panel {{ position:fixed; top:18px; right:22px; z-index:20; display:flex; align-items:center; gap:10px; background:white; color:#253044; border:1px solid #dbe5ef; border-radius:8px; padding:10px 12px; box-shadow:0 8px 24px rgba(23,43,77,.14); }}
  .action-panel span {{ font-size:.82rem; color:#607086; font-weight:700; }}
  .start-btn {{ border:0; background:#245c88; color:white; border-radius:6px; padding:9px 13px; font-weight:800; cursor:pointer; }}
  .start-btn:hover {{ background:#173f63; }}
  .container {{ max-width:none; margin:28px auto; padding:0 20px; }}
  .dashboard-grid {{ display:grid; grid-template-columns:minmax(0,1fr) 154px; gap:18px; align-items:start; transition:grid-template-columns .22s ease; }}
  .dashboard-grid.rejected-open {{ grid-template-columns:minmax(0,1fr) 410px; }}
  .card {{ background:white; border-radius:8px; box-shadow:0 2px 14px rgba(23,43,77,.1); overflow:hidden; border:1px solid #dde7f1; }}
  .card-header {{ display:flex; justify-content:space-between; align-items:center; gap:16px; padding:18px 24px; border-bottom:1px solid #e2e8f0; }}
  .card-header h2 {{ margin:0; font-size:1.08rem; }}
  .side-card {{ position:sticky; top:18px; width:100%; max-height:calc(100vh - 48px); z-index:5; transition:max-height .22s ease; }}
  .side-card.open {{ max-height:calc(100vh - 48px); }}
  .side-card .card-header {{ cursor:pointer; user-select:none; min-height:68px; }}
  .side-card .table-wrap {{ display:none; }}
  .side-card.open .table-wrap {{ display:block; max-height:calc(100vh - 145px); overflow:auto; }}
  .side-card:not(.open) .card-header {{ flex-direction:column; justify-content:center; align-items:center; gap:8px; padding:12px 10px; text-align:center; }}
  .side-card:not(.open) h2 {{ font-size:.86rem; line-height:1.3; }}
  .side-card:not(.open) .stats {{ justify-content:center; }}
  .side-card:not(.open) .stat {{ display:none; }}
  .stats {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .stat {{ background:#e8f3fb; color:#1e5b89; border-radius:6px; padding:7px 12px; font-size:.82rem; font-weight:700; }}
  .toggle-btn {{ border:1px solid #e2b8b8; background:#fff7f7; color:#9b1c1c; border-radius:5px; padding:7px 10px; font-weight:800; cursor:pointer; }}
  .toggle-btn::after {{ content:"열기"; }}
  .side-card.open .toggle-btn::after {{ content:"닫기"; }}
  .table-wrap {{ overflow-x:auto; }}
  table {{ width:100%; border-collapse:collapse; min-width:1180px; }}
  .side-card table {{ min-width:0; }}
  th {{ background:#f7fafc; color:#607086; text-align:left; padding:11px 12px; font-size:.79rem; border-bottom:2px solid #dce6f0; white-space:nowrap; }}
  td {{ padding:12px; border-bottom:1px solid #edf2f7; font-size:.86rem; vertical-align:middle; }}
  tr:hover td {{ background:#f7fbff; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .mono {{ font-family:Consolas, monospace; color:#4c5f76; }}
  .muted {{ color:#718096; font-size:.75rem; margin-top:3px; }}
  .grade {{ display:inline-block; min-width:28px; text-align:center; color:white; font-weight:800; border-radius:5px; padding:3px 9px; }}
  .decision {{ display:inline-block; color:white; border-radius:14px; padding:4px 10px; font-size:.78rem; font-weight:700; white-space:nowrap; }}
  .btn-detail {{ display:inline-block; background:#245c88; color:white; text-decoration:none; border-radius:5px; padding:6px 10px; font-size:.8rem; white-space:nowrap; }}
  .btn-detail:hover {{ background:#173f63; }}
  .score-btn {{ border:1px solid #8fc4e8; background:#e8f4fd; color:#174b73; border-radius:5px; padding:5px 9px; min-width:54px; cursor:pointer; font:inherit; font-weight:800; }}
  .score-btn:hover, .score-btn.active {{ background:#245c88; color:white; }}
  .empty {{ text-align:center; color:#718096; padding:34px; }}
  .reason-panel {{ display:none; margin-top:16px; background:#fbfdff; border:1px solid #cfddeb; border-radius:8px; padding:18px; box-shadow:0 1px 8px rgba(23,43,77,.06); }}
  .reason-panel.active {{ display:block; }}
  .reason-title {{ font-weight:800; color:#1e5b89; margin-bottom:12px; }}
  .reason-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(145px,1fr)); gap:10px; margin-bottom:12px; }}
  .reason-grid div {{ background:white; border:1px solid #e2e8f0; border-radius:6px; padding:10px; }}
  .reason-grid span {{ display:block; color:#718096; font-size:.76rem; margin-bottom:5px; }}
  .reason-panel ul {{ margin:0; padding-left:18px; line-height:1.72; }}
  @media (max-width:1180px) {{
    .dashboard-grid, .dashboard-grid.rejected-open {{ display:block; }}
    .side-card {{ position:static; width:100%; margin-top:16px; }}
    .side-card.open {{ width:100%; }}
    .action-panel {{ position:static; margin:16px 20px 0; justify-content:space-between; }}
  }}
  footer {{ text-align:center; color:#8da0b4; padding:22px; font-size:.8rem; }}
</style>
</head>
<body>
<header>
  <h1>BioCredit Agent</h1>
  <p>코스닥 바이오·제약 관련 업종 시가총액 상위 50개 기업 신용 분석 대시보드</p>
</header>
<div class="action-panel">
  <span id="analysis-state">{"분석 중" if _analysis_started else "대기 중"}</span>
  <button class="start-btn" id="start-analysis" type="button">분석 시작</button>
</div>
<div class="container">
  <div class="dashboard-grid" id="dashboard-grid">
    <div class="card">
      <div class="card-header">
        <h2>A/B/C 등급 기업 ({len(main_reports)}개, 점수 높은 순)</h2>
        <div class="stats">
          <span class="stat">분석 {len(reports)} / {total_companies}</span>
          <span class="stat">승인 {approved_count}</span>
          <span class="stat">검토 {review_count}</span>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>기업명</th><th>종목코드</th><th>시장/분류</th><th class="num">시가총액</th>
              <th class="num">최종점수</th><th>등급</th><th class="num">재무</th><th class="num">뉴스</th>
              <th class="num">바이오</th><th>공시</th><th>특이사항</th><th>판단</th><th>상세</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    <aside class="card side-card" id="rejected-card">
      <div class="card-header" id="rejected-toggle" role="button" tabindex="0" aria-expanded="false" aria-controls="rejected-panel">
        <h2>부결/D/E 등급 ({len(rejected_reports)}개)</h2>
        <div class="stats">
          <span class="stat" style="background:#fdf2f2;color:#9b1c1c">부결 {rejected_count}</span>
          <button class="toggle-btn" type="button" aria-label="부결 기업 목록 열기"></button>
        </div>
      </div>
      <div class="table-wrap" id="rejected-panel">
        <table>
          <thead>
            <tr><th>기업</th><th>등급</th><th class="num">점수</th><th>판단</th><th>상세</th></tr>
          </thead>
          <tbody>{rejected_rows}</tbody>
        </table>
      </div>
    </aside>
  </div>
  <div id="news-panels">{panels}</div>
</div>
<footer>BioCredit Agent v1.0 · KOSDAQ Bio Top 50 · FastAPI</footer>
<script>
  document.querySelectorAll('.score-btn').forEach((button) => {{
    button.addEventListener('click', () => {{
      const id = button.dataset.panel;
      const panel = document.getElementById(id);
      const wasActive = panel && panel.classList.contains('active');
      document.querySelectorAll('.reason-panel').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.score-btn').forEach((item) => item.classList.remove('active'));
      if (panel && !wasActive) {{
        panel.classList.add('active');
        button.classList.add('active');
        panel.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
      }}
    }});
  }});
  const rejectedCard = document.getElementById('rejected-card');
  const rejectedToggle = document.getElementById('rejected-toggle');
  const dashboardGrid = document.getElementById('dashboard-grid');
  if (rejectedCard && rejectedToggle) {{
    const setRejectedOpen = () => {{
      const isOpen = rejectedCard.classList.toggle('open');
      if (dashboardGrid) {{
        dashboardGrid.classList.toggle('rejected-open', isOpen);
      }}
      rejectedToggle.setAttribute('aria-expanded', String(isOpen));
    }};
    rejectedToggle.addEventListener('click', setRejectedOpen);
    rejectedToggle.addEventListener('keydown', (event) => {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        setRejectedOpen();
      }}
    }});
  }}
  const renderedCount = {len(reports)};
  const totalCompanies = {total_companies};
  const startButton = document.getElementById('start-analysis');
  const analysisState = document.getElementById('analysis-state');
  const applyAnalysisStatus = (status) => {{
    const running = Boolean(status.analysis_started);
    if (analysisState) {{
      analysisState.textContent = running ? '분석 중' : '대기 중';
    }}
  }};
  if (startButton) {{
    startButton.addEventListener('click', async () => {{
      if (analysisState) {{
        analysisState.textContent = '분석 시작 중';
      }}
      try {{
        const response = await fetch('/api/start', {{ method: 'POST', cache: 'no-store' }});
        const status = await response.json();
        applyAnalysisStatus(status);
        window.setTimeout(() => window.location.reload(), 1000);
      }} catch (error) {{
        if (analysisState) {{
          analysisState.textContent = '시작 실패';
        }}
        console.warn('analysis start failed', error);
      }}
    }});
  }}
  window.setInterval(async () => {{
    try {{
      const response = await fetch('/api/status', {{ cache: 'no-store' }});
      const status = await response.json();
      applyAnalysisStatus(status);
      if (status.completed > renderedCount) {{
        window.location.reload();
      }}
    }} catch (error) {{
      console.warn('status refresh failed', error);
    }}
  }}, 3000);
</script>
</body>
</html>'''
    return HTMLResponse(content=html)


@app.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(company_id: str) -> HTMLResponse:
    report = _REPORTS.get(company_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Company ID '{company_id}' not found.")

    company = COMPANIES_BY_ID.get(company_id)
    ticker = escape(company.ticker_code if company else "N/A")
    industry = escape(company.industry_category if company else "N/A")
    market_cap = _market_cap_text(company.market_cap if company else None)
    news_str = _fmt_score(report.news_score)
    decision_label = DECISION_LABEL.get(report.final_decision.value, report.final_decision.value)
    grade_color = GRADE_COLOR.get(report.grade.value, "#555")
    report_html = escape(report.report_text).replace("\n", "<br>")
    bio_summary = escape(report.bio_domain_summary or "없음")
    news_summary = escape(report.news_llm_summary or "없음")
    positive = escape(_safe_join(report.news_positive_keywords))
    negative = escape(_safe_join(report.news_negative_keywords))
    financial_risks = escape(_safe_join(report.financial_risk_factors))
    disclosure_keywords = escape(_safe_join(report.disclosure_detected_keywords))

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(report.company_name)} - BioCredit Agent</title>
<style>
  body {{ margin:0; font-family:'Segoe UI', Arial, sans-serif; background:#eef3f8; color:#253044; }}
  header {{ background:linear-gradient(135deg,#16345b,#245c88 65%,#2d7c8f); color:white; padding:22px 36px; }}
  header a {{ color:white; text-decoration:none; opacity:.9; font-weight:700; }}
  header h1 {{ margin:10px 0 0; font-size:1.55rem; }}
  main {{ max-width:1120px; margin:24px auto; padding:0 20px; }}
  .card {{ background:white; border-radius:8px; padding:22px; margin-bottom:18px; box-shadow:0 1px 10px rgba(23,43,77,.09); border:1px solid #dde7f1; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
  .metric {{ background:#f7fafc; border:1px solid #e2e8f0; border-radius:6px; padding:14px; }}
  .metric-button {{ width:100%; text-align:left; cursor:pointer; font:inherit; color:inherit; }}
  .metric-button:hover, .metric-button.active {{ border-color:#8fc4e8; background:#e8f4fd; box-shadow:0 0 0 2px rgba(36,92,136,.08); }}
  .label {{ color:#718096; font-size:.78rem; margin-bottom:6px; }}
  .value {{ font-size:1.15rem; font-weight:800; }}
  .grade {{ display:inline-block; background:{grade_color}; color:white; padding:5px 12px; border-radius:5px; }}
  .report {{ background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding:16px; line-height:1.65; }}
  .evidence-panel {{ display:none; }}
  .evidence-panel.active {{ display:block; }}
  ul {{ line-height:1.7; padding-left:20px; }}
</style>
</head>
<body>
<header><a href="/">← 목록으로</a><h1>{escape(report.company_name)} 상세 보고서</h1></header>
<main>
  <section class="card">
    <div class="grid">
      <div class="metric"><div class="label">종목코드</div><div class="value">{ticker}</div></div>
      <div class="metric"><div class="label">시장/분류</div><div class="value">{industry}</div></div>
      <div class="metric"><div class="label">시가총액</div><div class="value">{market_cap}</div></div>
      <div class="metric"><div class="label">등급</div><div class="value"><span class="grade">{report.grade.value}</span></div></div>
      <button class="metric metric-button active" type="button" data-panel="final-evidence"><div class="label">최종점수</div><div class="value">{report.final_score:.1f}</div></button>
      <button class="metric metric-button" type="button" data-panel="financial-evidence"><div class="label">재무</div><div class="value">{report.financial_score:.1f}</div></button>
      <button class="metric metric-button" type="button" data-panel="news-evidence"><div class="label">뉴스</div><div class="value">{news_str}</div></button>
      <button class="metric metric-button" type="button" data-panel="bio-evidence"><div class="label">바이오</div><div class="value">{report.bio_score:.1f}</div></button>
      <div class="metric"><div class="label">판단</div><div class="value">{decision_label}</div></div>
    </div>
  </section>
  <section class="card evidence-panel active" id="final-evidence">
    <h2>최종점수 산출 근거</h2>
    <ul>
      <li><strong>최종점수:</strong> {report.final_score:.1f}</li>
      <li><strong>등급:</strong> {report.grade.value}</li>
      <li><strong>판단:</strong> {decision_label}</li>
      <li><strong>재무 점수:</strong> {report.financial_score:.1f}</li>
      <li><strong>뉴스 점수:</strong> {news_str}</li>
      <li><strong>바이오 점수:</strong> {report.bio_score:.1f}</li>
      <li><strong>공시 리스크:</strong> {escape(report.disclosure_risk_level.value)}</li>
      <li><strong>특이사항:</strong> {"있음" if report.special_case else "없음"}</li>
    </ul>
  </section>
  <section class="card evidence-panel" id="news-evidence">
    <h2>뉴스 분석 근거</h2>
    <ul>
      <li><strong>뉴스 최종 점수:</strong> {news_str}</li>
      <li><strong>키워드 점수:</strong> {_fmt_score(report.news_keyword_score)}</li>
      <li><strong>LLM 점수:</strong> {_fmt_score(report.news_llm_score)}</li>
      <li><strong>키워드 적중:</strong> {report.news_keyword_hits}</li>
      <li><strong>긍정 키워드:</strong> {positive}</li>
      <li><strong>부정 키워드:</strong> {negative}</li>
      <li><strong>중대 부정 이벤트:</strong> {"감지됨" if report.news_negative_critical_event else "없음"}</li>
      <li><strong>병합 가중치:</strong> {escape(report.news_merge_weights or "없음")}</li>
      <li><strong>LLM 요약:</strong> {news_summary}</li>
    </ul>
  </section>
  <section class="card evidence-panel" id="financial-evidence">
    <h2>재무제표 분석 근거</h2>
    <ul>
      <li><strong>재무 점수:</strong> {report.financial_score:.1f}</li>
      <li><strong>위험 요인:</strong> {financial_risks}</li>
      <li><strong>공시 리스크 영향:</strong> {escape(report.disclosure_risk_level.value)}</li>
    </ul>
  </section>
  <section class="card evidence-panel" id="bio-evidence"><h2>바이오 분석 근거</h2><p>{bio_summary}</p></section>
  <section class="card">
    <h2>공시 리스크 근거</h2>
    <ul>
      <li><strong>공시 리스크:</strong> {escape(report.disclosure_risk_level.value)}</li>
      <li><strong>감지 키워드:</strong> {disclosure_keywords}</li>
    </ul>
  </section>
  <section class="card"><h2>Report</h2><div class="report">{report_html}</div></section>
</main>
<script>
  document.querySelectorAll('.metric-button').forEach((button) => {{
    button.addEventListener('click', () => {{
      const targetId = button.dataset.panel;
      document.querySelectorAll('.metric-button').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.evidence-panel').forEach((panel) => panel.classList.remove('active'));
      button.classList.add('active');
      const target = document.getElementById(targetId);
      if (target) {{
        target.classList.add('active');
        target.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
      }}
    }});
  }});
</script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/companies")
async def api_all_companies() -> JSONResponse:
    return JSONResponse(content=[report.model_dump() for report in _REPORTS.values()])


@app.get("/api/companies/{company_id}")
async def api_company(company_id: str) -> JSONResponse:
    report = _REPORTS.get(company_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Company ID '{company_id}' not found.")
    return JSONResponse(content=report.model_dump())


@app.post("/api/start")
async def api_start_analysis() -> JSONResponse:
    _start_analysis_task()
    total = len(_COMPANIES) or int(os.getenv("KOSDAQ_TOP_LIMIT", "50"))
    return JSONResponse(
        content={
            "analysis_started": _analysis_started,
            "total_companies": total,
            "completed": len(_REPORTS),
        }
    )


@app.get("/api/status")
async def api_status() -> JSONResponse:
    total = len(_COMPANIES) or int(os.getenv("KOSDAQ_TOP_LIMIT", "50"))
    return JSONResponse(
        content={
            "analysis_started": _analysis_started,
            "total_companies": total,
            "completed": len(_REPORTS),
            "company_ids": list(COMPANIES_BY_ID.keys()),
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
