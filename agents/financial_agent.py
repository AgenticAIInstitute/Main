from __future__ import annotations

import logging

from models.schemas import BioAgentState, FinancialResult

logger = logging.getLogger(__name__)


class FinancialAgent:
    """
    유동비율, 부채비율, 영업이익률, 영업현금흐름, 현금성자산, R&D 비용 비중, Cash Runway 기반
    바이오 기업 특화 재무 점수(0~100)를 산출한다.
    """

    def run(self, state: BioAgentState) -> BioAgentState:
        fd = state.company_data.financial
        company_name = state.company_data.company_name
        clinical_stage = state.company_data.bio_domain.clinical_stage
        risk_factors: list[str] = []

        if fd.current_ratio >= 2.0:
            cr_score = 20.0
        elif fd.current_ratio >= 1.5:
            cr_score = 16.0
        elif fd.current_ratio >= 1.0:
            cr_score = 10.0
        else:
            cr_score = 3.0
            risk_factors.append(f"유동비율 위험 ({fd.current_ratio:.1f} < 1.0)")

        if fd.debt_ratio <= 40:
            dr_score = 20.0
        elif fd.debt_ratio <= 70:
            dr_score = 15.0
        elif fd.debt_ratio <= 100:
            dr_score = 8.0
        else:
            dr_score = 2.0
            risk_factors.append(f"부채비율 과다 ({fd.debt_ratio:.0f}%)")

        if fd.operating_profit_margin >= 10.0:
            opm_score = 15.0
        elif fd.operating_profit_margin >= 0.0:
            opm_score = 10.0
        elif fd.operating_profit_margin >= -20.0:
            opm_score = 5.0
        else:
            opm_score = 2.0
            if fd.rd_expense_ratio < 20.0:
                risk_factors.append(f"영업적자 심화 (영업이익률 {fd.operating_profit_margin:.1f}%)")

        if fd.operating_cash_flow >= 500:
            ocf_score = 15.0
        elif fd.operating_cash_flow >= 200:
            ocf_score = 11.0
        elif fd.operating_cash_flow >= 0:
            ocf_score = 6.0
        else:
            ocf_score = 2.0
            risk_factors.append(f"영업현금흐름 음수 ({fd.operating_cash_flow:.0f}억원)")

        if fd.cash_assets >= 1000:
            ca_score = 15.0
        elif fd.cash_assets >= 500:
            ca_score = 11.0
        elif fd.cash_assets >= 100:
            ca_score = 6.0
        else:
            ca_score = 2.0
            risk_factors.append(f"현금성 자산 부족 ({fd.cash_assets:.0f}억원)")

        if fd.rd_expense_ratio >= 20.0:
            rd_score = 10.0
        elif fd.rd_expense_ratio >= 10.0:
            rd_score = 7.0
        elif fd.rd_expense_ratio >= 5.0:
            rd_score = 4.0
        else:
            rd_score = 1.0
            risk_factors.append(f"R&D 투자 부족 (R&D 비중 {fd.rd_expense_ratio:.1f}%)")

        if fd.cash_runway_months >= 24:
            runway_score = 5.0
        elif fd.cash_runway_months >= 12:
            runway_score = 3.0
        elif fd.cash_runway_months >= 6:
            runway_score = 1.0
        else:
            runway_score = 0.0
            risk_factors.append(f"Cash Runway 위험 ({fd.cash_runway_months:.0f}개월)")

        base_score = cr_score + dr_score + opm_score + ocf_score + ca_score + rd_score + runway_score

        has_protection = False
        if fd.operating_profit_margin < 0 and clinical_stage in ["Phase 1", "Phase 2", "Phase 3", "Preclinical"]:
            if fd.rd_expense_ratio >= 20.0 and fd.cash_runway_months >= 12:
                has_protection = True
                base_score += 5.0
                logger.info(
                    "[FinancialAgent] %s | 기술 성장성 보정 가점 적용 (+5.0점) - R&D 비중: %.1f%%, Runway: %.1f개월",
                    company_name,
                    fd.rd_expense_ratio,
                    fd.cash_runway_months,
                )

        financial_score = max(0.0, min(100.0, base_score))

        if has_protection:
            risk_factors.append("임상 단계 연구개발 진행에 따른 계획된 적자 (R&D 투자 양호)")

        state.financial_result = FinancialResult(
            financial_score=round(financial_score, 2),
            risk_factors=risk_factors,
        )

        logger.info(
            "[FinancialAgent] %s | score=%.1f | risks=%s | protection=%s",
            company_name,
            financial_score,
            risk_factors,
            has_protection,
        )
        return state
