# The 17-State Market

This repository contains a formal and computational specification of the **17-State Market**, a hierarchical extended-state-machine model for market price formation, analysis, arbitrage, transaction processing, governance, and retrospective learning.

The reference implementation is a research scaffold. It does not connect to a broker, exchange, clearing house, or settlement system and must not be used as a production trading system.

## The 17 named states

| Symbol | State | Subsystem |
|---|---|---|
| O | Open | Price Formation |
| H | High | Price Formation |
| L | Low | Price Formation |
| C | Close | Price Formation |
| I | Introspection | Market Intelligence |
| R | Reflection | Market Intelligence |
| A | Arbitrage | Market Intelligence |
| S | Settlement | Transaction Operations |
| D | Delisting | Institutional Governance |
| T | Retrospection | Learning and Evaluation |
| V | Data Validation | Market Intelligence |
| K | Risk Assessment | Institutional Governance |
| E | Order Execution | Transaction Operations |
| Q | Clearing | Transaction Operations |
| U | Suspension | Institutional Governance |
| J | Re-listing | Institutional Governance |
| M | Model Revision | Learning and Evaluation |

The five subsystems contain 4, 4, 3, 4, and 2 named states, respectively. The 17 named states are not a claim that the global market can occupy only 17 configurations. The subsystem configuration space is constrained by guards, transaction dependencies, listing status, and other invariants.

## Architecture

- **Price Formation:** O, H, L, C.
- **Market Intelligence:** V, I, R, A.
- **Transaction Operations:** E, Q, S.
- **Institutional Governance:** K, D, U, J.
- **Learning and Evaluation:** T, M.

The subsystems are logically concurrent. A real implementation must specify which combinations can coexist and how synchronized events are processed.

## Core design rules

1. A completed OHLC record must satisfy `low <= min(open, close)`, `high >= max(open, close)`, and `low <= high`.
2. The adjacency relation defines structural transitions; guards decide whether transitions are enabled in a particular context.
3. An arbitrage discrepancy does not itself justify execution. The reference guard checks data validity, net profit against a threshold, liquidity, and risk-policy approval.
4. A negative estimated equity risk premium is a signal, not an automatic delisting command. Delisting requires a completed risk assessment, applicable criteria, and authorization in this proposed policy.
5. For the normal modeled route, settlement requires successful clearing.
6. An effective suspension blocks ordinary new orders for the affected instrument. It does not silently erase outstanding obligations.
7. A model revision does not activate until testing and approval pass.
8. Historical evaluation should preserve the information set and model version used for each prior decision.

These are design choices for this model, not universal descriptions of every exchange's legal or operational rules. The governance rules must be parameterized for the jurisdiction and market under study.

## Event processor and event-time policy

`src/market17/event_processor.py` provides an in-memory event processor with:
- deterministic ordering by `(timestamp, sequence, event_id)`;
- the same event-time ordering for suspension/resumption controls and ordinary events;
- instrument-scoped suspension and listing checks;
- transaction progression through order submission, execution, clearing, and settlement;
- guards against skipping transaction stages;
- duplicate event-ID handling and an append-only in-memory audit log;
- in-memory batch rollback if an unexpected exception interrupts processing;
- an invariant check that transaction flags form a reachable prefix of the normal route.

The ordering policy is explicit: a suspension affects events at or after its position in the event-time ordering. A later suspension does not retroactively block an earlier order. The processor rejects an event that sorts before the last accepted event for that instrument as **late**, rather than rewinding prior state. This simple watermark policy is a reference assumption; production event-time processing needs a documented lateness window, correction/replay policy, and durable event log.

A blocked or rejected event ID is consumed for idempotency. A retry after a state change must use a new event ID. This prevents a repeated delivery from changing the outcome of an already processed event silently.

## Persistent event journal and recovery

`src/market17/persistent.py` adds an optional local JSON Lines journal. `PersistentEventProcessor` writes each input batch as a versioned record, flushes it to disk, and calls `fsync` before applying the batch to the in-memory processor. On an ordinary processing exception, it truncates the appended record and re-raises; the underlying processor's batch rollback restores in-memory state. On construction, it replays journal batches in their original batch sequence, while each batch retains the event processor's canonical event-time ordering.

Example:

```python
from market17.event_processor import Event, EventKind
from market17.persistent import PersistentEventProcessor

market = PersistentEventProcessor("data/market-events.jsonl")
market.process_batch([
    Event("submit-1", 1, 1, "ABC", EventKind.SUBMIT_ORDER, "tx-1"),
    Event("execute-1", 2, 1, "ABC", EventKind.EXECUTION_CONFIRMED, "tx-1"),
])

# Reopening the same journal reconstructs state by replay:
recovered = PersistentEventProcessor("data/market-events.jsonl")
assert recovered.processor.invariants_hold()
```

Journal recovery fails closed on malformed or unsupported records instead of silently skipping them. The journal is local, append-only JSONL; it has no inter-process locking, log rotation, checksums, replicated storage, schema migration framework, or protection against every possible crash/filesystem failure. The wrapper assumes a fresh processor when replaying an existing journal. Do not share one journal between concurrent writers. This is a recovery scaffold, not a durable distributed transaction protocol.

## Safety and reachability checks

The transaction flags are constrained by:
- execution implies order submission;
- clearing implies execution;
- settlement implies clearing.

The exhaustive unit test enumerates all `2**4 = 16` Boolean combinations and verifies that exactly five are reachable prefixes of the normal route: no stage completed, order submitted, executed, cleared, or settled. This is a finite invariant check over the four transaction flags, not a proof of all reachable states of the complete market model.

## Repository layout

```text
src/market17/model.py             State, transition, and guard definitions
src/market17/event_processor.py   Deterministic in-memory event processor
src/market17/persistent.py        Local JSONL journal and deterministic replay
tests/test_model.py               Architecture and core safety guard tests
tests/test_event_processor.py     Ordering, recovery, and reachability tests
tests/test_persistent.py          Persistence, replay, and failure-path tests
tests/test_state_explorer.py      Bounded explorer and guard tests
```

## Run tests

Python 3.10 or later is recommended. The implementation uses only the Python standard library.

From the repository root:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Scope and limitations

The event processor does not connect to live market infrastructure. The local journal provides replay after ordinary process restarts when its records remain intact, but does not provide distributed consensus, concurrent-writer safety, replicated durability, or a regulatory-grade audit trail. The in-memory batch rollback cannot protect against process termination, machine failure, external side effects, or concurrent writers. Journal recovery re-executes the recorded event batches under the current implementation, so behavior changes across software versions require explicit compatibility and migration controls.

The subsystem adjacency table is an initial structural model. Every transition should have a documented event, guard, side effect, audit record, and failure path before use in a simulation or operational system.

## License

See [LICENSE](LICENSE).
