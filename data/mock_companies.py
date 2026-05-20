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
        ticker_code="068270",
        industry_category="바이오시밀러 및 제약",
        market_cap=320000.0,  # 32조원
        financial=FinancialData(
            current_ratio=2.5,
            debt_ratio=38.0,
            operating_cash_flow=850.0,
            cash_assets=1200.0,
            cash_runway_months=36.0,
            operating_profit_margin=35.5,
            rd_expense_ratio=15.0,
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
        ticker_code="128940",
        industry_category="신약 개발 및 제약",
        market_cap=35000.0,  # 3.5조원
        financial=FinancialData(
            current_ratio=1.8,
            debt_ratio=52.0,
            operating_cash_flow=420.0,
            cash_assets=580.0,
            cash_runway_months=24.0,
            operating_profit_margin=12.0,
            rd_expense_ratio=18.5,
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

    # 3. C등급 HITL 기업
    CompanyData(
        company_id="COMP003",
        company_name="메디파마솔루션",
        ticker_code="206650",
        industry_category="세포치료제 개발",
        market_cap=8500.0,  # 8500억원
        financial=FinancialData(
            current_ratio=1.6,
            debt_ratio=60.0,
            operating_cash_flow=130.0,
            cash_assets=250.0,
            cash_runway_months=18.0,
            operating_profit_margin=-5.2,
            rd_expense_ratio=30.0,
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

    # 4. D등급 부결 기업
    CompanyData(
        company_id="COMP004",
        company_name="이노바이오케어",
        ticker_code="086890",
        industry_category="유전자 치료제 개발",
        market_cap=3200.0,  # 3200억원
        financial=FinancialData(
            current_ratio=1.1,
            debt_ratio=70.0,
            operating_cash_flow=20.0,
            cash_assets=150.0,
            cash_runway_months=12.0,
            operating_profit_margin=-25.0,
            rd_expense_ratio=45.0,
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
        ticker_code="950130",
        industry_category="줄기세포 치료제",
        market_cap=450.0,  # 450억원
        financial=FinancialData(
            current_ratio=0.6,
            debt_ratio=145.0,
            operating_cash_flow=-380.0,
            cash_assets=40.0,
            cash_runway_months=4.0,
            operating_profit_margin=-120.0,
            rd_expense_ratio=5.0,
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
        ticker_code="298040",
        industry_category="뇌질환 치료제 개발",
        market_cap=4200.0,  # 4200억원
        financial=FinancialData(
            current_ratio=0.95,
            debt_ratio=82.0,
            operating_cash_flow=-45.0,
            cash_assets=95.0,
            cash_runway_months=10.0,
            operating_profit_margin=-45.0,
            rd_expense_ratio=55.0,
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
        ticker_code="095700",
        industry_category="면역 항암제 개발",
        market_cap=9500.0,  # 9500억원
        financial=FinancialData(
            current_ratio=2.2,
            debt_ratio=35.0,
            operating_cash_flow=620.0,
            cash_assets=980.0,
            cash_runway_months=30.0,
            operating_profit_margin=15.0,
            rd_expense_ratio=22.0,
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

# 코스닥/코스피 바이오 및 제약 분야 상위 50개 확장을 위한 43개사 원시 메타데이터 정의
extra_raw = [
    ("COMP008", "HLB", "028300", "신약 개발", 50000.0, "Phase 3", 6, True),
    ("COMP009", "알테오젠", "196170", "바이오 플랫폼", 45000.0, "Approved", 5, True),
    ("COMP010", "휴젤", "145020", "보툴리눔 및 톡신", 25000.0, "Approved", 3, False),
    ("COMP011", "삼천당제약", "000250", "안과 제약 및 바이오시밀러", 18000.0, "Phase 3", 4, True),
    ("COMP012", "에스티팜", "237690", "올리고 CDMO 및 제약", 15000.0, "Phase 3", 3, False),
    ("COMP013", "리가켐바이오", "141080", "ADC 신약 및 플랫폼", 16000.0, "Phase 2", 7, True),
    ("COMP014", "펩트론", "086520", "약효지속성 의약품", 12000.0, "Phase 2", 4, True),
    ("COMP015", "에이비엘바이오", "298040", "이중항체 면역항암제", 14000.0, "Phase 2", 5, True),
    ("COMP016", "셀트리온제약", "068760", "일반/전문 의약품", 22000.0, "Approved", 4, False),
    ("COMP017", "메디포스트", "206650", "줄기세포 세포치료제", 4500.0, "Phase 3", 3, False),
    ("COMP018", "지아이이노베이션", "358570", "이중융합단백질 신약", 6200.0, "Phase 2", 4, True),
    ("COMP019", "차바이오텍", "085660", "세포치료 및 헬스케어", 8700.0, "Phase 2", 3, False),
    ("COMP020", "오스코텍", "039200", "표적항암제 연구개발", 7500.0, "Phase 3", 2, True),
    ("COMP021", "헬릭스미스", "084990", "유전자 치료제 신약", 3500.0, "Phase 3", 2, False),
    ("COMP022", "신라젠", "215600", "항암 바이러스 치료제", 4200.0, "Phase 2", 2, False),
    ("COMP023", "동국제약", "086450", "일반의약품 및 전문 제약", 9800.0, "Approved", 2, False),
    ("COMP024", "대원제약", "003220", "전통 제약 및 호흡기 치료", 4500.0, "Approved", 3, False),
    ("COMP025", "보령", "003850", "항암제 전문 제약", 8200.0, "Approved", 4, False),
    ("COMP026", "유한양행", "000100", "종합 전통 제약 및 신약", 48000.0, "Approved", 8, True),
    ("COMP027", "녹십자", "006280", "백신 및 혈액제제 제약", 18000.0, "Approved", 5, False),
    ("COMP028", "대웅제약", "069620", "보툴리눔 톡신 및 전문제약", 15000.0, "Approved", 6, True),
    ("COMP029", "종근당", "185750", "전통 전문의약품 및 R&D", 14000.0, "Approved", 7, True),
    ("COMP030", "광동제약", "009290", "일반의약품 및 드링크류", 4800.0, "Approved", 1, False),
    ("COMP031", "동아에스티", "170900", "전문의약품 및 신약개발", 5200.0, "Phase 3", 4, True),
    ("COMP032", "JW중외제약", "001060", "수액 및 수입신약 전문제약", 6800.0, "Approved", 3, False),
    ("COMP033", "일동제약", "249420", "일반의약품 및 유산균 제약", 3500.0, "Approved", 2, False),
    ("COMP034", "보로노이", "310210", "인산화효소 저해 표적항암제", 9200.0, "Phase 1", 5, True),
    ("COMP035", "큐리옥스바이오", "445680", "세포 분석 자동화 의료장비", 3200.0, "Approved", 2, False),
    ("COMP036", "유틸렉스", "263050", "면역 세포치료제 신약", 2100.0, "Phase 2", 3, False),
    ("COMP037", "앱클론", "174900", "항체 플랫폼 및 신약", 2800.0, "Phase 1", 4, True),
    ("COMP038", "지놈앤컴퍼니", "314130", "마이크로바이옴 항암 신약", 1800.0, "Phase 2", 3, False),
    ("COMP039", "고바이오랩", "348150", "마이크로바이옴 대사성 신약", 1500.0, "Phase 2", 2, False),
    ("COMP040", "올릭스", "226950", "RNA 간섭 플랫폼 신약", 2400.0, "Phase 2", 3, True),
    ("COMP041", "압타바이오", "293780", "난치성 질환 녹스 저해제", 1900.0, "Phase 2", 4, False),
    ("COMP042", "티움바이오", "321550", "희귀 질환 치료제 신약", 2100.0, "Phase 2", 3, False),
    ("COMP043", "엔지켐생명과학", "183490", "원료의약품 및 세포치료제", 1600.0, "Phase 2", 2, False),
    ("COMP044", "안트로젠", "065660", "줄기세포 기반 치료제", 1700.0, "Phase 3", 2, False),
    ("COMP045", "바이오니아", "064550", "유전자 분석 및 분자진단", 5200.0, "Approved", 3, False),
    ("COMP046", "바디텍메드", "208470", "면역 진단 카트리지 및 POCT", 3800.0, "Approved", 2, False),
    ("COMP047", "아이센스", "099190", "자가혈당 측정기 제조", 5800.0, "Approved", 1, False),
    ("COMP048", "랩지노믹스", "084650", "NGS 분자진단 서비스", 2200.0, "Approved", 2, False),
    ("COMP049", "수젠텍", "253840", "다중 분자진단 키트", 1200.0, "Approved", 1, False),
    ("COMP050", "바이오에프디엔씨", "251350", "식물세포 플랫폼 바이오소재", 1500.0, "Approved", 2, False)
]

for cid, name, ticker, ind, mcap, stage, p_count, te in extra_raw:
    # 기본 고품질 baseline 모의 수치 적용 (DART 성공 시 오버라이드)
    comp = CompanyData(
        company_id=cid,
        company_name=name,
        ticker_code=ticker,
        industry_category=ind,
        market_cap=mcap,
        financial=FinancialData(
            current_ratio=1.65,
            debt_ratio=48.0,
            operating_cash_flow=150.0,
            cash_assets=350.0,
            cash_runway_months=20.0,
            operating_profit_margin=-12.5,
            rd_expense_ratio=22.5,
        ),
        news=[
            NewsItem(
                title=f"{name}, 글로벌 바이오 메드 세미나 참가 발표",
                date="2025-11-20",
                content=f"{name}이 글로벌 파트너십 확대를 위해 핵심 신약 파이프라인 소개를 마쳤습니다."
            ),
        ],
        bio_domain=BioDomainData(
            clinical_stage=stage,
            pipeline_count=p_count,
            has_tech_export=te,
            has_patent=True,
            core_pipeline_dependency=0.45,
        ),
        disclosure=DisclosureData(risk_keywords=[]),
    )
    MOCK_COMPANIES.append(comp)

COMPANIES_BY_ID = {c.company_id: c for c in MOCK_COMPANIES}

