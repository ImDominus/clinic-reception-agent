# Clinic Reception Voice Agent

An AI receptionist that answers patient calls and web enquiries and **books
appointments** for a clinic. The goal is to replace front-desk phone handling at
a Korean primary-care clinic (의원).

> 🇰🇷 [한국어 README](README.md) is the primary document. This file is a
> translation for readers who don't read Korean; code comments, docstrings and
> commit messages are in Korean.

> **Status: M1 complete.** The booking core and the first-visit/return-visit
> decision are implemented. All 44 non-DB tests pass; 3 concurrency tests are
> skipped until a real Postgres is available.
>
> ```
> $ make test
> 44 passed, 3 skipped
> ```
>
> → [docs/roadmap.md](docs/roadmap.md) for what M2–M7 hold.

---

## Built for Korea only

This is deliberate, not an oversight. The domain model encodes assumptions that
do not travel:

- **Timezone is fixed to `Asia/Seoul`.** Korea has had no daylight saving since
  1988, so KST is always `+09:00`. Tests exploit this — they use a fixed
  `+09:00` offset so they run on Windows without `tzdata`.
- **Patient identity is phone number + date of birth.** Korean clinics identify
  patients this way, and families routinely share one phone number, so the
  number alone never identifies a person. There is no national-ID handling and
  there will not be.
- **Clinic workflow is 의원-shaped**: departments, a provider per department,
  fixed-length slots from a weekly schedule, lunch breaks expressed as two
  schedule rows on the same weekday rather than a dedicated column.
- **The conversation is in Korean.** Prompts, tool descriptions and refusal
  wording are all Korean.

Nothing here is written to be internationalised. If this ever needed another
country it would be a different domain model, not a configuration flag.

---

## Scope

**It does**

- Create, change and cancel appointments
- Answer questions about departments, providers and opening hours
- Decide first visit vs. return visit
- Search for bookable times (closures, opening hours, double-booking)
- Hand off to a human when it cannot help

**It refuses — explicitly**

- Symptom advice, diagnosis, treatment decisions
- Medication guidance
- Insurance claims, cost enquiries
- Delivering test results

The line is drawn at reception work. Drifting into medical judgement is a
regulated activity and blows up the product scope as well. Out-of-scope
questions are **escalated to a human.** The refusal list lives verbatim in the
`escalate_to_human` description in `app/agent/tools.py`, and
`tests/test_tools.py` guards that wording against erosion.

## Data principles

- **No real patient data.** Everything is synthetic →
  [seeds/synthetic.py](seeds/synthetic.py)
- Not connected to any real clinic. This is a demo and portfolio project.
- Call audio is not retained. Only text transcripts.
  (Transcript boundaries are still open → [docs/open-questions.md](docs/open-questions.md), item 6)

---

## What exists / what doesn't

| | Status |
|---|---|
| `app/config.py` settings | Works (no dependencies, 4 tests) |
| `app/main.py` `GET /health` | Works |
| `app/domain/models.py` domain types | Done. 1:1 with the DDL |
| `app/domain/ports.py` repository interfaces | Done (protocols only) |
| `app/domain/slots.py` slot materialisation | Done. 12 tests |
| `app/domain/scheduling.py` booking core | **Done. 17 tests** |
| `app/domain/patients.py` first/return visit | **Done. 6 tests** |
| `app/agent/tools.py` 4 tool specs | Done (no handlers, 6 tests) |
| `app/vendors/base.py` STT/TTS/LLM adapters | Interfaces only |
| `schema/001_init.sql` | Done. Applied by `make db` |
| Repository implementations (`app/infra`) | **Missing — M2.** Only in-memory fakes exist |
| Voice pipeline (LiveKit, STT/TTS) | Missing — M3 |
| Admin UI | Missing — M6 |

### The two things to know about M1

**Check order is part of the contract.** In `book()` and `reschedule()`, slot
validation comes *before* the idempotency-key lookup. Idempotency means "do not
process the same request twice", not "let a bad request through" — a retry must
still be rejected if the slot is gone or in the past.

**`reschedule()` claims before it releases.** If claiming the new slot raises
`SlotTaken`, execution never reaches the release, so the patient keeps their
original appointment. Written the other way round, a failed change would delete
a booking. `test_a_failed_reschedule_keeps_the_original_appointment` is the test
that pins this down.

## Running it

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
make test          # 44 passed, 3 skipped
make db            # dev Postgres + schema/001_init.sql applied automatically
make run           # uvicorn, GET /health
```

The concurrency tests only mean something against a real Postgres, so they are
skipped rather than faked:

```bash
make db
TEST_DATABASE_URL=postgresql://clinic:clinic@localhost:5433/clinic make test
```

## Layout

```
app/
  config.py            settings (standard library only)
  main.py              FastAPI entrypoint
  domain/
    models.py          types, 1:1 with schema/001_init.sql
    errors.py          explainable refusals
    ports.py           what the domain asks of the outside world
    slots.py           weekly schedule → slots (pure functions)
    scheduling.py      booking core — confirmation happens only here
    patients.py        patient identity, first vs. return visit
  agent/tools.py       the 4 tools handed to the model
  vendors/base.py      STT / TTS / LLM adapter protocols
seeds/synthetic.py     synthetic seed data
schema/001_init.sql    initial DDL
tests/
  fakes.py             in-memory repositories (ports.py implemented in memory)
  conftest.py          one seeded scenario, rebuilt per test
  …                    47 tests
```

## Design note: why the domain owns the decision

The model proposes; it never decides. `find_slots` offers at most
`MAX_SUGGESTIONS` (3) candidates — you cannot read ten options to someone on the
phone — and every booking goes through `scheduling.book()`, which re-validates
the slot. **If the model invents a time or a slot id, the booking does not
happen.** That is the one structural guarantee this codebase is built around.

Because the domain functions only accept the protocols in `ports.py`, the
booking rules are tested without a database at all. The one thing that cannot be
faked is concurrency: two calls racing for the same slot are settled by the
`appointments_active_slot` unique index, not by an application lock, so that
test waits for a real Postgres instead of pretending to pass.

## Documents

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Stack decisions and rationale, diagram, latency budget |
| [docs/schema.md](docs/schema.md) | Domain model and tables |
| [docs/open-questions.md](docs/open-questions.md) | Questions still unanswered |
| [docs/roadmap.md](docs/roadmap.md) | Remaining work (M1–M7) |

## License

MIT — see [LICENSE](LICENSE).
