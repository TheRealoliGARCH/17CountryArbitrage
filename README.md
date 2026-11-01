# The 17-State Market

**A research implementation of a hierarchical market state machine — from OHLC price formation to market intelligence, transaction processing, institutional governance, and model revision.**

[![Unit tests](https://github.com/TheRealoliGARCH/17StateMarket/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/TheRealoliGARCH/17StateMarket/actions/workflows/unit-tests.yml)

> **Status:** Research scaffold. The automated unit-test workflow has passed on Python 3.10, 3.11, and 3.12. This is not a production trading, exchange, clearing, or settlement system.

## Overview

The 17-State Market organizes market behavior into five interacting subsystems. Its goal is to make transitions, event ordering, transaction dependencies, risk decisions, and retrospective model changes explicit and testable.

The **17 named states are not a claim that a market has only 17 possible configurations**. They are the named components of a constrained state-machine model. Which combinations are valid depends on transition guards, transaction dependencies, instrument status, and other invariants.

## The 17 states

| Symbol | State | Subsystem |
|---|---|---|
| O | Open | Price Formation |
| H | High | Price Formation |
| L | Low | Price Formation |
| C | Close | Price Formation |
| V | Data Validation | Market Intelligence |
| I | Introspection | Market Intelligence |
| R | Reflection | Market Intelligence |
| A | Arbitrage | Market Intelligence |
| E | Order Execution | Transaction Operations |
| Q | Clearing | Transaction Operations |
| S | Settlement | Transaction Operations |
| K | Risk Assessment | Institutional Governance |
| D | Delisting | Institutional Governance |
| U | Suspension | Institutional Governance |
| J | Re-listing | Institutional Governance |
| T | Retrospection | Learning and Evaluation |
| M | Model Revision | Learning and Evaluation |

### Five subsystem layers

1. **Price Formation — O, H, L, C:** represents the open, high, low, and close values of a market interval.
2. **Market Intelligence — V, I, R, A:** validates data, inspects model state, reflects on evidence, and evaluates potential arbitrage.
3. **Transaction Operations — E, Q, S:** separates order execution, clearing, and settlement into distinct stages.
4. **Institutional Governance — K, D, U, J:** represents risk assessment and the distinct actions of delisting, suspension, and re-listing.
5. **Learning and Evaluation — T, M:** evaluates historical decisions and governs model revisions.

The layers are logically interacting; a production-grade implementation would need an explicit concurrency model and jurisdiction-specific governance rules.

## Design invariants and policies

- **OHLC consistency:** low <= min(open, close), high >= max(open, close), and low <= high.
- **Deterministic event order:** events are ordered by (timestamp, sequence, event_id).
- **Explicit transaction progression:** the normal route is order submission → execution → clearing → settlement. Later stages cannot be skipped.
- **Arbitrage is conditional:** a discrepancy alone does not authorize execution; data validity, net-profit thresholds, liquidity, and risk-policy checks matter.
- **Risk signals are not automatic institutional actions:** a negative estimated equity risk premium does not by itself trigger delisting.
- **Suspension is distinct from delisting:** suspension blocks ordinary new orders for the affected instrument without silently erasing outstanding obligations.
- **Model changes are governed:** a revised model must pass the required tests and approval before activation.
- **Historical decisions retain context:** retrospective evaluation should preserve the information set and model version used for each decision.

These are policies of this reference model, not universal statements of exchange rules. Real deployments would require applicable law, market rules, and institutional controls to be represented explicitly.

## Implementation

### Deterministic event processor

The file **src/market17/event_processor.py** provides an in-memory processor with:

- deterministic event-time ordering, including control events;
- instrument-scoped suspension and listing checks;
- guarded transaction progression;
- duplicate event-ID handling and an append-only in-memory audit log;
- atomic rollback of in-memory state when batch processing raises an ordinary exception;
- rejection of events that arrive earlier than the last accepted event for an instrument;
- a reachability invariant for transaction-stage flags.

The current late-event policy rejects an out-of-order event rather than rewinding state. A production event-time system would need a documented lateness window, correction/replay policy, and durable event history.

### Persistent journal and recovery

The file **src/market17/persistent.py** provides an optional local JSON Lines (JSONL) event journal.

- New records use schema version 3, a monotonically increasing record index, a SHA-512 digest, and a previous_sha512 link.
- Recovery validates record structure, digest, index, and chain continuity before replaying into a private processor.
- Legacy version-1 and version-2 records can be read, but legacy records are rejected after version 3 hash chaining begins.
- A failed validation or replay leaves the supplied processor unchanged.
- Journal appends are flushed and synchronized with fsync before the corresponding in-memory batch is applied.
- On POSIX systems, an advisory exclusive file lock serializes cooperating local writers, and stale processor instances are rejected.

**Integrity boundary:** the hash chain helps detect edits, replacement, or reordering within a retained chain. It does not authenticate a journal against an actor who can rewrite the whole file and recompute its hashes, and a missing final suffix cannot be proven absent without an external trusted checkpoint. POSIX advisory locks are neither distributed locks nor a guarantee for filesystems that do not honor them.

### Bounded state-space check

The tests enumerate all 2^4 = 16 combinations of the four transaction-stage flags. Exactly five are reachable prefixes of the normal transaction route. This is a finite check of that invariant, not a proof of every possible configuration of the complete market model.

## Quick start

**Requirements:** Python 3.10 or later. The implementation and tests use the Python standard library.

From the repository root, run the unit tests:

~~~bash
PYTHONPATH=src python -m unittest discover -s tests -v
~~~

Example of processing a batch and recovering it by replaying the same journal:

~~~python
from market17.event_processor import Event, EventKind
from market17.persistent import PersistentEventProcessor

market = PersistentEventProcessor("data/market-events.jsonl")
market.process_batch([
    Event("submit-1", 1, 1, "ABC", EventKind.SUBMIT_ORDER, "tx-1"),
    Event("execute-1", 2, 1, "ABC", EventKind.EXECUTION_CONFIRMED, "tx-1"),
])

recovered = PersistentEventProcessor("data/market-events.jsonl")
assert recovered.processor.invariants_hold()
~~~

## Repository layout

~~~text
src/market17/model.py             State, transition, and guard definitions
src/market17/event_processor.py   Deterministic in-memory event processor
src/market17/persistent.py        Local JSONL journal, integrity checks, and replay
tests/test_model.py               Architecture and core safety-guard tests
tests/test_event_processor.py     Ordering, recovery, and reachability tests
tests/test_persistent.py          Persistence, integrity, and failure-path tests
tests/test_state_explorer.py      Bounded explorer and guard tests
~~~

## Verification and current limitations

The repository's configured GitHub Actions unit-test workflow has passed on **Python 3.10, 3.11, and 3.12**. The latest full-suite run is available in [GitHub Actions](https://github.com/TheRealoliGARCH/17StateMarket/actions/runs/41279639971).

Passing tests establish that the configured test cases pass; they do not establish correctness under every concurrency interleaving, every crash or filesystem failure, all market regimes, or production workloads.

The current implementation does **not** provide:

- connectivity to a live broker, exchange, clearing house, or settlement system;
- distributed consensus or replicated durable storage;
- a distributed writer lock;
- a regulatory-grade or externally authenticated audit trail;
- automatic safe migration across arbitrary software-version changes;
- a comprehensive specification of every state combination and transition failure path.

The local journal's replay behavior depends on the implementation used to interpret recorded events. Compatibility and migration controls are required when behavior changes across software versions. Before operational use, each transition should specify its triggering event, guard, side effect, audit record, failure path, and recovery procedure.

## Repository map

- **Source:** [src/market17/](https://github.com/TheRealoliGARCH/17StateMarket/tree/main/src/market17)
- **Tests:** [tests/](https://github.com/TheRealoliGARCH/17StateMarket/tree/main/tests)
- **Workflow runs:** [GitHub Actions](https://github.com/TheRealoliGARCH/17StateMarket/actions)
- **License:** see [LICENSE](LICENSE).

## License

See [LICENSE](LICENSE).
