from __future__ import annotations

import re

BIO_COMPANY_ALIASES: dict[str, list[str]] = {
    "알테오젠": ["Alteogen", "ALT-B4", "Hybrozyme"],
    "HLB": ["HLB", "HLB Co", "Elevar Therapeutics", "rivoceranib", "apatinib"],
    "삼천당제약": ["SCD", "SCD Pharm", "SCD411", "SCD-411"],
    "휴젤": ["Hugel", "botulinum toxin"],
    "에이비엘바이오": ["ABL Bio", "ABL001", "CTX-009", "givastomig"],
    "지아이이노베이션": ["GI Innovation", "GI-101", "GI-102"],
    "바이오니아": ["Bioneer"],
    "메지온": ["Mezzion", "udenafil"],
    "오스코텍": ["Oscotec", "SKI-O-703", "cevidoplenib"],
    "네이처셀": ["Nature Cell", "JointStem"],
    "제넥신": ["Genexine", "GX-I7", "efineptakin alfa"],
    "차바이오텍": ["CHA Biotech", "CHA Bio", "CordSTEM"],
    "에스티팜": ["ST Pharm"],
    "씨젠": ["Seegene"],
    "헬릭스미스": ["Helixmith", "VM202", "Engensis"],
    "파마리서치": ["PharmaResearch"],
    "코오롱티슈진": ["Kolon TissueGene", "Invossa"],
    "셀트리온제약": ["Celltrion Pharm", "Celltrion"],
    "동국제약": ["DongKook Pharmaceutical", "DK Pharm"],
}


def aliases_for_company(company_name: str) -> list[str]:
    aliases: list[str] = []
    normalized = company_name.strip()
    if normalized:
        aliases.append(normalized)

    for key, values in BIO_COMPANY_ALIASES.items():
        if key in normalized or normalized in key:
            aliases.extend(values)

    aliases.extend(_generated_aliases(normalized))
    return _dedupe(aliases)


def _generated_aliases(company_name: str) -> list[str]:
    cleaned = company_name
    for token in ("주식회사", "(주)", "㈜", "제약", "바이오", "바이오텍", "헬스케어", "테라퓨틱스"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip(" -_.,")

    aliases: list[str] = []
    if cleaned and cleaned != company_name:
        aliases.append(cleaned)

    ascii_like = re.sub(r"[^A-Za-z0-9]", "", company_name)
    if ascii_like and ascii_like != company_name:
        aliases.append(ascii_like)
    return aliases


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = value.strip()
        if not term:
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(term)
    return result
