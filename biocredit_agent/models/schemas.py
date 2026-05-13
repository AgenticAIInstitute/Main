from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CompanyData(BaseModel):
    id: str
    name: str
    financials: dict  # e.g., {"current_ratio": 1.5, "debt_ratio": 120, "operating_cash_flow": 500, "cash_and_equivalents": 1000, "cash_runway_months": 24}
    news: Optional[List[str]] = None
    bio_data: dict # e.g., {"clinical_stage": "Phase 3", "pipeline_count": 3, "tech_export": True, "has_patent": True, "core_pipeline_dependency": 0.8}
    disclosures: List[str]

class AgentResult(BaseModel):
    company_id: str = ""
    company_name: str = ""
    
    financial_score: float = 0.0
    financial_risks: List[str] = Field(default_factory=list)
    
    news_score: Optional[float] = None
    news_keywords: dict = Field(default_factory=dict)
    missing_news: bool = False
    
    bio_score: float = 0.0
    bio_risks: List[str] = Field(default_factory=list)
    
    disclosure_risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    
    final_score: float = 0.0
    grade: str = ""
    
    special_case: bool = False
    special_case_reason: str = ""
    negative_critical_event: bool = False
    
    final_decision: Literal["APPROVED", "REJECTED", "HUMAN_IN_THE_LOOP", "PENDING"] = "PENDING"
    decision_reason: str = ""
    
    final_report: str = ""
