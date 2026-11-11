# 의원 접수 음성 에이전트

전화·웹으로 들어온 환자 문의를 받아 **예약을 잡아주는 AI 접수 담당**입니다.
의원(1차 의료기관) 프런트 데스크의 전화 응대를 대체하는 것이 목표입니다.

> **현재 상태: M1 진행 중 — 슬롯 실체화 완료.**
> 근무표에서 슬롯을 만드는 부분은 구현했고 테스트 11개가 초록불입니다.
> **예약 코어와 초진/재진 판정은 아직 비어 있습니다.**
> 테스트 47개 중 23개가 아직 빨간불이고, 그걸 켜는 것이 남은 M1 입니다.
> → [docs/roadmap.md](docs/roadmap.md)

```
$ make test
23 failed, 21 passed, 3 skipped
```

빨간불은 전부 `NotImplementedError("M1")` 입니다. 테스트 본문은 최종 형태로 써뒀습니다.
**무엇을 만들지가 테스트에 적혀 있고, 어떻게 만들지는 비어 있는 상태**입니다.

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
| `app/domain/slots.py` 슬롯 실체화 | 완성. 테스트 11개 통과 |
| **`app/domain/scheduling.py` 예약 코어** | **비어 있음 — 테스트 17개 대기** |
| **`app/domain/patients.py` 초진/재진 판정** | **비어 있음 — 테스트 6개 대기** |
| 음성 파이프라인 (LiveKit, STT/TTS 구현) | 없음 — M3 |
| 관리자 화면 | 없음 — M6 |

## 돌려보기

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
make test          # 빨간불 23개가 정상입니다
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
tests/                 47개. 23개가 M1 대기
```

## 문서

| 문서 | 내용 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 스택 결정과 근거, 구성도, 지연 예산 |
| [docs/schema.md](docs/schema.md) | 도메인 모델과 테이블 |
| [docs/open-questions.md](docs/open-questions.md) | 아직 답을 못 정한 것들 |
| [docs/roadmap.md](docs/roadmap.md) | 남은 작업 (M1~M7) |
