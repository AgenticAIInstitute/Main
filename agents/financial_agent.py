from __future__ import annotations
import logging
from models.schemas import BioAgentState, FinancialResult
from services.gemini_client import get_gemini_client

logger = logging.getLogger(__name__)


class FinancialAgent:
    """
    유동비율·부채비율·영업이익률·영업현금흐름·현금성자산·R&D비용비중·Cash Runway 기반
    바이오 기업 특화 재무 점수(0~100) 산출.
    """

    def run(self, state: BioAgentState) -> BioAgentState:
        fd = state.company_data.financial
        company_name = state.company_data.company_name
        clinical_stage = state.company_data.bio_domain.clinical_stage
        risk_factors: list[str] = []

        # 1. 유동비율 (current_ratio) - 20점 만점
        if fd.current_ratio >= 2.0:
            cr_score = 20.0
        elif fd.current_ratio >= 1.5:
            cr_score = 16.0
        elif fd.current_ratio >= 1.0:
            cr_score = 10.0
        else:
            cr_score = 3.0
            risk_factors.append(f"유동비율 위험 ({fd.current_ratio:.1f} < 1.0)")

        # 2. 부채비율 (debt_ratio) - 20점 만점
        if fd.debt_ratio <= 40:
            dr_score = 20.0
        elif fd.debt_ratio <= 70:
            dr_score = 15.0
        elif fd.debt_ratio <= 100:
            dr_score = 8.0
        else:
            dr_score = 2.0
            risk_factors.append(f"부채비율 과다 ({fd.debt_ratio:.0f}%)")

        # 3. 영업이익률 (operating_profit_margin) - 15점 만점
        if fd.operating_profit_margin >= 10.0:
            opm_score = 15.0
        elif fd.operating_profit_margin >= 0.0:
            opm_score = 10.0
        elif fd.operating_profit_margin >= -20.0:
            opm_score = 5.0
        else:
            opm_score = 2.0
            # 초기 연구개발 기업이 아닐 경우에만 리스크로 처리
            if fd.rd_expense_ratio < 20.0:
                risk_factors.append(f"영업적자 심화 (영업이익률 {fd.operating_profit_margin:.1f}%)")

        # 4. 영업현금흐름 (operating_cash_flow) - 15점 만점
        if fd.operating_cash_flow >= 500:
            ocf_score = 15.0
        elif fd.operating_cash_flow >= 200:
            ocf_score = 11.0
        elif fd.operating_cash_flow >= 0:
            ocf_score = 6.0
        else:
            ocf_score = 2.0
            risk_factors.append(f"영업현금흐름 음수 ({fd.operating_cash_flow:.0f}억원)")

        # 5. 현금성 자산 (cash_assets) - 15점 만점
        if fd.cash_assets >= 1000:
            ca_score = 15.0
        elif fd.cash_assets >= 500:
            ca_score = 11.0
        elif fd.cash_assets >= 100:
            ca_score = 6.0
        else:
            ca_score = 2.0
            risk_factors.append(f"현금성 자산 부족 ({fd.cash_assets:.0f}억원)")

        # 6. R&D 비용 비중 (rd_expense_ratio) - 10점 만점
        if fd.rd_expense_ratio >= 20.0:
            rd_score = 10.0
        elif fd.rd_expense_ratio >= 10.0:
            rd_score = 7.0
        elif fd.rd_expense_ratio >= 5.0:
            rd_score = 4.0
        else:
            rd_score = 1.0
            risk_factors.append(f"R&D 투자 부족 (R&D 비중 {fd.rd_expense_ratio:.1f}%)")

        # 7. Cash Runway (cash_runway_months) - 5점 만점
        if fd.cash_runway_months >= 24:
            runway_score = 5.0
        elif fd.cash_runway_months >= 12:
            runway_score = 3.0
        elif fd.cash_runway_months >= 6:
            runway_score = 1.0
        else:
            runway_score = 0.0
            risk_factors.append(f"Cash Runway 위험 ({fd.cash_runway_months:.0f}개월)")

        # 기본 재무 합산 점수 계산
        base_score = cr_score + dr_score + opm_score + ocf_score + ca_score + rd_score + runway_score

        # 🌟 바이오 벤처 특화 우대/보정 로직 (Deficit-R&D Protection)
        # 영업적자 상태임에도 R&D 비중이 높고 Cash Runway가 충분하면 가점 부여 (+5점)
        if fd.operating_profit_margin < 0 and fd.rd_expense_ratio >= 20.0 and fd.cash_runway_months >= 12:
            base_score += 5.0
            risk_factors.append("적자임에도 높은 R&D 투자와 안정적 Runway 보유 (Deficit-R&D Protection 가점 적용)")

        # 최종 점수를 0~100점 사이로 캡(Cap)을 씌웁니다.
        final_score = max(0.0, min(100.0, base_score))
        final_score = max(0.0, min(100.0, base_score))

        state.financial_result = FinancialResult(
            financial_score=round(final_score, 2),
            risk_factors=risk_factors,
        )

        logger.info(
            "[FinancialAgent] %s | score=%.1f | risks=%s",
            company_name, final_score, risk_factors
        )
        return state