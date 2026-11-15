# 의원 접수 음성 에이전트

전화·웹으로 들어온 환자 문의를 받아 **예약을 잡아주는 AI 접수 담당**입니다.
의원(1차 의료기관) 프런트 데스크의 전화 응대를 대체하는 것이 목표입니다.

> 🇬🇧 [English README](README.en.md) — 코드 주석·docstring·커밋 메시지는 한국어입니다.

> **현재 상태: M1 완료.** 예약 코어와 초진/재진 판정이 구현됐습니다.
> DB 없이 도는 테스트 44개가 전부 초록불이고, 동시성 테스트 3개는 실제
> Postgres 를 기다리며 건너뜁니다.
> → 다음은 M2(레포지토리 구현 + 텍스트 채널) [docs/roadmap.md](docs/roadmap.md)

```
$ make test
44 passed, 3 skipped
```

M1 의 방식은 **테스트를 먼저 최종 형태로 쓰고 나중에 켜는** 것이었습니다.
무엇을 만들지가 `tests/` 에 적혀 있었고, 구현은 그 23개를 켜는 작업이었습니다.
남은 빨간불은 없고, 건너뛴 3개는 실제 DB 가 없으면 "통과"라고 말할 수 없는
것들입니다(유니크 제약, 동시 예약).

---

## 범위

**합니다**

- 예약 생성 · 변경 · 취소
- 진료과 · 의사 · 진료시간 안내
- 초진 / 재진 분기
- 예약 가능 시간 탐색 (휴진일 · 영업시간 · 중복 예약 처리)
- 처리 불가 시 상담원 연결

**안 합니다 — 명시적으로 거절합니다**

- 증상 상담 · 진단 · 치료 방침
- 복약 안내
- 보험 청구 · 비용 상담
- 검사 결과 전달

접수 업무에만 선을 긋습니다. 의료 판단으로 번지면 규제 영역이고, 제품으로서도 범위가 터집니다.
에이전트는 범위 밖 질문을 받으면 **상담원 연결로 넘깁니다.**
거절 목록은 `app/agent/tools.py` 의 `escalate_to_human` 설명문에 그대로 들어가 있고,
`tests/test_tools.py` 가 그 문장이 흐려지지 않는지 지킵니다.

## 데이터 원칙

- **실제 환자 데이터를 넣지 않습니다.** 전부 합성 데이터입니다 → [seeds/synthetic.py](seeds/synthetic.py)
- 실제 의료기관에 연결하지 않습니다. 데모·포트폴리오 목적입니다.
- 통화 녹음은 보관하지 않습니다. 텍스트 전사만 남깁니다.
  (전사의 경계는 아직 미결입니다 → [docs/open-questions.md](docs/open-questions.md) 6번)

---

## 지금 있는 것 / 없는 것

| | 상태 |
|---|---|
| `app/config.py` 설정 | 돌아갑니다 (의존성 없음, 테스트 4개 통과) |
| `app/main.py` `GET /health` | 돌아갑니다 |
| `app/domain/models.py` 도메인 타입 | 완성. DDL 과 1:1 |
| `app/domain/ports.py` 레포지토리 인터페이스 | 완성 (프로토콜만) |
| `app/agent/tools.py` 툴 명세 4종 | 완성 (핸들러 없음, 테스트 6개 통과) |
| `app/vendors/base.py` STT/TTS/LLM 어댑터 | 인터페이스만 |
| `schema/001_init.sql` | 완성. `make db` 로 바로 적용됩니다 |
| `app/domain/slots.py` 슬롯 실체화 | 완성. 테스트 12개 통과 |
| **`app/domain/scheduling.py` 예약 코어** | **완성. 테스트 17개 통과** |
| **`app/domain/patients.py` 초진/재진 판정** | **완성. 테스트 6개 통과** |
| `tests/fakes.py` 인메모리 레포지토리 | 완성. ports.py 의 메모리 구현 |
| 레포지토리 실구현 (`app/infra`) | **없음 — M2.** 지금은 메모리 더블만 있습니다 |
| 음성 파이프라인 (LiveKit, STT/TTS 구현) | 없음 — M3 |
| 관리자 화면 | 없음 — M6 |

### M1 에서 결정된 것 두 가지

**검사 순서가 계약의 일부입니다.** `book()` 과 `reschedule()` 은 멱등키를
조회하기 **전에** 슬롯을 검증합니다. 멱등은 "같은 요청을 두 번 처리하지
않는다"는 뜻이고 "틀린 요청을 통과시킨다"는 뜻이 아니라서, 재시도여도 없는
슬롯이나 지난 슬롯은 그대로 거절됩니다.

**`reschedule()` 은 claim 먼저, release 나중입니다.** 새 슬롯 점유가
`SlotTaken` 으로 죽으면 release 에 도달하지 못하고, 그래서 환자의 원래 예약이
남습니다. 반대로 쓰면 실패한 변경이 예약을 지웁니다.
`test_a_failed_reschedule_keeps_the_original_appointment` 가 이걸 못 박습니다.

## 돌려보기

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
make test          # 44 passed, 3 skipped
make db            # 개발용 Postgres + schema/001_init.sql 자동 적용
make run           # uvicorn, GET /health
```

동시성 테스트는 실제 Postgres 가 있어야 의미가 있어서, DB 없이는 건너뜁니다.

```bash
make db
TEST_DATABASE_URL=postgresql://clinic:clinic@localhost:5433/clinic make test
```

## 구조

```
app/
  config.py            환경 설정 (표준 라이브러리만)
  main.py              FastAPI 진입점
  domain/
    models.py          타입. schema/001_init.sql 과 1:1
    errors.py          설명 가능한 거절들
    ports.py           도메인이 바깥에 요구하는 인터페이스
    slots.py           근무표 → 슬롯 실체화 (순수 함수)
    scheduling.py      예약 코어 — 확정은 여기서만
    patients.py        환자 식별, 초진/재진
  agent/tools.py       모델에게 주는 툴 4종
  vendors/base.py      STT / TTS / LLM 어댑터 프로토콜
seeds/synthetic.py     합성 시드 데이터
schema/001_init.sql    초기 DDL
tests/
  fakes.py             인메모리 레포지토리 (ports.py 의 메모리 구현)
  conftest.py          시나리오 시드 하나, 테스트마다 새로 세움
  …                    47개 (44 통과 / 3 건너뜀)
```

## 문서

| 문서 | 내용 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 스택 결정과 근거, 구성도, 지연 예산 |
| [docs/schema.md](docs/schema.md) | 도메인 모델과 테이블 |
| [docs/open-questions.md](docs/open-questions.md) | 아직 답을 못 정한 것들 |
| [docs/roadmap.md](docs/roadmap.md) | 남은 작업 (M1~M7) |
