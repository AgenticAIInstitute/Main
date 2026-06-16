# BioCredit Agent

코스닥 바이오·제약 기업 특화 **여신 심사 의사결정 지원 AI 시스템**

LangGraph 9-Agent 파이프라인으로 재무·뉴스·바이오 도메인·공시 리스크를 종합 분석하고,  
A~E 등급을 산출하여 승인 / 부결 / Human-in-the-Loop를 자동 판정합니다.

---

## 폴더 구조

```
biocredit_agent/
├── app.py                        # FastAPI 앱 + LangGraph 워크플로우
├── agents/
│   ├── planner_agent.py          # 1. 분석 계획 수립
│   ├── financial_agent.py        # 2. 재무 점수 산출
│   ├── news_agent.py             # 3. 뉴스 키워드 분석
│   ├── bio_domain_agent.py       # 4. 바이오 도메인 점수
│   ├── disclosure_agent.py       # 5. 공시 리스크 판정
│   ├── risk_scoring_agent.py     # 6. 가중 합산 점수·등급
│   ├── supervisory_review_agent.py  # 7. 관리·감독 특이사항 감지
│   ├── loan_decision_agent.py    # 8. 최종 여신 판단
│   └── report_writer_agent.py   # 9. 보고서 생성
├── data/
│   └── mock_companies.py         # 인메모리 Mock 기업 데이터 (7개사)
├── services/
│   └── openai_client.py          # OpenAI API 클라이언트
├── models/
│   └── schemas.py                # Pydantic 데이터 모델
├── requirements.txt
├── .env.example
└── README.md
```

---

## 설치 방법

```bash
cd biocredit_agent
pip install -r requirements.txt
```

---

## 실행 방법

```bash
# 방법 1: 직접 실행
python app.py

# 방법 2: uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000
```

브라우저에서 `http://localhost:8000` 접속

---

## 환경변수 설정

`.env.example`을 복사하여 `.env`를 생성하고 키를 입력합니다:

```
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

- `OPENAI_API_KEY`: OpenAI Platform에서 발급 (없어도 앱 정상 동작)
- `OPENAI_MODEL`: 사용할 OpenAI 모델 (기본값: gpt-5.4-mini)

---

## 주요 Agent 설명

| Agent | 역할 |
|-------|------|
| **PlannerAgent** | 분석 대상 기업 목록 정리, 누락 데이터 확인 |
| **FinancialAgent** | 유동비율·부채비율·영업현금흐름·현금성자산·Cash Runway → 재무점수(0~100) |
| **NewsAgent** | 긍/부정 키워드 분석 → 뉴스점수(0~100), 뉴스 없으면 None(판단 불확실) |
| **BioDomainAgent** | 임상단계·파이프라인·기술수출·특허·의존도 → 바이오점수(0~100) |
| **DisclosureAgent** | 공시 리스크 문구 → LOW / MEDIUM / HIGH |
| **RiskScoringAgent** | 가중합산(재무40+뉴스25+바이오25+공시10) → 최종점수 + A~E 등급 |
| **SupervisoryReviewAgent** | 점수 간 모순·데이터 누락·치명적 리스크 감지 → special_case 판정 |
| **LoanDecisionAgent** | 등급 + special_case 기반 최종 판단 |
| **ReportWriterAgent** | OpenAI AI 또는 템플릿 기반 한국어 보고서 생성 |

---

## 최종 판단 로직

```
1. special_case == True  →  HUMAN_IN_THE_LOOP
2. grade == "C"          →  HUMAN_IN_THE_LOOP
3. grade in ["A", "B"]   →  APPROVED
4. grade in ["D", "E"]   →  REJECTED
```

**special_case 감지 조건 (하나라도 해당 시)**

| 조건 | 설명 |
|------|------|
| a | 재무점수≤50 AND 뉴스점수≥75 (점수 간 모순) |
| b | 재무점수≥75 AND 뉴스데이터 없음 |
| c | 재무·뉴스·바이오 점수 간 최대 편차 ≥35점 |
| d | 횡령·상장폐지·감사의견거절 등 치명적 이벤트 |
| e | 뉴스 없음 + A/B등급 (고등급 신뢰도 부족) |
| f | 공시리스크 HIGH |

---

## Mock 데이터 케이스

| 기업 | 예상 등급 | 최종 판단 | 설명 |
|------|----------|----------|------|
| 셀트리온바이오 | A | 승인 | FDA 승인, 기술수출, 우수 재무 |
| 한미바이오텍 | B | 승인 | 특허·임상 3상, 안정적 재무 |
| 메디파마솔루션 | C | 전문가 검토 | 경계 구간, 임상 지연 |
| 이노바이오케어 | D | 부결 | 임상 실패, 현금 부족 |
| 파마리스크코리아 | E | 부결 | 횡령·감사거절·관리종목 |
| 뉴로바이오시스 | C→특이 | 전문가 검토 | 재무 낮음+뉴스 좋음 (모순) |
| 제넥신알파 | B→특이 | 전문가 검토 | 재무 높음+뉴스 없음 |

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/` | 전체 기업 목록 대시보드 (HTML) |
| GET | `/companies/{company_id}` | 기업 상세 보고서 (HTML) |
| GET | `/api/companies` | 전체 기업 분석 결과 (JSON) |
| GET | `/api/companies/{company_id}` | 특정 기업 분석 결과 (JSON) |
