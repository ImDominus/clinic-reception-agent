"""도메인 예외.

에이전트는 이 예외들을 그대로 환자에게 읽어주지 않습니다. 툴 레이어에서
사람이 들을 문장으로 바꿉니다. 코어는 사유를 정확히 구분해서 올리는 일만 합니다.
"""

from __future__ import annotations


class DomainError(Exception):
    """사용자에게 설명 가능한 거절. 버그가 아닙니다."""


class SlotNotFound(DomainError): ...


class SlotTaken(DomainError):
    """이미 살아있는 예약이 붙어 있는 슬롯. DB 유니크 제약이 최종 판정자입니다."""


class SlotInPast(DomainError): ...


class OutsideSchedule(DomainError):
    """근무표 밖의 시각."""


class ProviderClosed(DomainError):
    """휴진."""


class AppointmentNotFound(DomainError): ...


class AlreadyCancelled(DomainError): ...


class PatientNotIdentified(DomainError):
    """전화번호와 생년월일이 모두 있어야 사람을 특정합니다."""


class OutOfScope(DomainError):
    """접수·예약 범위 밖. 즉시 상담원 연결 대상입니다."""
