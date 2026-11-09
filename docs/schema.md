# 도메인 모델

Postgres 단일 저장소. 전부 합성 데이터입니다.

## 테이블

| 테이블 | 역할 |
|---|---|
| `clinics` | 의원. 테넌트 단위 |
| `departments` | 진료과 (내과·정형외과·…) |
| `providers` | 의사 |
| `provider_schedules` | 의사별 요일·시간대 근무표 |
| `closures` | 휴진일 (의원 전체 또는 의사별) |
| `slots` | 실체화된 예약 단위. 근무표 + 휴진 반영해 생성 |
| `patients` | 합성 환자. 전화번호 + 생년월일로 식별 |
| `appointments` | 예약. 초진/재진, 상태 |
| `calls` | 통화 1건 |
| `call_events` | 통화 내 턴 단위 기록 (전사·툴 호출·구간별 지연) |

## 왜 슬롯을 실체화하는가

근무표에서 매번 계산해도 됩니다. 그런데 실체화하면,

- 동시 예약 충돌을 **DB 유니크 제약**으로 막을 수 있습니다. 애플리케이션 락이 필요 없습니다.
- 예약 가능 시간 조회가 단순 조회가 됩니다. 통화 중 지연에 직접 영향을 줍니다.
- 임시 휴진·특별 진료 같은 예외를 슬롯 단위로 덮어쓸 수 있습니다.

대가는 생성 잡이 필요하다는 점입니다. 근무표가 바뀌면 재생성합니다.

## 핵심 제약

- `slots`: `(provider_id, starts_at)` 유니크 — 같은 의사·같은 시각 중복 불가
- `appointments`: `slot_id` 유니크 부분 인덱스 (`status <> 'cancelled'`) — 취소된 건 재예약 허용
- `appointments.idempotency_key` 유니크 — 통화 재시도 시 중복 예약 방지
- `patients`: `(clinic_id, phone, birth_date)` 유니크 — 식별 기준

## 상태 전이

```
appointments.status:  booked ──> completed
                        │
                        ├──> cancelled
                        └──> no_show
```

취소는 슬롯을 다시 열고, 그 외 전이는 슬롯을 점유한 채로 둡니다.

## 초진 / 재진 판정

`lookup_patient(phone, birth_date)` 결과로 갈립니다.

- 레코드 없음 → **초진**. 이름·생년월일·연락처를 받아 `patients`에 생성
- 레코드 있고 과거 `completed` 예약 있음 → **재진**
- 레코드는 있으나 완료 이력 없음 → **초진으로 취급** (예약만 하고 안 온 경우)
