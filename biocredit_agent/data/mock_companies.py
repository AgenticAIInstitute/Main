from biocredit_agent.models.schemas import CompanyData

MOCK_COMPANIES = [
    CompanyData(
        id="C001",
        name="에이바이오 (A등급 승인)",
        financials={"current_ratio": 2.5, "debt_ratio": 50, "operating_cash_flow": 1500, "cash_and_equivalents": 5000, "cash_runway_months": 36},
        news=["FDA 승인 획득", "글로벌 기술수출 계약 체결"],
        bio_data={"clinical_stage": "NDA", "pipeline_count": 5, "tech_export": True, "has_patent": True, "core_pipeline_dependency": 0.4},
        disclosures=[]
    ),
    CompanyData(
        id="C002",
        name="비파마 (B등급 승인)",
        financials={"current_ratio": 1.8, "debt_ratio": 80, "operating_cash_flow": 500, "cash_and_equivalents": 2000, "cash_runway_months": 24},
        news=["임상 2상 순항 중", "신규 특허 취득"],
        bio_data={"clinical_stage": "Phase 2", "pipeline_count": 3, "tech_export": False, "has_patent": True, "core_pipeline_dependency": 0.6},
        disclosures=[]
    ),
    CompanyData(
        id="C003",
        name="씨제약 (C등급 HITL)",
        financials={"current_ratio": 1.2, "debt_ratio": 120, "operating_cash_flow": -200, "cash_and_equivalents": 800, "cash_runway_months": 12},
        news=["임상 1상 환자 모집", "자금 조달 계획 발표"],
        bio_data={"clinical_stage": "Phase 1", "pipeline_count": 2, "tech_export": False, "has_patent": False, "core_pipeline_dependency": 0.8},
        disclosures=["유상증자 결정"]
    ),
    CompanyData(
        id="C004",
        name="디신약 (D등급 부결)",
        financials={"current_ratio": 0.8, "debt_ratio": 200, "operating_cash_flow": -800, "cash_and_equivalents": 300, "cash_runway_months": 6},
        news=["임상 지연 우려", "추가 임상 비용 부담"],
        bio_data={"clinical_stage": "Pre-clinical", "pipeline_count": 1, "tech_export": False, "has_patent": False, "core_pipeline_dependency": 1.0},
        disclosures=["최대주주 변경"]
    ),
    CompanyData(
        id="C005",
        name="이사이언스 (E등급 부결)",
        financials={"current_ratio": 0.4, "debt_ratio": 500, "operating_cash_flow": -2000, "cash_and_equivalents": 50, "cash_runway_months": 2},
        news=["임상 실패 공식화", "횡령 의혹 수사"],
        bio_data={"clinical_stage": "Phase 3 (Failed)", "pipeline_count": 1, "tech_export": False, "has_patent": False, "core_pipeline_dependency": 1.0},
        disclosures=["감사의견 한정", "계속기업 불확실성", "관리종목 지정"]
    ),
    CompanyData(
        id="C006",
        name="에프바이오 (재무저조 뉴스우수)",
        financials={"current_ratio": 0.9, "debt_ratio": 250, "operating_cash_flow": -1000, "cash_and_equivalents": 400, "cash_runway_months": 5},
        news=["기적의 항암제 FDA 승인 완료", "초대형 기술수출 잭팟"],
        bio_data={"clinical_stage": "Approved", "pipeline_count": 2, "tech_export": True, "has_patent": True, "core_pipeline_dependency": 0.5},
        disclosures=[]
    ),
    CompanyData(
        id="C007",
        name="지테라퓨틱스 (재무우수 뉴스없음)",
        financials={"current_ratio": 3.0, "debt_ratio": 30, "operating_cash_flow": 2000, "cash_and_equivalents": 8000, "cash_runway_months": 48},
        news=None,
        bio_data={"clinical_stage": "Phase 2", "pipeline_count": 4, "tech_export": True, "has_patent": True, "core_pipeline_dependency": 0.3},
        disclosures=[]
    )
]
