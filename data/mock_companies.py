"""
Mock company data covering 7 required test cases:
1. A등급 승인 기업         - 셀트리온바이오 (score ~89)
2. B등급 승인 기업         - 한미바이오텍 (score ~77)
3. C등급 HITL 기업        - 메디파마솔루션 (score ~61)
4. D등급 부결 기업         - 이노바이오케어 (score ~47)
5. E등급 부결 기업         - 파마리스크코리아 (score ~27)
6. 재무 낮+뉴스 좋 → HITL  - 뉴로바이오시스 (financial=45, news=82)
7. 재무 높+뉴스 없음 → HITL - 제넥신알파 (financial=82, news=None)
"""
from models.schemas import (
    CompanyData, FinancialData, NewsItem, BioDomainData, DisclosureData
)

MOCK_COMPANIES: list[CompanyData] = [
    # 1. A등급 승인 기업
    CompanyData(
        company_id="COMP001",
        company_name="셀트리온바이오",
        financial=FinancialData(
            current_ratio=2.5,
            debt_ratio=38.0,
            operating_cash_flow=850.0,
            cash_assets=1200.0,
            cash_runway_months=36.0,
        ),
        news=[
            NewsItem(title="셀트리온바이오, FDA 품목허가 획득", date="2025-12-01",
                     content="FDA 승인을 받아 미국 시장 진출 확정"),
            NewsItem(title="기술수출 계약 체결 1조 규모", date="2025-11-15",
                     content="글로벌 빅파마와 기술수출 계약 성사"),
            NewsItem(title="임상 3상 성공 발표", date="2025-10-20",
                     content="핵심 파이프라인 임상 3상 성공적 완료"),
        ],
        bio_domain=BioDomainData(
            clinical_stage="Approved",
            pipeline_count=8,
            has_tech_export=True,
            has_patent=True,
            core_pipeline_dependency=0.35,
        ),
        disclosure=DisclosureData(risk_keywords=[]),
    ),

    # 2. B등급 승인 기업
    CompanyData(
        company_id="COMP002",
        company_name="한미바이오텍",
        financial=FinancialData(
            current_ratio=1.8,
            debt_ratio=52.0,
            operating_cash_flow=420.0,
            cash_assets=580.0,
            cash_runway_months=24.0,
        ),
        news=[
            NewsItem(title="한미바이오텍 특허 취득 완료", date="2025-11-10",
                     content="핵심 신약 특허 국내외 동시 취득"),
            NewsItem(title="임상 2상 긍정적 결과 발표", date="2025-10-05",
                     content="주요 파이프라인 임상 2상 성공적 완료"),
        ],
        bio_domain=BioDomainData(
            clinical_stage="Phase 3",
            pipeline_count=5,
            has_tech_export=False,
            has_patent=True,
            core_pipeline_dependency=0.50,
        ),
        disclosure=DisclosureData(risk_keywords=[]),
    ),

    # 3. C등급 HITL 기업 (목표 점수 55~70 → ~57)
    # financial=67, news=47(특허취득+임상지연), bio=50, disc=MEDIUM(60)
    # score = 0.4*67 + 0.25*47 + 0.25*50 + 0.1*60 = 26.8+11.75+12.5+6 = 57.05
    CompanyData(
        company_id="COMP003",
        company_name="메디파마솔루션",
        financial=FinancialData(
            current_ratio=1.6,
            debt_ratio=60.0,
            operating_cash_flow=130.0,
            cash_assets=250.0,
            cash_runway_months=18.0,
        ),
        news=[
            NewsItem(title="메디파마솔루션 특허 취득 완료", date="2025-10-10",
                     content="핵심 신약 특허 국내 취득"),
            NewsItem(title="메디파마솔루션, 임상 지연 발표", date="2025-11-20",
                     content="핵심 파이프라인 임상 일정 6개월 지연"),
        ],
        bio_domain=BioDomainData(
            clinical_stage="Phase 2",
            pipeline_count=5,
            has_tech_export=False,
            has_patent=True,
            core_pipeline_dependency=0.55,
        ),
        disclosure=DisclosureData(risk_keywords=["유상증자 반복"]),
    ),

    # 4. D등급 부결 기업 (목표 점수 40~55 → ~42)
    # financial=54, news=35(임상실패), bio=23, disc=MEDIUM(60)
    # score = 0.4*54 + 0.25*35 + 0.25*23 + 0.1*60 = 21.6+8.75+5.75+6 = 42.1
    CompanyData(
        company_id="COMP004",
        company_name="이노바이오케어",
        financial=FinancialData(
            current_ratio=1.1,
            debt_ratio=70.0,
            operating_cash_flow=20.0,
            cash_assets=150.0,
            cash_runway_months=12.0,
        ),
        news=[
            NewsItem(title="이노바이오케어 임상 실패", date="2025-10-15",
                     content="주요 파이프라인 임상 2상 실패 발표"),
        ],
        bio_domain=BioDomainData(
            clinical_stage="Phase 2",
            pipeline_count=2,
            has_tech_export=False,
            has_patent=False,
            core_pipeline_dependency=0.78,
        ),
        disclosure=DisclosureData(risk_keywords=["유상증자 반복"]),
    ),

    # 5. E등급 부결 기업
    CompanyData(
        company_id="COMP005",
        company_name="파마리스크코리아",
        financial=FinancialData(
            current_ratio=0.6,
            debt_ratio=145.0,
            operating_cash_flow=-380.0,
            cash_assets=40.0,
            cash_runway_months=4.0,
        ),
        news=[
            NewsItem(title="파마리스크코리아 횡령 혐의 임원 구속", date="2025-12-01",
                     content="최대주주 횡령 혐의로 검찰 조사"),
            NewsItem(title="감사의견 거절 통보", date="2025-11-28",
                     content="회계법인으로부터 감사의견 거절 통보"),
            NewsItem(title="상장폐지 사유 발생 통보", date="2025-11-25",
                     content="거래소로부터 상장폐지 사유 발생 통보"),
        ],
        bio_domain=BioDomainData(
            clinical_stage="Phase 1",
            pipeline_count=1,
            has_tech_export=False,
            has_patent=False,
            core_pipeline_dependency=0.95,
        ),
        disclosure=DisclosureData(risk_keywords=["관리종목", "계속기업 불확실성", "감사의견 한정", "최대주주 변경"]),
    ),

    # 6. 재무 낮 + 뉴스 좋 → special_case (condition a) → HITL
    CompanyData(
        company_id="COMP006",
        company_name="뉴로바이오시스",
        financial=FinancialData(
            current_ratio=0.95,
            debt_ratio=82.0,
            operating_cash_flow=-45.0,
            cash_assets=95.0,
            cash_runway_months=10.0,
        ),
        news=[
            NewsItem(title="뉴로바이오시스, FDA 승인 획득", date="2025-12-05",
                     content="FDA로부터 희귀질환 치료제 신속승인 획득"),
            NewsItem(title="기술수출 5000억 규모 계약 체결", date="2025-11-30",
                     content="유럽 대형 제약사와 기술수출 계약 성사"),
            NewsItem(title="임상 성공으로 주가 급등", date="2025-11-10",
                     content="임상 3상 성공으로 기업가치 재평가"),
        ],
        bio_domain=BioDomainData(
            clinical_stage="Approved",
            pipeline_count=4,
            has_tech_export=True,
            has_patent=True,
            core_pipeline_dependency=0.75,
        ),
        disclosure=DisclosureData(risk_keywords=[]),
    ),

    # 7. 재무 높 + 뉴스 없음 → special_case (condition b, e) → HITL
    CompanyData(
        company_id="COMP007",
        company_name="제넥신알파",
        financial=FinancialData(
            current_ratio=2.2,
            debt_ratio=35.0,
            operating_cash_flow=620.0,
            cash_assets=980.0,
            cash_runway_months=30.0,
        ),
        news=None,
        bio_domain=BioDomainData(
            clinical_stage="Phase 3",
            pipeline_count=6,
            has_tech_export=True,
            has_patent=True,
            core_pipeline_dependency=0.45,
        ),
        disclosure=DisclosureData(risk_keywords=[]),
    ),
]

COMPANIES_BY_ID: dict[str, CompanyData] = {c.company_id: c for c in MOCK_COMPANIES}
