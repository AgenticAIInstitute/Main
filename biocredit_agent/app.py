from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import json

from biocredit_agent.agents.planner_agent import PlannerAgent
from biocredit_agent.agents.financial_agent import FinancialAgent
from biocredit_agent.agents.news_agent import NewsAgent
from biocredit_agent.agents.bio_domain_agent import BioDomainAgent
from biocredit_agent.agents.disclosure_agent import DisclosureAgent
from biocredit_agent.agents.risk_scoring_agent import RiskScoringAgent
from biocredit_agent.agents.supervisory_review_agent import SupervisoryReviewAgent
from biocredit_agent.agents.loan_decision_agent import LoanDecisionAgent
from biocredit_agent.agents.report_writer_agent import ReportWriterAgent
from biocredit_agent.models.schemas import AgentResult

app = FastAPI(title="BioCredit Agent")

analyzed_data = []

@app.on_event("startup")
def startup_event():
    global analyzed_data
    print("Agentic pipeline running on startup...")
    companies = PlannerAgent().plan()
    
    fin_agent = FinancialAgent()
    news_agent = NewsAgent()
    bio_agent = BioDomainAgent()
    disc_agent = DisclosureAgent()
    score_agent = RiskScoringAgent()
    review_agent = SupervisoryReviewAgent()
    decision_agent = LoanDecisionAgent()
    report_agent = ReportWriterAgent()
    
    for c in companies:
        res = AgentResult(company_id=c.id, company_name=c.name)
        res = fin_agent.analyze(c, res)
        res = news_agent.analyze(c, res)
        res = bio_agent.analyze(c, res)
        res = disc_agent.analyze(c, res)
        res = score_agent.analyze(res)
        res = review_agent.analyze(res)
        res = decision_agent.analyze(res)
        res = report_agent.analyze(res)
        analyzed_data.append(res.dict())
    print("Pipeline finished. Data ready.")

@app.get("/api/data")
def get_data():
    return analyzed_data

