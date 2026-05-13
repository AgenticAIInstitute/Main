from __future__ import annotations
import sys
import os
import logging
from typing import Any

# .env 로드 (최우선)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

# 패키지 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from langgraph.graph import StateGraph, END

from models.schemas import BioAgentState, CompanyReport
from data.mock_companies import MOCK_COMPANIES, COMPANIES_BY_ID
from agents import (
    PlannerAgent, FinancialAgent, NewsAgent, BioDomainAgent,
    DisclosureAgent, RiskScoringAgent, SupervisoryReviewAgent,
    LoanDecisionAgent, ReportWriterAgent,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# LangGraph 워크플로우 구성
# ──────────────────────────────────────────────

_planner = PlannerAgent()
_financial = FinancialAgent()
_news = NewsAgent()
_bio = BioDomainAgent()
_disclosure = DisclosureAgent()
_risk = RiskScoringAgent()
_supervisory = SupervisoryReviewAgent()
_loan = LoanDecisionAgent()
_report = ReportWriterAgent()


def planner_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _planner.run(s).model_dump()


def financial_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _financial.run(s).model_dump()


def news_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _news.run(s).model_dump()


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
    return _supervisory.run(s).model_dump()


def loan_decision_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _loan.run(s).model_dump()


def report_writer_node(state: dict) -> dict:
    s = BioAgentState(**state)
    return _report.run(s).model_dump()


def _build_graph() -> Any:
    g = StateGraph(dict)
    g.add_node("planner", planner_node)
    g.add_node("financial", financial_node)
    g.add_node("news", news_node)
    g.add_node("bio_domain", bio_domain_node)
    g.add_node("disclosure", disclosure_node)
    g.add_node("risk_scoring", risk_scoring_node)
    g.add_node("supervisory", supervisory_node)
    g.add_node("loan_decision", loan_decision_node)
    g.add_node("report_writer", report_writer_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "financial")
    g.add_edge("financial", "news")
    g.add_edge("news", "bio_domain")
    g.add_edge("bio_domain", "disclosure")
    g.add_edge("disclosure", "risk_scoring")
    g.add_edge("risk_scoring", "supervisory")
    g.add_edge("supervisory", "loan_decision")
    g.add_edge("loan_decision", "report_writer")
    g.add_edge("report_writer", END)
    return g.compile()


_pipeline = _build_graph()


def analyze_company(company_data: Any) -> CompanyReport:
    initial_state = BioAgentState(company_data=company_data).model_dump()
    final_state = _pipeline.invoke(initial_state)
    result = BioAgentState(**final_state)
    if result.report is None:
        raise RuntimeError(f"분석 실패: {company_data.company_id}")
    return result.report


# ──────────────────────────────────────────────
# 앱 시작 시 전체 기업 분석 실행
# ──────────────────────────────────────────────

_REPORTS: dict[str, CompanyReport] = {}


def _run_all_analyses() -> None:
    logger.info("전체 기업 분석 시작 (%d개)", len(MOCK_COMPANIES))
    for company in MOCK_COMPANIES:
        try:
            report = analyze_company(company)
            _REPORTS[company.company_id] = report
            logger.info("분석 완료: %s → %s (%s)", company.company_name, report.grade, report.final_decision)
        except Exception as e:
            logger.error("분석 오류 [%s]: %s", company.company_id, e)


_run_all_analyses()

# ──────────────────────────────────────────────
# FastAPI 앱
# ──────────────────────────────────────────────

app = FastAPI(title="BioCredit Agent", version="1.0.0")

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
    "A": "#1a6b3a", "B": "#2980b9",
    "C": "#e67e22", "D": "#c0392b", "E": "#7f0000",
}


