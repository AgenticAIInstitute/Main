from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel
from enum import Enum


class GradeEnum(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class DisclosureRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class FinalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"


class FinancialData(BaseModel):
    current_ratio: float
    debt_ratio: float
    operating_cash_flow: float
    cash_assets: float
    cash_runway_months: float


class NewsItem(BaseModel):
    title: str
    date: str
    content: str


class BioDomainData(BaseModel):
    clinical_stage: str
    pipeline_count: int
    has_tech_export: bool
    has_patent: bool
    core_pipeline_dependency: float


class DisclosureData(BaseModel):
    risk_keywords: list[str]


class CompanyData(BaseModel):
    company_id: str
    company_name: str
    financial: FinancialData
    news: Optional[list[NewsItem]]
    bio_domain: BioDomainData
    disclosure: DisclosureData


class FinancialResult(BaseModel):
    financial_score: float
    risk_factors: list[str]


class NewsResult(BaseModel):
    news_score: Optional[float]
    positive_keywords: list[str]
    negative_keywords: list[str]
    negative_critical_event: bool
    missing_news: bool


class BioDomainResult(BaseModel):
    bio_score: float
    domain_risks: list[str]


class DisclosureResult(BaseModel):
    disclosure_risk_level: DisclosureRiskLevel
    detected_keywords: list[str]


class RiskScoreResult(BaseModel):
    final_score: float
    grade: GradeEnum
    missing_news: bool
    score_breakdown: dict[str, Any]


class SupervisoryResult(BaseModel):
    special_case:        bool
    special_case_reason: str
    flags:               list[str]
    original_grade:      Optional[str] = None
    adjusted_grade:      Optional[str] = None
    llm_called:          bool = False
    is_error:            bool = False


class LoanDecisionResult(BaseModel):
    final_decision: FinalDecision
    decision_reason: str


class CompanyReport(BaseModel):
    company_id: str
    company_name: str
    grade: GradeEnum
    final_score: float
    financial_score: float
    news_score: Optional[float]
    bio_score: float
    disclosure_risk_level: DisclosureRiskLevel
    special_case: bool
    special_case_reason: str
    final_decision: FinalDecision
    decision_reason: str
    report_text: str


class BioAgentState(BaseModel):
    company_data: CompanyData
    financial_result: Optional[FinancialResult] = None
    news_result: Optional[NewsResult] = None
    bio_domain_result: Optional[BioDomainResult] = None
    disclosure_result: Optional[DisclosureResult] = None
    risk_score_result: Optional[RiskScoreResult] = None
    supervisory_result: Optional[SupervisoryResult] = None
    loan_decision_result: Optional[LoanDecisionResult] = None
    report: Optional[CompanyReport] = None
    errors: list[str] = []

    # 흐름 제어 필드
    restart_required:   bool = False
    restart_count:      int  = 0
    needs_human_review: bool = False