@app.get("/", response_class=HTMLResponse)
def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BioCredit AI - 여신 대출 심사 스튜디오</title>
        <!-- Pretendard Font for perfect Korean typography -->
        <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css" />
        <style>
            :root {
                --bg-app: #090d16;
                --bg-sidebar: #0e1322;
                --bg-card: #131a30;
                --bg-card-hover: #19223e;
                --border-color: rgba(255, 255, 255, 0.08);
                
                --text-main: #f3f4f6;
                --text-sub: #9ca3af;
                --text-muted: #6b7280;
                
                --primary: #3b82f6;
                --primary-glow: rgba(59, 130, 246, 0.3);
                
                /* Sophisticated Pastel Colors */
                --success-bg: rgba(16, 185, 129, 0.12);
                --success-text: #10b981;
                --success-border: rgba(16, 185, 129, 0.3);
                
                --warning-bg: rgba(245, 158, 11, 0.12);
                --warning-text: #f59e0b;
                --warning-border: rgba(245, 158, 11, 0.3);
                
                --danger-bg: rgba(239, 68, 68, 0.12);
                --danger-text: #ef4444;
                --danger-border: rgba(239, 68, 68, 0.3);

                --purple-bg: rgba(139, 92, 246, 0.12);
                --purple-text: #a78bfa;
                --purple-border: rgba(139, 92, 246, 0.3);
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            }

            body {
                background-color: var(--bg-app);
                color: var(--text-main);
                min-height: 100vh;
                display: flex;
                overflow-x: hidden;
            }

            /* Sidebar */
            .sidebar {
                width: 260px;
                background-color: var(--bg-sidebar);
                border-right: 1px solid var(--border-color);
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                padding: 32px 20px;
                flex-shrink: 0;
            }

            .logo-area {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 0 8px 32px 8px;
                border-bottom: 1px solid var(--border-color);
            }

            .logo-icon {
                width: 32px;
                height: 32px;
                background: linear-gradient(135deg, #2563eb, #8b5cf6);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                color: #fff;
                font-size: 1.1rem;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            }

            .logo-text {
                font-size: 1.15rem;
                font-weight: 700;
                letter-spacing: -0.03em;
                background: linear-gradient(to right, #ffffff, #a5b4fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }

            .sidebar-menu {
                margin-top: 24px;
                display: flex;
                flex-direction: column;
                gap: 6px;
                flex-grow: 1;
            }

            .menu-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 14px;
                border-radius: 8px;
                color: var(--text-sub);
                font-size: 0.95rem;
                font-weight: 500;
                text-decoration: none;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .menu-item:hover, .menu-item.active {
                color: #fff;
                background-color: rgba(255, 255, 255, 0.05);
            }

            .menu-item.active {
                background-color: rgba(37, 99, 235, 0.15);
                color: #60a5fa;
                font-weight: 600;
                border: 1px solid rgba(37, 99, 235, 0.25);
            }

            .sidebar-footer {
                padding-top: 16px;
                border-top: 1px solid var(--border-color);
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .avatar {
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background-color: #3b82f6;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 600;
                color: #fff;
                font-size: 0.85rem;
            }

            .user-info {
                display: flex;
                flex-direction: column;
            }

            .user-info .name {
                font-size: 0.85rem;
                font-weight: 600;
                color: #fff;
            }

            .user-info .role {
                font-size: 0.75rem;
                color: var(--text-muted);
            }

            /* Main Content Container */
            .main-content {
                flex-grow: 1;
                padding: 40px 48px;
                display: flex;
                flex-direction: column;
                gap: 32px;
                overflow-y: auto;
                max-width: calc(100vw - 260px);
            }

            /* Top Bar */
            .top-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .welcome-msg h2 {
                font-size: 1.8rem;
                font-weight: 700;
                letter-spacing: -0.03em;
                margin-bottom: 4px;
            }

            .welcome-msg p {
                color: var(--text-sub);
                font-size: 0.95rem;
            }

            .engine-status {
                display: flex;
                align-items: center;
                gap: 8px;
                background-color: rgba(16, 185, 129, 0.06);
                border: 1px solid rgba(16, 185, 129, 0.15);
                padding: 8px 16px;
                border-radius: 99px;
                font-size: 0.85rem;
                font-weight: 600;
                color: var(--success-text);
            }

            .status-dot {
                width: 8px;
                height: 8px;
                background-color: var(--success-text);
                border-radius: 50%;
                box-shadow: 0 0 10px var(--success-text);
                animation: pulse 2s infinite;
            }

            @keyframes pulse {
                0% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.3); opacity: 0.5; }
                100% { transform: scale(1); opacity: 1; }
            }

            /* KPI Cards Grid */
            .kpi-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
            }

            .kpi-card {
                background-color: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                padding: 24px;
                display: flex;
                flex-direction: column;
                gap: 12px;
                position: relative;
                overflow: hidden;
            }

            .kpi-card::before {
                content: '';
                position: absolute;
                top: 0; left: 0; width: 4px; height: 100%;
            }

            .kpi-card.total::before { background-color: var(--primary); }
            .kpi-card.approved::before { background-color: var(--success-text); }
            .kpi-card.hitl::before { background-color: var(--warning-text); }
            .kpi-card.rejected::before { background-color: var(--danger-text); }

            .kpi-header {
                font-size: 0.85rem;
                color: var(--text-sub);
                font-weight: 600;
                letter-spacing: -0.01em;
            }

            .kpi-value {
                font-size: 2rem;
                font-weight: 700;
                color: #fff;
                font-family: 'JetBrains Mono', monospace;
            }

            .kpi-desc {
                font-size: 0.75rem;
                color: var(--text-muted);
            }

            /* Search and Filter Section */
            .filter-section {
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                background-color: rgba(255, 255, 255, 0.02);
                border: 1px solid var(--border-color);
                padding: 16px 24px;
                border-radius: 12px;
            }

            .search-box {
                position: relative;
                width: 320px;
            }

            .search-box input {
                width: 100%;
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid var(--border-color);
                padding: 10px 16px 10px 40px;
                border-radius: 8px;
                color: #fff;
                font-size: 0.9rem;
                outline: none;
                transition: all 0.2s ease;
            }

            .search-box input:focus {
                border-color: var(--primary);
                background-color: rgba(255, 255, 255, 0.06);
                box-shadow: 0 0 0 3px var(--primary-glow);
            }

            .search-box svg {
                position: absolute;
                left: 14px;
                top: 50%;
                transform: translateY(-50%);
                color: var(--text-muted);
            }

            .filter-tabs {
                display: flex;
                gap: 8px;
            }

            .filter-tab {
                background: none;
                border: 1px solid transparent;
                color: var(--text-sub);
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 0.85rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
                white-space: nowrap;
            }

            .filter-tab:hover {
                color: #fff;
                background-color: rgba(255, 255, 255, 0.04);
            }

            .filter-tab.active {
                background-color: rgba(255, 255, 255, 0.08);
                border-color: var(--border-color);
                color: #fff;
            }

            /* Table Section */
            .table-card {
                background-color: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
            }

            .table-wrapper {
                overflow-x: auto;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                text-align: left;
                white-space: nowrap;
            }

            th {
                background-color: rgba(0, 0, 0, 0.15);
                color: var(--text-sub);
                font-size: 0.8rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                padding: 16px 24px;
                border-bottom: 1px solid var(--border-color);
            }

            td {
                padding: 18px 24px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
                font-size: 0.9rem;
                color: var(--text-main);
                vertical-align: middle;
            }

            tbody tr {
                cursor: pointer;
                transition: all 0.2s ease;
            }

            tbody tr:hover {
                background-color: var(--bg-card-hover);
            }

            .comp-name {
                font-weight: 600;
                color: #fff;
                font-size: 0.95rem;
            }

            .score-num {
                font-family: 'JetBrains Mono', monospace;
                font-weight: 600;
                color: #fff;
            }

            /* Score Progress Bar */
            .progress-container {
                display: flex;
                align-items: center;
                gap: 12px;
                min-width: 120px;
            }

            .progress-bar-bg {
                width: 60px;
                height: 6px;
                background-color: rgba(255, 255, 255, 0.08);
                border-radius: 3px;
                overflow: hidden;
            }

            .progress-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, #3b82f6, #60a5fa);
                border-radius: 3px;
            }

            .progress-bar-fill.high {
                background: linear-gradient(90deg, #10b981, #34d399);
            }

            .progress-bar-fill.low {
                background: linear-gradient(90deg, #ef4444, #f87171);
            }

            .progress-val {
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                color: var(--text-sub);
                width: 28px;
                text-align: right;
            }

            /* Better Status Badges */
            .badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 0.75rem;
                font-weight: 600;
                border: 1px solid transparent;
            }

            .badge::before {
                content: '';
                width: 6px;
                height: 6px;
                border-radius: 50%;
            }

            .badge.APPROVED {
                background-color: var(--success-bg);
                color: var(--success-text);
                border-color: var(--success-border);
            }
            .badge.APPROVED::before { background-color: var(--success-text); }

            .badge.HUMAN_IN_THE_LOOP {
                background-color: var(--warning-bg);
                color: var(--warning-text);
                border-color: var(--warning-border);
            }
            .badge.HUMAN_IN_THE_LOOP::before { background-color: var(--warning-text); }

            .badge.REJECTED {
                background-color: var(--danger-bg);
                color: var(--danger-text);
                border-color: var(--danger-border);
            }
            .badge.REJECTED::before { background-color: var(--danger-text); }

            .badge.grade-A, .badge.grade-B {
                background-color: var(--success-bg);
                color: var(--success-text);
                border-color: var(--success-border);
            }
            .badge.grade-C {
                background-color: var(--warning-bg);
                color: var(--warning-text);
                border-color: var(--warning-border);
            }
            .badge.grade-D, .badge.grade-E {
                background-color: var(--danger-bg);
                color: var(--danger-text);
                border-color: var(--danger-border);
            }

            .badge.special {
                background-color: var(--purple-bg);
                color: var(--purple-text);
                border-color: var(--purple-border);
            }
            .badge.special::before { background-color: var(--purple-text); }

            .badge.normal {
                background-color: rgba(255, 255, 255, 0.04);
                color: var(--text-sub);
                border-color: var(--border-color);
            }
            .badge.normal::before { background-color: var(--text-muted); }

            /* Premium Report Modal Slide-over style */
            .modal-overlay {
                display: none;
                position: fixed;
                top: 0; left: 0; width: 100vw; height: 100vh;
                background-color: rgba(3, 7, 18, 0.6);
                backdrop-filter: blur(8px);
                z-index: 1000;
                justify-content: flex-end;
                opacity: 0;
                transition: opacity 0.3s ease;
            }

            .modal-overlay.show {
                display: flex;
                opacity: 1;
            }

            .modal-content {
                background-color: var(--bg-sidebar);
                width: 680px;
                height: 100%;
                border-left: 1px solid var(--border-color);
                box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
                display: flex;
                flex-direction: column;
                transform: translateX(100%);
                transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            }

            .modal-overlay.show .modal-content {
                transform: translateX(0);
            }

            .modal-header {
                padding: 32px 40px;
                border-bottom: 1px solid var(--border-color);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .modal-title h3 {
                font-size: 1.3rem;
                font-weight: 700;
                color: #fff;
                margin-bottom: 4px;
            }

            .modal-title p {
                font-size: 0.85rem;
                color: var(--text-sub);
            }

            .close-btn {
                background: none;
                border: 1px solid var(--border-color);
                color: var(--text-sub);
                width: 36px;
                height: 36px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
            }

            .close-btn:hover {
                color: #fff;
                background-color: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.25);
            }

            .modal-body {
                flex-grow: 1;
                overflow-y: auto;
                padding: 40px;
                display: flex;
                flex-direction: column;
                gap: 28px;
            }

            /* Report Styles inside Slide-over */
            .report-card {
                background-color: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 24px;
            }

            .report-section-title {
                font-size: 0.95rem;
                font-weight: 700;
                color: #fff;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                padding-bottom: 8px;
            }

            .report-section-title svg {
                color: var(--primary);
            }

            .report-grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
            }

            .report-item {
                display: flex;
                flex-direction: column;
                gap: 4px;
            }

            .report-label {
                font-size: 0.75rem;
                color: var(--text-muted);
                font-weight: 600;
            }

            .report-value {
                font-size: 0.95rem;
                color: var(--text-main);
                font-weight: 500;
            }

            .report-markdown {
                font-size: 0.95rem;
                line-height: 1.7;
                color: #d1d5db;
                white-space: pre-wrap;
            }

            /* Custom scrollbar for premium feel */
            ::-webkit-scrollbar {
                width: 6px;
                height: 6px;
            }
            ::-webkit-scrollbar-track {
                background: transparent;
            }
            ::-webkit-scrollbar-thumb {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        </style>
    </head>
    <body>
        <!-- Left Sidebar Navigation -->
        <aside class="sidebar">
            <div>
                <div class="logo-area">
                    <div class="logo-icon">B</div>
                    <span class="logo-text">BioCredit Studio</span>
                </div>
                <div class="sidebar-menu">
                    <div class="menu-item active">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
                        종합 여신 모니터링
                    </div>
                    <div class="menu-item">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                        심사 내역 일지
                    </div>
                    <div class="menu-item">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                        엔진 파라미터 세팅
                    </div>
                </div>
            </div>
            <div class="sidebar-footer">
                <div class="avatar">심</div>
                <div class="user-info">
                    <div class="name">심사역 모드</div>
                    <div class="role">BioCredit Senior Officer</div>
                </div>
            </div>
        </aside>

        <!-- Right Main Workspace Container -->
        <main class="main-content">
            <!-- Top App Bar -->
            <header class="top-bar">
                <div class="welcome-msg">
                    <h2>안녕하세요, 심사역님</h2>
                    <p>인메모리 모의 데이터를 활용한 제약·바이오 여신 한도 심사 결과 요약 보고서</p>
                </div>
                <div class="engine-status">
                    <div class="status-dot"></div>
                    Supervisory AI Engine Active
                </div>
            </header>

            <!-- KPI Cards Grid -->
            <section class="kpi-grid">
                <div class="kpi-card total">
                    <div class="kpi-header">총 분석 기업</div>
                    <div class="kpi-value" id="kpi-total">-</div>
                    <div class="kpi-desc">KOSDAQ Bio 기업 수집군</div>
                </div>
                <div class="kpi-card approved">
                    <div class="kpi-header">자동 승인 대상</div>
                    <div class="kpi-value" id="kpi-approved">-</div>
                    <div class="kpi-desc">A/B 등급 및 특이사항 없음</div>
                </div>
                <div class="kpi-card hitl">
                    <div class="kpi-header">심층 전문가 심사</div>
                    <div class="kpi-value" id="kpi-hitl">-</div>
                    <div class="kpi-desc">특이사항 또는 C등급 기업 (HITL)</div>
                </div>
                <div class="kpi-card rejected">
                    <div class="kpi-header">여신 자동 부결</div>
                    <div class="kpi-value" id="kpi-rejected">-</div>
                    <div class="kpi-desc">D/E 등급 가이드라인 미달</div>
                </div>
            </section>

            <!-- Search, Tab and Filter controls -->
            <section class="filter-section">
                <div class="search-box">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <input type="text" id="search-input" placeholder="기업명을 입력하세요..." oninput="filterData()">
                </div>
                <div class="filter-tabs">
                    <button class="filter-tab active" onclick="setFilter('ALL', this)">전체 리스트</button>
                    <button class="filter-tab" onclick="setFilter('APPROVED', this)">승인 대상</button>
                    <button class="filter-tab" onclick="setFilter('HUMAN_IN_THE_LOOP', this)">심층 검토 (HITL)</button>
                    <button class="filter-tab" onclick="setFilter('REJECTED', this)">부결 대상</button>
                </div>
            </section>

            <!-- Main Data Table -->
            <section class="table-card">
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>기업명</th>
                                <th>심사 등급</th>
                                <th>종합 점수</th>
                                <th>재무 평가</th>
                                <th>뉴스 모멘텀</th>
                                <th>바이오 도메인</th>
                                <th>특이사항 검출</th>
                                <th>최종 심사판단</th>
                            </tr>
                        </thead>
                        <tbody id="table-body">
                            <!-- Populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
            </section>
        </main>

        <!-- Right Side Slide-over Detail Modal -->
        <div class="modal-overlay" id="modal" onclick="closeModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <div class="modal-title">
                        <h3 id="modal-title-text">종합 심사 결과</h3>
                        <p>BioCredit AI Multi-Agent종합 리스크 심사의견서</p>
                    </div>
                    <button class="close-btn" onclick="closeModal()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
                </div>
                <div class="modal-body">
                    <!-- Summary block -->
                    <div class="report-card">
                        <div class="report-section-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                            핵심 심사 지표 요약
                        </div>
                        <div class="report-grid">
                            <div class="report-item">
                                <span class="report-label">최종 등급</span>
                                <span class="report-value" id="detail-grade">-</span>
                            </div>
                            <div class="report-item">
                                <span class="report-label">종합 평가점수</span>
                                <span class="report-value" id="detail-score">-</span>
                            </div>
                            <div class="report-item">
                                <span class="report-label">공시 리스크 수준</span>
                                <span class="report-value" id="detail-disclosure">-</span>
                            </div>
                            <div class="report-item">
                                <span class="report-label">특이사항 감지 사유</span>
                                <span class="report-value" id="detail-special">-</span>
                            </div>
                        </div>
                    </div>

                    <!-- AI Report Content -->
                    <div class="report-card" style="flex-grow: 1;">
                        <div class="report-section-title">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                            Agent 심층 분석 의견서 (AI 생성)
                        </div>
                        <div class="report-markdown" id="detail-report">
                            <!-- Rendered markdown report -->
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let reportData = [];
            let currentFilter = 'ALL';

            async function fetchData() {
                try {
                    const response = await fetch('/api/data');
                    const data = await response.json();
                    reportData = data;
                    
                    // Render UI components
                    calculateKPIs(data);
                    renderTable(data);
                } catch (e) {
                    console.error(e);
                }
            }

            function calculateKPIs(data) {
                const total = data.length;
                const approved = data.filter(item => item.final_decision === 'APPROVED').length;
                const hitl = data.filter(item => item.final_decision === 'HUMAN_IN_THE_LOOP').length;
                const rejected = data.filter(item => item.final_decision === 'REJECTED').length;

                document.getElementById('kpi-total').innerText = total + '개';
                document.getElementById('kpi-approved').innerText = approved + '개';
                document.getElementById('kpi-hitl').innerText = hitl + '개';
                document.getElementById('kpi-rejected').innerText = rejected + '개';
            }

            function setFilter(filterType, element) {
                currentFilter = filterType;
                document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
                element.classList.add('active');
                filterData();
            }

            function filterData() {
                const searchQuery = document.getElementById('search-input').value.toLowerCase();
                let filtered = reportData;

                // Apply Search
                if (searchQuery) {
                    filtered = filtered.filter(item => item.company_name.toLowerCase().includes(searchQuery));
                }

                // Apply Tab Filter
                if (currentFilter !== 'ALL') {
                    filtered = filtered.filter(item => item.final_decision === currentFilter);
                }

                renderTable(filtered);
            }

            function getProgressFillClass(score) {
                if (score >= 70) return 'high';
                if (score <= 45) return 'low';
                return '';
            }

            function renderTable(data) {
                const tbody = document.getElementById('table-body');
                tbody.innerHTML = '';

                if (data.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 40px; color: var(--text-muted);">검색 조건에 맞는 제약·바이오 기업이 없습니다.</td></tr>`;
                    return;
                }
                
                data.forEach((item, index) => {
                    const tr = document.createElement('tr');
                    // Get the actual original index in reportData to map correctly to modal open function
                    const originalIndex = reportData.findIndex(p => p.company_id === item.company_id);
                    tr.onclick = () => openModal(originalIndex);
                    
                    const newsScoreDisplay = item.news_score === null 
                        ? `<span style="color:var(--text-muted); font-size: 0.8rem;">데이터 부재</span>` 
                        : `<div class="progress-container">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill ${getProgressFillClass(item.news_score)}" style="width: ${item.news_score}%"></div>
                            </div>
                            <span class="progress-val">${item.news_score.toFixed(0)}</span>
                           </div>`;

                    const specialLabel = item.special_case ? '특이사항 감지' : '해당없음';
                    const specialClass = item.special_case ? 'special' : 'normal';

                    let decisionText = item.final_decision;
                    if(decisionText === 'HUMAN_IN_THE_LOOP') decisionText = '심층심사 요망';
                    else if(decisionText === 'APPROVED') decisionText = '자동 승인';
                    else if(decisionText === 'REJECTED') decisionText = '자동 부결';

                    tr.innerHTML = `
                        <td class="comp-name">${item.company_name}</td>
                        <td><span class="badge grade-${item.grade}">${item.grade} 등급</span></td>
                        <td class="score-num" style="color: #60a5fa; font-size: 0.95rem;">${item.final_score.toFixed(1)}</td>
                        <td>
                            <div class="progress-container">
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill ${getProgressFillClass(item.financial_score)}" style="width: ${item.financial_score}%"></div>
                                </div>
                                <span class="progress-val">${item.financial_score.toFixed(0)}</span>
                            </div>
                        </td>
                        <td>${newsScoreDisplay}</td>
                        <td>
                            <div class="progress-container">
                                <div class="progress-bar-bg">
                                    <div class="progress-bar-fill ${getProgressFillClass(item.bio_score)}" style="width: ${item.bio_score}%"></div>
                                </div>
                                <span class="progress-val">${item.bio_score.toFixed(0)}</span>
                            </div>
                        </td>
                        <td><span class="badge ${specialClass}">${specialLabel}</span></td>
                        <td><span class="badge ${item.final_decision}">${decisionText}</span></td>
                    `;
                    tbody.appendChild(tr);
                });
            }

            function renderMarkdown(text) {
                if (!text) return '';
                // Escape HTML first to prevent XSS
                let html = text
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");

                // Headings
                html = html.replace(/^### (.*$)/gim, '<h4 style="color:#60a5fa; margin: 18px 0 8px 0; font-size: 1.05rem; font-weight:700;">$1</h4>');
                html = html.replace(/^## (.*$)/gim, '<h3 style="color:#fff; margin: 24px 0 12px 0; font-size: 1.15rem; font-weight:700; border-bottom:1px solid rgba(255,255,255,0.05); padding-bottom:6px;">$1</h3>');
                html = html.replace(/^# (.*$)/gim, '<h2 style="color:#fff; margin: 28px 0 16px 0; font-size: 1.3rem; font-weight:800;">$1</h2>');

                // Bold text
                html = html.replace(/\*\*(.*?)\*\*/g, '<strong style="color:#fff; font-weight:600;">$1</strong>');

                // Bullet lists
                html = html.replace(/^\s*[-*]\s+(.*$)/gim, '<li style="margin-left: 12px; margin-bottom: 6px; color: #d1d5db; list-style-type: disc;">$1</li>');

                // Line breaks
                html = html.replace(/\n/g, '<br>');

                return html;
            }

            function openModal(index) {
                const item = reportData[index];
                document.getElementById('modal-title-text').innerText = item.company_name;
                
                // Set sidebar details
                document.getElementById('detail-grade').innerHTML = `<span class="badge grade-${item.grade}">${item.grade} 등급</span>`;
                document.getElementById('detail-score').innerText = item.final_score.toFixed(1) + ' 점 / 100';
                document.getElementById('detail-disclosure').innerText = item.disclosure_risk_level;
                document.getElementById('detail-special').innerText = item.special_case ? item.special_case_reason : '없음';
                
                // Content body rendering
                document.getElementById('detail-report').innerHTML = renderMarkdown(item.final_report);
                
                const modal = document.getElementById('modal');
                modal.style.display = 'flex';
                void modal.offsetWidth;
                modal.classList.add('show');
            }

            function closeModal() {
                const modal = document.getElementById('modal');
                modal.classList.remove('show');
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 300);
            }

            fetchData();
        </script>
    </body>
    </html>
    """
    return html_content

