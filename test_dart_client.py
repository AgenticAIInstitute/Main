import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.dart_client import get_dart_client
from models.schemas import FinancialData

def run_test():
    dart = get_dart_client()
    print(f"Loaded {len(dart.ticker_to_corp)} mapping entries.")
    
    mock_fallback = FinancialData(
        current_ratio=2.0,
        debt_ratio=50.0,
        operating_cash_flow=100.0,
        cash_assets=500.0,
        cash_runway_months=24.0,
        operating_profit_margin=10.0,
        rd_expense_ratio=20.0
    )
    
    res = dart.get_financial_data("999999", fallback_data=mock_fallback)
    print(f"Result fallback test: {res}")

if __name__ == "__main__":
    run_test()
