import os
import json
import logging
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from models.schemas import FinancialData

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CORP_CODE_CACHE_FILE = os.path.join(CACHE_DIR, "ticker_to_corp.json")

class DartClient:
    def __init__(self):
        # 환경 변수에서 최신 API Key를 로드
        self.api_key = os.environ.get("DART_API_KEY", "").strip()
        self.ticker_to_corp = {}
        self._load_or_fetch_corp_codes()

    def _load_or_fetch_corp_codes(self):
        if os.path.exists(CORP_CODE_CACHE_FILE):
            try:
                with open(CORP_CODE_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.ticker_to_corp = json.load(f)
                logger.info("[DartClient] 캐시에서 고유번호 매핑 정보를 로드했습니다.")
                return
            except Exception as e:
                logger.warning(f"[DartClient] 캐시 읽기 실패. 다시 다운로드합니다: {e}")

        if not self.api_key:
            logger.warning("[DartClient] DART_API_KEY가 설정되지 않아 고유번호 목록을 받을 수 없습니다.")
            return

        logger.info("[DartClient] DART 고유번호 ZIP 파일을 다운로드하여 파싱합니다...")
        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={self.api_key}"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                xml_data = zf.read("CORPCODE.xml")
            
            tree = ET.fromstring(xml_data)
            mapping = {}
            for list_elem in tree.findall("list"):
                corp_code = list_elem.findtext("corp_code")
                stock_code = list_elem.findtext("stock_code")
                if stock_code and stock_code.strip():
                    mapping[stock_code.strip()] = corp_code.strip()
            
            self.ticker_to_corp = mapping
            
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(CORP_CODE_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)
            logger.info(f"[DartClient] {len(mapping)}개의 고유번호를 성공적으로 캐싱했습니다.")
        except Exception as e:
            logger.error(f"[DartClient] 고유번호 매핑 다운로드 실패: {e}")

    def get_financial_data(self, ticker: str, fallback_data: Optional[FinancialData] = None) -> Optional[FinancialData]:
        if not self.api_key:
            logger.warning("[DartClient] DART_API_KEY가 없습니다. 원본 Mock 데이터를 반환합니다.")
            return fallback_data
            
        corp_code = self.ticker_to_corp.get(ticker)
        if not corp_code:
            logger.warning(f"[DartClient] 종목코드 {ticker}에 해당하는 DART 고유번호를 찾을 수 없습니다.")
            return fallback_data

        logger.info(f"[DartClient] DART에서 {ticker}({corp_code}) 재무 데이터를 조회합니다.")
        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": "2023", # MVP 기준 2023년 고정
            "reprt_code": "11014" # 사업보고서
        }
        
        try:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("status") != "000":
                logger.warning(f"[DartClient] DART API 응답 에러: {data.get('message')}")
                return fallback_data
                
            accounts = data.get("list", [])
            
            parsed = {
                "유동자산": 0.0,
                "유동부채": 0.0,
                "부채총계": 0.0,
                "자본총계": 0.0,
                "매출액": 0.0,
                "영업이익": 0.0,
            }
            
            for item in accounts:
                acnt_nm = item.get("account_nm", "")
                amt_str = str(item.get("thstrm_amount", "0")).replace(",", "")
                # 음수 등 숫자 파싱 검증
                if not amt_str.isdigit() and not (amt_str.startswith('-') and amt_str[1:].isdigit()):
                    continue
                amt = float(amt_str)
                
                # 금액이 원 단위이므로 억 단위로 변환
                amt_in_hundred_million = amt / 100_000_000
                
                # '유동자산' 등 텍스트를 포함하면 매핑 (동일명 중복 방지를 위해 단순화)
                for k in parsed.keys():
                    if k in acnt_nm and parsed[k] == 0.0:
                        parsed[k] = amt_in_hundred_million
                        break

            # 지표 계산 로직 (에지케이스 방어)
            current_ratio = (parsed["유동자산"] / parsed["유동부채"]) if parsed["유동부채"] > 0 else 1.0
            debt_ratio = (parsed["부채총계"] / parsed["자본총계"] * 100) if parsed["자본총계"] > 0 else 0.0
            operating_profit_margin = (parsed["영업이익"] / parsed["매출액"] * 100) if parsed["매출액"] > 0 else 0.0
            
            # 현금성 자산, 영업현금흐름, R&D 비중 등은 주요계정 API에 명확히 없으므로 Fallback(Mock 데이터) 승계
            ocf = fallback_data.operating_cash_flow if fallback_data else 0.0
            cash = fallback_data.cash_assets if fallback_data else (parsed["유동자산"] * 0.5)
            rd = fallback_data.rd_expense_ratio if fallback_data else 0.0
            runway = fallback_data.cash_runway_months if fallback_data else 0.0
            
            logger.info(f"[DartClient] {ticker} 데이터 산출 완료. 유동비율: {current_ratio:.2f}, 부채비율: {debt_ratio:.2f}%, 영업이익률: {operating_profit_margin:.2f}%")
            
            return FinancialData(
                current_ratio=round(current_ratio, 2),
                debt_ratio=round(debt_ratio, 2),
                operating_cash_flow=ocf,
                cash_assets=cash,
                cash_runway_months=runway,
                operating_profit_margin=round(operating_profit_margin, 2),
                rd_expense_ratio=rd
            )
            
        except Exception as e:
            logger.error(f"[DartClient] DART 재무 데이터 조회 실패: {e}")
            return fallback_data

_instance = None
def get_dart_client():
    global _instance
    if _instance is None:
        _instance = DartClient()
    return _instance
