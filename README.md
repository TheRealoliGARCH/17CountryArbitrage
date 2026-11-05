# 17-Country Arbitrage

**A research framework for cross-country sovereign-bond relative value, monetary-rate relationships, and network-aware arbitrage across 17 national markets, supported by a 17-state market-processing architecture.**

[![Unit tests](https://github.com/TheRealoliGARCH/17CountryArbitrage/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/TheRealoliGARCH/17CountryArbitrage/actions/workflows/unit-tests.yml)

> **Status:** Research implementation. The repository currently contains a deterministic 17-state market event-processing scaffold. The 17-country relative-value and arbitrage framework is the research objective; it must not be mistaken for a live, validated, or production trading system. The automated unit-test workflow has previously passed on Python 3.10, 3.11, and 3.12.

## Research objective

The project studies relative monetary and sovereign-bond conditions across a 17-country panel. Its objective is to identify, measure, validate, and—only where justified by executable prices and risk controls—act on cross-country relative-value opportunities.

The country panel is:

| Code | Country |
|---|---|
| AU | Australia |
| AT | Austria |
| CA | Canada |
| DK | Denmark |
| DE | Germany |
| FR | France |
| IN | India |
| LU | Luxembourg |
| NL | Netherlands |
| NZ | New Zealand |
| NO | Norway |
| PK | Pakistan |
| RU | Russia |
| SG | Singapore |
| SE | Sweden |
| CH | Switzerland |
| US | United States |

The panel contains 17 national observations, 136 unique unordered country pairs, and 272 directed bilateral relationships. These counts describe the analytical network; they do not imply that every pair is investable, liquid, legally accessible, or directly arbitrageable.

## Relative-rate research framework

Let the observed sovereign yield and selected reference rate for country $i$ at time $t$ be denoted by $r_{i,t}$ and $r_{if,t}$. A candidate common reference is:

\[
r_f^*(t)=\min_{1\leq i\leq 17} r_{if,t}.
\]

The corresponding excess-rate measure is:

\[
e_{i,t}=r_{i,t}-r_f^*(t).
\]

A proposed bilateral relative-rate statistic is:

\[
\rho_{ij,t}=\frac{e_{i,t}}{e_{j,t}},
\qquad i\ne j,
\]

where it is numerically and economically well-defined. The diagonal of the relative-rate matrix is one, and reciprocal symmetry holds where both ratios are defined.

These quantities are **research statistics, not executable arbitrage prices**. Ratios can be unstable when a denominator is close to zero and can be difficult to interpret when excess rates are negative. The minimum national reference rate is not automatically a common investable risk-free numeraire.

Cross-country comparisons must account for, as applicable:

- currency denomination and FX-forward or swap hedging;
- cross-currency basis, collateral, and funding costs;
- sovereign credit and default risk;
- duration, convexity, curve shape, carry, and roll-down;
- bid-ask spreads, market depth, market impact, and turnover;
- taxes, capital controls, market access, sanctions, settlement, and legal constraints;
- instrument-specific liquidity and trading calendars.

The empirical programme should therefore distinguish raw yield comparisons, currency-hedged total-return comparisons, and genuinely executable net-of-cost opportunities. A yield differential alone is not proof of arbitrage.

## Analytical network

The 17-country panel induces a complete *analytical* graph with 17 vertices and 136 unique undirected edges. Each edge can carry country-pair features such as:

- yield and reference-rate differentials;
- relative-rate and spread measures;
- FX-hedged return differentials;
- liquidity and transaction-cost estimates;
- duration- and risk-adjusted relative-value signals;
- estimated uncertainty and regime classifications.

A network no-arbitrage layer can test whether observed executable bid and ask prices admit profitable cycles after transaction costs. The graph representation is a modelling device; actual market connectivity, instrument availability, and trading permissions must be established pair by pair.

## The 17-state market architecture

The 17-State Market is the processing and governance scaffold intended to support the research workflow. Its 17 named states are organized into five interacting subsystems:

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

1. **Price Formation — O, H, L, C:** represents open, high, low, and close values of a market interval.
2. **Market Intelligence — V, I, R, A:** validates data, inspects model state, evaluates evidence, and assesses candidate arbitrage.
3. **Transaction Operations — E, Q, S:** separates execution, clearing, and settlement.
4. **Institutional Governance — K, D, U, J:** represents risk assessment and distinct delisting, suspension, and re-listing actions.
5. **Learning and Evaluation — T, M:** evaluates historical decisions and governs model revisions.

The 17 named states are not a claim that a market has only 17 possible configurations. They are components of a constrained state-machine model. The country dimension and the state-machine dimension are distinct: **17 countries do not correspond one-to-one with the 17 operational states.**

## Research and system design principles

- **Signal before execution:** a statistical discrepancy is a candidate signal, not an instruction to trade.
- **Net economics:** assess expected returns after spreads, fees, financing, hedging, market impact, and other applicable costs.
- **Comparable exposures:** control for currency, duration, convexity, credit, liquidity, and instrument characteristics.
- **Data validity:** preserve timestamps, source provenance, revisions, missingness, and market-calendar conventions.
- **No look-ahead:** construct every feature using only information available at the decision timestamp.
- **Out-of-sample evaluation:** use chronological validation, walk-forward testing, and regime-aware performance analysis.
- **Risk governance:** impose position, leverage, liquidity, concentration, drawdown, and country/jurisdiction limits.
- **Auditable decisions:** retain the data snapshot, signal, model version, risk decision, order intent, and execution outcome.
- **Model-change control:** a revised model must pass its required tests and approval before activation.

## Current implementation

The current codebase implements a market state model and event-processing scaffold. It does not yet implement the complete 17-country data pipeline, a validated relative-value strategy, broker connectivity, or live order execution.

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

**Requirements:** Python 3.10 or later. The current implementation and tests use the Python standard library.

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

## Planned research stages

1. **Panel and data specification:** define instruments, maturities, observation frequencies, data provenance, calendars, and missing-data policy for all 17 countries.
2. **Comparable-return construction:** estimate currency-specific curves and construct duration-aware, FX-hedged total-return measures where the required data are available.
3. **Relative-value estimation:** test bilateral spreads, relative-rate statistics, cointegration or error-correction specifications, and regime-dependent deviations.
4. **Network analysis:** evaluate pairwise and cycle-level consistency using executable bid/ask prices and transaction-cost bounds.
5. **Signal validation:** test predictive content, stability, uncertainty, and incremental value against simple benchmarks using strictly chronological out-of-sample evaluation.
6. **Portfolio and execution research:** model sizing, hedging, liquidity, market impact, execution scheduling, and portfolio-level risk before any live deployment is considered.
7. **17-state integration:** connect validated research outputs to explicit data-validation, risk, execution, clearing, settlement, retrospective, and model-governance transitions.

Each stage should have reproducible data contracts, unit tests, documented assumptions, and empirical acceptance criteria.

## Verification and limitations

The repository's configured GitHub Actions unit-test workflow has previously passed on **Python 3.10, 3.11, and 3.12**. Passing tests establish that the configured test cases pass; they do not establish profitability, predictive validity, correctness under every concurrency interleaving, every crash or filesystem failure, all market regimes, or production readiness.

The current implementation does **not** provide:

- a live 17-country market-data acquisition pipeline;
- a validated cross-country trading signal or profitable strategy;
- connectivity to a live broker, exchange, clearing house, or settlement system;
- distributed consensus or replicated durable storage;
- a distributed writer lock;
- a regulatory-grade or externally authenticated audit trail;
- a comprehensive specification of every state combination and transition failure path.

Real deployments would require applicable law, market rules, instrument eligibility, institutional controls, and jurisdiction-specific operational requirements to be represented explicitly. Research results should not be interpreted as investment advice or as evidence of risk-free profit.

## Repository map

- **Source:** [src/market17/](https://github.com/TheRealoliGARCH/17CountryArbitrage/tree/main/src/market17)
- **Tests:** [tests/](https://github.com/TheRealoliGARCH/17CountryArbitrage/tree/main/tests)
- **Workflow runs:** [GitHub Actions](https://github.com/TheRealoliGARCH/17CountryArbitrage/actions)
- **License:** see [LICENSE](LICENSE).

## License

See [LICENSE](LICENSE).