@app.get("/", response_class=HTMLResponse)
async def main_page() -> HTMLResponse:
    rows = ""
    for r in _REPORTS.values():
        news_str = f"{r.news_score:.1f}" if r.news_score is not None else "<em>없음</em>"
        dec_color = DECISION_COLOR.get(r.final_decision.value, "#555")
        dec_label = DECISION_LABEL.get(r.final_decision.value, r.final_decision.value)
        grade_color = GRADE_COLOR.get(r.grade.value, "#555")
        special_badge = (
            '<span class="badge badge-warn">특이</span>'
            if r.special_case
            else '<span class="badge badge-ok">정상</span>'
        )
        rows += f"""
        <tr>
          <td><strong>{r.company_name}</strong></td>
          <td class="num">{r.final_score:.1f}</td>
          <td><span class="grade" style="background:{grade_color}">{r.grade.value}</span></td>
          <td class="num">{r.financial_score:.1f}</td>
          <td class="num">{news_str}</td>
          <td class="num">{r.bio_score:.1f}</td>
          <td class="num">{r.disclosure_risk_level.value}</td>
          <td>{special_badge}</td>
          <td><span class="decision" style="background:{dec_color}">{dec_label}</span></td>
          <td><a href="/companies/{r.company_id}" class="btn-detail">상세보기</a></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BioCredit Agent — 여신심사 대시보드</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #2d3748; }}
  header {{ background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
            color: white; padding: 24px 40px; }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; }}
  header p  {{ font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }}
  .container {{ max-width: 1300px; margin: 30px auto; padding: 0 20px; }}
  .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.08);
           overflow: hidden; }}
  .card-header {{ padding: 20px 28px; border-bottom: 1px solid #e2e8f0;
                  display: flex; justify-content: space-between; align-items: center; }}
  .card-header h2 {{ font-size: 1.1rem; color: #2d3748; }}
  .stats {{ display: flex; gap: 12px; }}
  .stat {{ background: #ebf8ff; color: #2b6cb0; border-radius: 8px;
           padding: 6px 14px; font-size: 0.82rem; font-weight: 600; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #f7fafc; padding: 12px 16px; text-align: left;
        font-size: 0.82rem; color: #718096; font-weight: 600;
        border-bottom: 2px solid #e2e8f0; white-space: nowrap; }}
  td {{ padding: 13px 16px; border-bottom: 1px solid #f0f4f8;
        font-size: 0.88rem; vertical-align: middle; }}
  tr:hover td {{ background: #f7fafc; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .grade {{ display: inline-block; color: white; font-weight: 700;
            border-radius: 6px; padding: 3px 10px; font-size: 0.9rem; }}
  .decision {{ display: inline-block; color: white; border-radius: 20px;
               padding: 4px 12px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; }}
  .badge {{ display: inline-block; border-radius: 12px; padding: 3px 10px;
            font-size: 0.78rem; font-weight: 600; }}
  .badge-warn {{ background: #fff3cd; color: #856404; }}
  .badge-ok   {{ background: #d1e7dd; color: #0f5132; }}
  .btn-detail {{ background: #2b6cb0; color: white; text-decoration: none;
                 border-radius: 6px; padding: 5px 12px; font-size: 0.8rem;
                 white-space: nowrap; transition: background .2s; }}
  .btn-detail:hover {{ background: #1a4e8a; }}
  .legend {{ margin-top: 20px; display: flex; flex-wrap: wrap; gap: 12px; padding: 0 4px; }}
  .legend-item {{ font-size: 0.8rem; color: #718096; }}
  .legend-item strong {{ color: #4a5568; }}
  footer {{ text-align: center; padding: 24px; color: #a0aec0; font-size: 0.8rem; }}
</style>
</head>
<body>
<header>
  <h1>BioCredit Agent</h1>
  <p>코스닥 바이오·제약 기업 여신 심사 AI 대시보드</p>
</header>
<div class="container">
  <div class="card">
    <div class="card-header">
      <h2>기업 심사 결과 ({len(_REPORTS)}개사)</h2>
      <div class="stats">
        <span class="stat">승인 {sum(1 for r in _REPORTS.values() if r.final_decision.value == "APPROVED")}건</span>
        <span class="stat" style="background:#fff3cd;color:#856404">검토 {sum(1 for r in _REPORTS.values() if r.final_decision.value == "HUMAN_IN_THE_LOOP")}건</span>
        <span class="stat" style="background:#f8d7da;color:#842029">부결 {sum(1 for r in _REPORTS.values() if r.final_decision.value == "REJECTED")}건</span>
      </div>
    </div>
    <table>
      <thead>
        <tr>
          <th>기업명</th><th style="text-align:right">최종점수</th><th>등급</th>
          <th style="text-align:right">재무점수</th><th style="text-align:right">뉴스점수</th>
          <th style="text-align:right">바이오점수</th><th>공시리스크</th>
          <th>특이사항</th><th>최종판단</th><th>상세</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
  <div class="legend">
    <span class="legend-item"><strong>등급 기준:</strong> A≥85 · B≥70 · C≥55 · D≥40 · E&lt;40</span>
    <span class="legend-item"><strong>가중치:</strong> 재무40% · 뉴스25% · 바이오25% · 공시10%</span>
    <span class="legend-item"><strong>판단:</strong> A·B→승인 · C→전문가검토 · D·E→부결 · 특이사항→전문가검토</span>
  </div>
</div>
<footer>BioCredit Agent v1.0 · LangGraph + Gemini AI · FastAPI</footer>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(company_id: str) -> HTMLResponse:
    r = _REPORTS.get(company_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"기업 ID '{company_id}'를 찾을 수 없습니다.")

    news_str = f"{r.news_score:.1f}점" if r.news_score is not None else "데이터 없음 (판단 불확실)"
    dec_color = DECISION_COLOR.get(r.final_decision.value, "#555")
    dec_label = DECISION_LABEL.get(r.final_decision.value, r.final_decision.value)
    grade_color = GRADE_COLOR.get(r.grade.value, "#555")
    special_str = "있음 ⚠️" if r.special_case else "없음"
    report_html = r.report_text.replace("\n", "<br>")

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{r.company_name} — BioCredit Agent</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #f0f4f8; color: #2d3748; }}
  header {{ background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
            color: white; padding: 20px 40px; display: flex; align-items: center; gap: 20px; }}
  header a {{ color: rgba(255,255,255,.8); text-decoration: none; font-size: 0.9rem; }}
  header h1 {{ font-size: 1.5rem; font-weight: 700; }}
  .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; display: grid;
                gap: 20px; }}
  .card {{ background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,.08);
           padding: 28px; }}
  .card h2 {{ font-size: 1.05rem; color: #4a5568; margin-bottom: 18px;
              padding-bottom: 10px; border-bottom: 2px solid #e2e8f0; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
                   gap: 16px; }}
  .metric {{ background: #f7fafc; border-radius: 10px; padding: 16px; text-align: center; }}
  .metric .label {{ font-size: 0.78rem; color: #718096; margin-bottom: 6px; }}
  .metric .value {{ font-size: 1.5rem; font-weight: 700; color: #2d3748; }}
  .metric .sub {{ font-size: 0.78rem; color: #a0aec0; margin-top: 4px; }}
  .grade-big {{ display: inline-block; color: white; border-radius: 10px;
                padding: 8px 22px; font-size: 1.8rem; font-weight: 800;
                background: {grade_color}; }}
  .decision-badge {{ display: inline-block; color: white; border-radius: 24px;
                     padding: 8px 22px; font-size: 1.1rem; font-weight: 700;
                     background: {dec_color}; }}
  .flags {{ list-style: none; }}
  .flags li {{ padding: 8px 12px; background: #fff8e1; border-left: 4px solid #f59e0b;
               border-radius: 4px; margin-bottom: 8px; font-size: 0.88rem; }}
  .report-box {{ background: #f7fafc; border-radius: 8px; padding: 20px;
                 font-size: 0.9rem; line-height: 1.8; color: #4a5568; }}
  .back-btn {{ display: inline-block; background: #2b6cb0; color: white;
               text-decoration: none; border-radius: 8px; padding: 10px 22px;
               font-size: 0.9rem; margin-top: 10px; }}
  .back-btn:hover {{ background: #1a4e8a; }}
</style>
</head>
<body>
<header>
  <div>
    <a href="/">← 목록으로 돌아가기</a>
    <h1>{r.company_name} 여신심사 상세 보고서</h1>
  </div>
</header>
<div class="container">
  <div class="card">
    <h2>심사 결과 요약</h2>
    <div class="summary-grid">
      <div class="metric">
        <div class="label">최초 산출 등급</div>
        <div class="value"><span class="grade-big">{r.grade.value}</span></div>
      </div>
      <div class="metric">
        <div class="label">최종 점수</div>
        <div class="value">{r.final_score:.1f}</div>
        <div class="sub">/ 100점</div>
      </div>
      <div class="metric">
        <div class="label">재무 점수</div>
        <div class="value">{r.financial_score:.1f}</div>
        <div class="sub">가중치 40%</div>
      </div>
      <div class="metric">
        <div class="label">뉴스 점수</div>
        <div class="value" style="font-size:1.1rem">{news_str}</div>
        <div class="sub">가중치 25%</div>
      </div>
      <div class="metric">
        <div class="label">바이오 점수</div>
        <div class="value">{r.bio_score:.1f}</div>
        <div class="sub">가중치 25%</div>
      </div>
      <div class="metric">
        <div class="label">공시 리스크</div>
        <div class="value" style="font-size:1.1rem">{r.disclosure_risk_level.value}</div>
        <div class="sub">가중치 10%</div>
      </div>
      <div class="metric">
        <div class="label">특이사항</div>
        <div class="value" style="font-size:1rem">{special_str}</div>
      </div>
      <div class="metric">
        <div class="label">최종 판단</div>
        <div class="value"><span class="decision-badge">{dec_label}</span></div>
      </div>
    </div>
  </div>

  {"" if not r.special_case else f'''
  <div class="card">
    <h2>⚠️ 특이사항 상세</h2>
    <p style="font-size:.88rem;color:#4a5568;line-height:1.7">{r.special_case_reason.replace(chr(10), "<br>")}</p>
  </div>'''}

  <div class="card">
    <h2>최종 판단 근거</h2>
    <p style="font-size:.9rem;line-height:1.7;color:#4a5568">{r.decision_reason}</p>
  </div>

  <div class="card">
    <h2>AI 생성 심사 보고서</h2>
    <div class="report-box">{report_html}</div>
  </div>

  <a href="/" class="back-btn">← 기업 목록으로 돌아가기</a>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/companies")
async def api_all_companies() -> JSONResponse:
    return JSONResponse(
        content=[r.model_dump() for r in _REPORTS.values()]
    )


@app.get("/api/companies/{company_id}")
async def api_company(company_id: str) -> JSONResponse:
    r = _REPORTS.get(company_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"기업 ID '{company_id}'를 찾을 수 없습니다.")
    return JSONResponse(content=r.model_dump())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
