from __future__ import annotations
import logging
from models.schemas import BioAgentState, FinancialResult

logger = logging.getLogger(__name__)


class FinancialAgent:
    """유동비율·부채비율·영업현금흐름·현금성자산·Cash Runway 기반 재무 점수 산출."""

    def run(self, state: BioAgentState) -> BioAgentState:
        fd = state.company_data.financial
        company_name = state.company_data.company_name
        risk_factors: list[str] = []
        score = 100.0

        # 유동비율 (current_ratio)
        if fd.current_ratio >= 2.0:
            cr_score = 25.0
        elif fd.current_ratio >= 1.5:
            cr_score = 20.0
        elif fd.current_ratio >= 1.0:
            cr_score = 12.0
        else:
            cr_score = 4.0
            risk_factors.append(f"유동비율 위험 ({fd.current_ratio:.1f} < 1.0)")

        # 부채비율 (debt_ratio) — 낮을수록 좋음
        if fd.debt_ratio <= 40:
            dr_score = 25.0
        elif fd.debt_ratio <= 70:
            dr_score = 18.0
        elif fd.debt_ratio <= 100:
            dr_score = 10.0
        else:
            dr_score = 3.0
            risk_factors.append(f"부채비율 과다 ({fd.debt_ratio:.0f}%)")

        # 영업현금흐름 (operating_cash_flow)
        if fd.operating_cash_flow >= 500:
            ocf_score = 20.0
        elif fd.operating_cash_flow >= 200:
            ocf_score = 15.0
        elif fd.operating_cash_flow >= 0:
            ocf_score = 8.0
        else:
            ocf_score = 2.0
            risk_factors.append(f"영업현금흐름 음수 ({fd.operating_cash_flow:.0f}억원)")

        # 현금성 자산 (cash_assets)
        if fd.cash_assets >= 1000:
            ca_score = 15.0
        elif fd.cash_assets >= 500:
            ca_score = 11.0
        elif fd.cash_assets >= 100:
            ca_score = 6.0
        else:
            ca_score = 2.0
            risk_factors.append(f"현금성 자산 부족 ({fd.cash_assets:.0f}억원)")

        # Cash Runway (개월)
        if fd.cash_runway_months >= 24:
            runway_score = 15.0
        elif fd.cash_runway_months >= 12:
            runway_score = 10.0
        elif fd.cash_runway_months >= 6:
            runway_score = 5.0
        else:
            runway_score = 1.0
            risk_factors.append(f"Cash Runway 위험 ({fd.cash_runway_months:.0f}개월)")

        financial_score = cr_score + dr_score + ocf_score + ca_score + runway_score

        state.financial_result = FinancialResult(
            financial_score=round(financial_score, 2),
            risk_factors=risk_factors,
        )
        logger.info(
            "[FinancialAgent] %s | score=%.1f | risks=%s",
            company_name, financial_score, risk_factors,
        )
        return state
