# BioCredit Agent

바이오 산업 특화 기업 여신 대출 의사결정 지원 Agentic AI 프로토타입입니다.

## 실행 방법

1. 의존성 패키지 설치
```bash
pip install -r requirements.txt
```

2. 환경변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 발급받은 Gemini API Key를 입력합니다.
(API 키가 없어도 기본 로직으로 정상 동작합니다)
```bash
cp .env.example .env
# .env 파일 편집 후 API 키 입력
```

3. 애플리케이션 실행
```bash
uvicorn app:app --reload
```

4. 웹 브라우저에서 확인
[http://localhost:8000](http://localhost:8000) 접속

## 핵심 에이전트 설명
- **PlannerAgent**: 분석 대상 기업 목록 수집
- **FinancialAgent**: 재무 데이터를 기반으로 재무 건전성 평가
- **NewsAgent**: 뉴스 키워드 기반 모멘텀 분석 (데이터 부재 시 불확실성 처리)
- **BioDomainAgent**: 파이프라인, 임상 단계, 특허 등 도메인 특화 리스크 분석
- **DisclosureAgent**: 공시 데이터 기반 마켓 리스크 평가
- **RiskScoringAgent**: 통합 점수 산출 및 등급(A~E) 부여
- **SupervisoryReviewAgent**: 에이전트 간 결과 모순 및 특이사항(Human-in-the-loop 대상) 감지
- **LoanDecisionAgent**: 승인, 부결, HITL 최종 결정
- **ReportWriterAgent**: Gemini API를 활용한 최종 심사 보고서 작성
