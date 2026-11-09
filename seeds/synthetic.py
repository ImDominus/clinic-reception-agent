"""합성 시드 데이터.

실제 환자 데이터를 넣지 않습니다. 실제 의료기관에도 연결하지 않습니다.
여기 있는 의원·의사·환자는 전부 가상입니다.

데이터 모양은 지금 정해두고, 넣는 일은 M1 에서 합니다.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any

CLINIC: dict[str, Any] = {
    "name": "새밭내과의원",  # 가상
    "timezone": "Asia/Seoul",
    "phone": "0269000000",  # 가상
}

DEPARTMENTS: list[str] = ["내과", "소아과"]

# 점심시간은 구간을 둘로 끊어서 표현합니다. weekday 0=월 … 6=일
PROVIDERS: list[dict[str, Any]] = [
    {
        "name": "김해원",
        "department": "내과",
        "slot_minutes": 15,
        "schedule": [
            (wd, time(9, 0), time(13, 0)) for wd in range(0, 5)
        ] + [
            (wd, time(14, 0), time(18, 0)) for wd in range(0, 5)
        ] + [(5, time(9, 0), time(13, 0))],  # 토요일 오전만
    },
    {
        "name": "윤소라",
        "department": "내과",
        "slot_minutes": 20,  # 슬롯 길이가 의사마다 다른 경우
        "schedule": [(wd, time(10, 0), time(17, 0)) for wd in (0, 2, 4)],
    },
    {
        "name": "장미르",
        "department": "소아과",
        "slot_minutes": 10,  # 짧은 슬롯 — 경계 계산이 제일 잘 깨지는 쪽
        "schedule": [
            (wd, time(9, 30), time(12, 50)) for wd in range(0, 5)
        ],  # 10분 간격이면 꼬리가 딱 안 맞는다
    },
]

CLOSURES: list[dict[str, Any]] = [
    # 의원 전체 휴진 (provider 가 None)
    {"provider": None, "date": date(2026, 12, 25), "reason": "휴진"},
    # 의사 한 명만 휴진 — 같은 날 다른 의사는 예약이 되어야 한다
    {"provider": "김해원", "date": date(2026, 12, 24), "reason": "학회"},
]

PATIENTS: list[dict[str, Any]] = [
    # 같은 번호를 쓰는 가족. 생년월일로 구분됩니다.
    {"name": "박연수", "phone": "01000000001", "birth_date": date(1984, 3, 12)},
    {"name": "박하람", "phone": "01000000001", "birth_date": date(2019, 7, 2)},
    # 기록은 있지만 온 적 없는 환자 (전부 취소) — 초진으로 판정되어야 한다
    {"name": "최도윤", "phone": "01000000002", "birth_date": date(1991, 11, 30)},
]


async def load(dsn: str) -> None:
    """위 데이터를 빈 DB 에 넣습니다. 멱등해야 합니다 — 두 번 돌려도 같은 상태."""
    raise NotImplementedError("M1")
