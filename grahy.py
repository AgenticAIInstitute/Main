"""LangGraph 워크플로우 — 9개 AI Agent + Human-in-the-Loop + 재시작 로직.

그래프 흐름:
  planner → financial → news → bio_domain → disclosure
          → risk_scoring → loan_decision
          → supervisory_review  ← B/C 등급만 처리
               ↓ restart_required: True
            planner (전체 재분석)
               ↓ needs_human_review: True
            human_review
               ↓
          report_writer → END

재시작 조건:
  supervisory_review에서 LLM 판단 실패 + restart_count < 1
  → restart_required: True → planner로 이동
  → planner에서 분석 결과 초기화 후 재분석

등급별 최종 처리:
  A      → 자동 승인
  B      → SupervisoryReviewAgent → 자동 처리
  C      → SupervisoryReviewAgent → 단순 케이스 Human Review,
                                    LLM 판단 후 B면 자동 승인 / D,E면 자동 거절
  D / E  → 자동 거절
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from biocredit.state import CompanyAnalysisState
from biocredit.agents.planner            import planner_node
from biocredit.agents.financial          import financial_node
from biocredit.agents.news               import news_node
from biocredit.agents.bio_domain         import bio_domain_node
from biocredit.agents.disclosure         import disclosure_node
from biocredit.agents.risk_scoring       import risk_scoring_node
from biocredit.agents.loan_decision      import loan_decision_node
from biocredit.agents.supervisory_review import supervisory_review_node
from biocredit.agents.human_review       import human_review_node
from biocredit.agents.report_writer      import report_writer_node


# ──────────────────────────────────────────────
# 조건부 엣지 함수
# ──────────────────────────────────────────────
def _route_after_supervisory(state: dict) -> str:
    """
    supervisory_review 노드 이후 라우팅.

    우선순위:
      1. restart_required: True  → planner (전체 재분석)
      2. needs_human_review: True → human_review
      3. 그 외                   → report_writer
    """
    if state.get("restart_required", False):
        return "planner"
    if state.get("needs_human_review", False):
        return "human_review"
    return "report_writer"


# ──────────────────────────────────────────────
# 그래프 생성
# ──────────────────────────────────────────────
def create_graph() -> StateGraph:
    g = StateGraph(CompanyAnalysisState)

    # ── 노드 등록 ─────────────────────────────
    g.add_node("planner",            planner_node)
    g.add_node("financial",          financial_node)
    g.add_node("news",               news_node)
    g.add_node("bio_domain",         bio_domain_node)
    g.add_node("disclosure",         disclosure_node)
    g.add_node("risk_scoring",       risk_scoring_node)
    g.add_node("loan_decision",      loan_decision_node)
    g.add_node("supervisory_review", supervisory_review_node)
    g.add_node("human_review",       human_review_node)
    g.add_node("report_writer",      report_writer_node)

    # ── 고정 엣지 ─────────────────────────────
    g.set_entry_point("planner")
    g.add_edge("planner",       "financial")
    g.add_edge("financial",     "news")
    g.add_edge("news",          "bio_domain")
    g.add_edge("bio_domain",    "disclosure")
    g.add_edge("disclosure",    "risk_scoring")
    g.add_edge("risk_scoring",  "loan_decision")
    g.add_edge("loan_decision", "supervisory_review")
    g.add_edge("human_review",  "report_writer")
    g.add_edge("report_writer", END)

    # ── 조건부 엣지 ───────────────────────────
    # supervisory_review 이후:
    #   restart_required: True  → planner (재시작)
    #   needs_human_review: True → human_review
    #   그 외                   → report_writer
    g.add_conditional_edges(
        "supervisory_review",
        _route_after_supervisory,
        {
            "planner":       "planner",
            "human_review":  "human_review",
            "report_writer": "report_writer",
        },
    )

    # MemorySaver: human_review interrupt() 재개를 위해 필요
    return g.compile(checkpointer=MemorySaver())