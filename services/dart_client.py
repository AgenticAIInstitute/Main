from __future__ import annotations
import os
import io
import json
import zipfile
import logging
import xml.etree.ElementTree as ET
from typing import Optional, Any
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 환경변수 활성화
load_dotenv()

class DartClient:
    def __init__(self) -> None:
        self.api_key: str = os.getenv("DART_API_KEY", "").strip()
        self.cache_dir: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.cache_path: str = os.path.join(self.cache_dir, "ticker_to_corp.json")
        
        # 1. 탑 코스닥 50 바이오 기업 및 주요 상장사 하드코딩 매핑 사전 (초고속 폴백 전용)
        self._fallback_map: dict[str, str] = {
            "068270": "00251975",  # 셀트리온
            "068760": "00412859",  # 셀트리온제약
            "128940": "00816723",  # 한미약품
            "095700": "00523417",  # 제넥신
            "028300": "00147611",  # HLB
            "196170": "00868841",  # 알테오젠
            "145020": "00808292",  # 휴젤
            "000250": "00108995",  # 삼천당제약
            "237690": "00792193",  # 에스티팜
            "096530": "00547055",  # 씨젠
            "141080": "00813957",  # 리가켐바이오
            "086520": "00511874",  # 펩트론
            "206650": "01037327",  # 메디포스트
            "298040": "01306357",  # 에이비엘바이오
        }
        self.ticker_to_corp: dict[str, str] = {}
        self._load_mappings()

    def is_available(self) -> bool:
        """API 키가 정상 등록되어 있는지 확인"""
        return bool(self.api_key) and self.api_key != "your_api_key_here"

    def _load_mappings(self) -> None:
        """JSON 캐시 또는 하드코딩 사전에서 매핑 로드"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.ticker_to_corp = json.load(f)
                logger.info("[DartClient] 로컬 캐시에서 DART 고유번호 매핑 로드 완료 (%d개)", len(self.ticker_to_corp))
                return
            except Exception as e:
                logger.warning("[DartClient] 캐시 로드 실패, 하드코딩 맵 적용: %s", e)
        
        # 캐시가 없으면 하드코딩 사전 적용
        self.ticker_to_corp = self._fallback_map.copy()

    def download_and_cache_corp_codes(self) -> bool:
        """Open DART API를 통해 전 상장사 고유번호 ZIP을 내려받아 로컬 JSON으로 캐싱"""
        if not self.is_available():
            logger.warning("[DartClient] DART API 키가 설정되지 않아 캐시를 생성할 수 없습니다.")
            return False

        url = "https://opendart.fss.or.kr/api/corpCode.xml"
        params = {"crtfc_key": self.api_key}

        try:
            logger.info("[DartClient] Open DART에서 전 상장사 고유번호 다운로드 중...")
            response = requests.get(url, params=params, timeout=15)
            if response.status_code != 200:
                logger.error("[DartClient] 고유번호 XML 다운로드 실패: HTTP %d", response.status_code)
                return False

            # ZIP 압축 풀기
            zip_file = zipfile.ZipFile(io.BytesIO(response.content))
            xml_filename = zip_file.namelist()[0]
            xml_data = zip_file.read(xml_filename)

            # XML 파싱
            root = ET.fromstring(xml_data)
            new_map = self._fallback_map.copy()

            for corp in root.findall("list"):
                stock_code_elem = corp.find("stock_code")
                corp_code_elem = corp.find("corp_code")
                
                if stock_code_elem is not None and corp_code_elem is not None:
                    stock_code = stock_code_elem.text.strip() if stock_code_elem.text else ""
                    corp_code = corp_code_elem.text.strip() if corp_code_elem.text else ""
                    
                    # 상장사(종목코드가 6자리인 기업)만 추출 및 매핑
                    if stock_code and len(stock_code) == 6:
                        new_map[stock_code] = corp_code

            # 캐시 파일 쓰기
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(new_map, f, ensure_ascii=False, indent=2)

            self.ticker_to_corp = new_map
            logger.info("[DartClient] 전 상장사 고유번호 매핑 완료 및 캐싱 완료 (%d개)", len(new_map))
            return True
        except Exception as e:
            logger.error("[DartClient] 고유번호 XML 다운로드 및 파싱 오류: %s", e)
            return False

    def get_corp_code(self, ticker: str) -> Optional[str]:
        """종목코드를 통해 8자리 DART corp_code 조회"""
        code = self.ticker_to_corp.get(ticker)
        if not code and self.is_available():
            # 캐시에 없는 신규 기업일 경우 캐시 재생성 시도
            if self.download_and_cache_corp_codes():
                code = self.ticker_to_corp.get(ticker)
        return code

    def fetch_disclosures(self, ticker: str, count: int = 20) -> list[dict[str, Any]]:
        """DART 실시간 공시 목록 수집"""
        if not self.is_available():
            return []

        corp_code = self.get_corp_code(ticker)
        if not corp_code:
            logger.warning("[DartClient] 종목코드 %s에 매핑되는 DART corp_code를 찾을 수 없습니다.", ticker)
            return []

        url = "https://opendart.fss.or.kr/api/list.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "page_count": str(count),
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "000":
                    return data.get("list", [])
                else:
                    logger.warning("[DartClient] 공시조회 응답 결과: %s - %s", data.get("status"), data.get("message"))
            else:
                logger.warning("[DartClient] 공시조회 HTTP 에러: %d", response.status_code)
        except Exception as e:
            logger.error("[DartClient] 공시조회 실패: %s", e)
        
        return []

    def fetch_financials(self, ticker: str, year: str = "2024", reprt_code: str = "11011") -> dict[str, float]:
        """
        DART 단일회사 주요계정 재무제표 수집 및 파싱.
        11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서.
        """
        result: dict[str, float] = {}
        if not self.is_available():
            return result

        corp_code = self.get_corp_code(ticker)
        if not corp_code:
            return result

        url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": year,
            "reprt_code": reprt_code,
        }

        try:
            logger.info("[DartClient] Open DART 재무제표 조회 중: %s (%s년)", ticker, year)
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "000":
                    accounts_list = data.get("list", [])
                    result = self._parse_financial_accounts(accounts_list)
                else:
                    logger.warning("[DartClient] 재무제표 응답 결과: %s - %s", data.get("status"), data.get("message"))
            else:
                logger.warning("[DartClient] 재무제표 HTTP 에러: %d", response.status_code)
        except Exception as e:
            logger.error("[DartClient] 재무제표 조회 실패: %s", e)

        return result

    def _parse_financial_accounts(self, accounts: list[dict[str, Any]]) -> dict[str, float]:
        """원시 DART 재무 목록에서 핵심 계정 값을 추려내어 만원단위(또는 원단위)에서 억원단위로 변환"""
        parsed: dict[str, float] = {}
        
        # 키워드 매핑 테이블 구축
        mapping_rules = {
            "current_assets": ["유동자산", "current assets"],
            "current_liabilities": ["유동부채", "current liabilities"],
            "total_liabilities": ["부채총계", "total liabilities"],
            "total_equity": ["자본총계", "total equity", "자본 총계"],
            "revenue": ["매출액", "매출", "revenue", "sales"],
            "operating_income": ["영업이익", "영업손실", "operating income", "operating profit"],
            "net_income": ["당기순이익", "당기순손실", "net income"],
        }

        for acnt in accounts:
            acnt_nm = acnt.get("account_nm", "").replace(" ", "").lower()
            amount_str = acnt.get("thstrm_amount", "0").replace(",", "").strip()
            
            try:
                amount_val = float(amount_str) if amount_str else 0.0
            except ValueError:
                amount_val = 0.0

            # 매핑 대조
            for key, keywords in mapping_rules.items():
                if any(kw in acnt_nm for kw in keywords):
                    # 보통 DART 단일회사 재무제표는 원 단위로 들어옴. 이를 '억원' 단위로 환산 (100,000,000으로 나누기)
                    # 단, 혹시라도 10억 이하의 대규모 벤처가 억단위로 기입한 경우에는 값의 크기를 확인하여 조정
                    amount_in_hundred_million = amount_val / 100000000.0
                    if amount_in_hundred_million > 1000000.0:  # 너무 크다면 원단위로 판단
                        amount_in_hundred_million = amount_val / 100000000.0
                    parsed[key] = round(amount_in_hundred_million, 2)
                    break

        return parsed

# 싱글톤 인스턴스 제공
_dart_client: Optional[DartClient] = None

def get_dart_client() -> DartClient:
    global _dart_client
    if _dart_client is None:
        _dart_client = DartClient()
    return _dart_client
