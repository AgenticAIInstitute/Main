from __future__ import annotations
from typing import Optional, Any
from pydantic import AliasChoices, BaseModel, Field
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
    operating_profit_margin: float  # 영업이익률 (%)
    rd_expense_ratio: float         # R&D 비용 비중 (%)


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
    ticker_code: str                 # 종목코드 (예: 091990)
    industry_category: str           # 산업 분류 (예: 제약/바이오)
    market_cap: float                # 시가총액 (억원 단위)
    financial: FinancialData
    news: Optional[list[NewsItem]]
    bio_domain: BioDomainData
    disclosure_data: DisclosureData = Field(
        validation_alias=AliasChoices("disclosure_data", "disclosure")
    )

    @property
    def disclosure(self) -> DisclosureData:
        return self.disclosure_data


class FinancialResult(BaseModel):
    financial_score: float
    risk_factors: list[str]


class NewsResult(BaseModel):
    news_score: Optional[float]
    positive_keywords: list[str]
    negative_keywords: list[str]
    negative_critical_event: bool
    missing_news: bool
    keyword_score: Optional[float] = None
    keyword_hits: int = 0
    llm_score: Optional[float] = None
    llm_summary: str = ""
    merge_weights: str = ""


class BioDomainResult(BaseModel):
    bio_domain_score: float = Field(
        validation_alias=AliasChoices("bio_domain_score", "bio_score")
    )
    domain_risks: list[str]
    summary: str = ""

    @property
    def bio_score(self) -> float:
        return self.bio_domain_score


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
    financial_risk_factors: list[str] = Field(default_factory=list)
    news_positive_keywords: list[str] = Field(default_factory=list)
    news_negative_keywords: list[str] = Field(default_factory=list)
    news_negative_critical_event: bool = False
    news_keyword_score: Optional[float] = None
    news_keyword_hits: int = 0
    news_llm_score: Optional[float] = None
    news_llm_summary: str = ""
    news_merge_weights: str = ""
    bio_domain_risks: list[str] = Field(default_factory=list)
    bio_domain_summary: str = ""
    disclosure_detected_keywords: list[str] = Field(default_factory=list)


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
