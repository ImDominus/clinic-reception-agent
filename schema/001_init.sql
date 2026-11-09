-- 의원 접수 음성 에이전트 — 초기 스키마
-- Postgres 16+

create extension if not exists "uuid-ossp";

create table clinics (
    id              uuid primary key default uuid_generate_v4(),
    name            text        not null,
    timezone        text        not null default 'Asia/Seoul',
    phone           text,
    created_at      timestamptz not null default now()
);

create table departments (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    name            text        not null,
    unique (clinic_id, name)
);

create table providers (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    department_id   uuid        not null references departments(id) on delete restrict,
    name            text        not null,
    slot_minutes    int         not null default 15,
    active          boolean     not null default true
);

-- 요일별 근무 시간대. weekday: 0=월 … 6=일
create table provider_schedules (
    id              uuid primary key default uuid_generate_v4(),
    provider_id     uuid        not null references providers(id) on delete cascade,
    weekday         smallint    not null check (weekday between 0 and 6),
    starts_at       time        not null,
    ends_at         time        not null,
    check (ends_at > starts_at)
);

-- 휴진. provider_id 가 null 이면 의원 전체 휴진
create table closures (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    provider_id     uuid        references providers(id) on delete cascade,
    starts_at       timestamptz not null,
    ends_at         timestamptz not null,
    reason          text,
    check (ends_at > starts_at)
);

-- 근무표 + 휴진을 반영해 생성되는 실체화된 예약 단위
create table slots (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    provider_id     uuid        not null references providers(id) on delete cascade,
    starts_at       timestamptz not null,
    ends_at         timestamptz not null,
    open            boolean     not null default true,
    unique (provider_id, starts_at)
);

create index on slots (clinic_id, starts_at) where open;

create table patients (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    name            text        not null,
    phone           text        not null,
    birth_date      date        not null,
    created_at      timestamptz not null default now(),
    unique (clinic_id, phone, birth_date)
);

create type appointment_status as enum ('booked', 'completed', 'cancelled', 'no_show');
create type visit_type        as enum ('first', 'return');

create table appointments (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    slot_id         uuid        not null references slots(id) on delete restrict,
    patient_id      uuid        not null references patients(id) on delete restrict,
    visit           visit_type  not null,
    status          appointment_status not null default 'booked',
    idempotency_key text        not null,
    created_at      timestamptz not null default now(),
    unique (idempotency_key)
);

-- 같은 슬롯에 살아있는 예약은 하나만
create unique index appointments_active_slot
    on appointments (slot_id)
    where status <> 'cancelled';

create table calls (
    id              uuid primary key default uuid_generate_v4(),
    clinic_id       uuid        not null references clinics(id) on delete cascade,
    channel         text        not null,          -- 'web' | 'sip'
    caller_phone    text,
    patient_id      uuid        references patients(id) on delete set null,
    started_at      timestamptz not null default now(),
    ended_at        timestamptz,
    outcome         text                            -- 'booked' | 'escalated' | 'abandoned' | …
);

-- 턴 단위 기록. 전사와 구간별 지연을 남긴다
create table call_events (
    id              bigserial primary key,
    call_id         uuid        not null references calls(id) on delete cascade,
    turn            int         not null,
    role            text        not null,          -- 'user' | 'agent' | 'tool'
    text            text,
    tool_name       text,
    tool_result     jsonb,
    stt_ms          int,
    llm_ms          int,
    tts_first_byte_ms int,
    created_at      timestamptz not null default now()
);

create index on call_events (call_id, turn);
