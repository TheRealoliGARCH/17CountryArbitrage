# Five-Layer Upgrade of the 17-State Market

## Scope

This change extends the existing 17-state research scaffold with explicit service
modules for the five functional layers. It preserves the original 17 state names,
subsystem partition, event processor, persistence format, and state explorer.
It does not create a live exchange, broker gateway, CCP, custodian, or regulatory
decision system.

## Layer map

| Layer | States | New service module | Responsibilities added |
|---|---|---|---|
| Price Formation | O, H, L, C | `price_formation.py` | Order book, deterministic call-auction convention, circuit-breaker guard |
| Market Intelligence | V, I, R, A | `market_intelligence.py` | Robust outlier alerts, net-of-cost arbitrage candidate filter |
| Transaction Operations | E, Q, S | `transaction_operations.py` | Collateral haircuts, margin arithmetic, clearing sufficiency, settlement guard |
| Institutional Governance | K, D, U, J | `institutional_governance.py` | Structured regulatory decision records with authority and evidence fields |
| Learning and Evaluation | T, M | `learning_evaluation.py` | Validation reports, stress scenarios/results, gated model activation |

## Important operational boundaries

- Order-book and auction code is deterministic research logic, not an exchange
  matching engine or an authoritative market-pricing mechanism.
- The call-auction tie-break convention is maximum executable quantity, minimum
  imbalance, then nearest reference price (if supplied), then lower price.
- Circuit breakers halt the local reference object; a reset requires an explicit
  authorization flag. Real deployment requires exchange-specific thresholds,
  market-wide coordination, and authenticated authority.
- Statistical anomalies generate review alerts only. They are not findings of
  manipulation and cannot automatically suspend an instrument.
- An arbitrage candidate is only a positive gross edge exceeding the enumerated
  spread, fee, funding, hedge, impact, settlement, and buffer costs. Currency,
  unit, and horizon must match. Legal, liquidity, counterparty, and risk checks
  remain separate execution gates.
- Collateral value is reduced by a haircut. This basic module does not implement
  eligible-collateral schedules, concentration add-ons, wrong-way risk, FX
  haircuts, intraday calls, or a default waterfall.
- A structurally valid governance record does not prove that the named authority
  actually has legal jurisdiction. Authentication and policy checks are external.
- Validation and stress-test records are evidence containers, not proof of model
  quality. Model activation requires a passed report and an externally
  authorized reviewer.
- Existing event journal hash chaining remains an audit aid, not tamper-proof
  storage. Production deployment requires access controls, key management,
  independent retention, backups, and operational resilience.

## Tests

Run the standard-library suite with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

The added tests cover order-book validation, auction price selection,
circuit-breaker reset authorization, anomaly review flags, net-edge cost
filtering, collateral haircuts, margin arithmetic, settlement gating,
governance evidence fields, and model-activation approval.
