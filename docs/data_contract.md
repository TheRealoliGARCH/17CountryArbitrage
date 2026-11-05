# 17-country panel and observation data contract

**Status:** Initial specification. This document defines the panel identity and the minimum contract for future market observations. It does not assert that instruments, source feeds, or executable markets are currently configured.

## 1. Panel identity

The canonical panel is stored in `config/country_panel.csv`. It contains 17 unique ISO 3166-1 alpha-2 country identifiers. Currency codes are ISO 4217 codes and identify the national currency convention used for the initial panel registry; they do not identify a specific bond, yield curve, trading venue, or hedge instrument.

The panel has 17 members, 136 unordered country pairs, and 272 directed pair relationships. Pair counts are combinatorial and do not imply market access or tradability.

## 2. Canonical observation grain

The canonical raw observation grain is:

**one instrument × one observation timestamp × one measure × one source vintage.**

Do not combine observations with different maturities, instrument types, currencies, compounding conventions, or source vintages into one series.

A future normalized observation table should contain at least:

| Field | Type | Required | Definition |
|---|---|---:|---|
| `country_code` | string | yes | ISO 3166-1 alpha-2 identifier from the panel registry |
| `instrument_id` | string | yes | Stable source or project identifier for the exact instrument |
| `instrument_type` | string | yes | For example, sovereign bill, sovereign bond, OIS, policy rate, or FX forward |
| `measure` | string | yes | Explicit measure name, such as mid_yield, bid_yield, ask_yield, price, or total_return |
| `observation_time` | ISO 8601 timestamp | yes | Timestamp to which the observation applies |
| `availability_time` | ISO 8601 timestamp | yes | Earliest time the value was publicly or operationally available |
| `value` | finite number | yes | Numeric observation in the declared unit |
| `unit` | string | yes | For example percent_per_annum, decimal, price_points, or index_points |
| `currency_code` | string | yes | ISO 4217 denomination of the instrument or measure |
| `maturity_date` | date or null | conditional | Contractual maturity where applicable |
| `tenor` | string or null | conditional | Standardized tenor where applicable |
| `day_count` | string or null | conditional | Day-count convention where applicable |
| `compounding` | string or null | conditional | Compounding convention where applicable |
| `source_name` | string | yes | Publisher, vendor, or institution |
| `source_series_id` | string | yes | Original series or instrument identifier |
| `retrieved_at` | ISO 8601 timestamp | yes | Time the project retrieved the record |
| `source_vintage` | string | yes | Release date, revision identifier, or immutable source snapshot |
| `quality_status` | enum | yes | valid, missing, stale, provisional, revised, rejected |
| `notes` | string | no | Provenance or quality annotations |

The schema is a target contract, not a claim that all fields are available from every source. Missing required metadata must be represented as missing and handled by validation; it must not be silently fabricated.

## 3. Time and vintage discipline

1. Store timestamps in ISO 8601 with an explicit UTC offset; normalize computational timestamps to UTC while retaining the original source timestamp and timezone metadata.
2. Preserve both `observation_time` and `availability_time`. Backtests must not use a value before it was available.
3. Preserve revisions and source vintages. Do not overwrite historical values without retaining the previous vintage.
4. Use an explicit market calendar and session convention for every instrument. A country-level calendar is not a substitute for an instrument calendar.
5. Do not forward-fill across market closures, missing releases, or stale observations unless a documented model explicitly permits it.

## 4. Comparability requirements

Before comparing two yield or return observations, verify and record:

- instrument class, issuer, seniority, currency, maturity, and tenor;
- yield definition, price convention, compounding, and day-count convention;
- bid, ask, or mid status and quote timestamp;
- duration, modified duration, and convexity where relevant;
- source market, liquidity status, and trading calendar;
- currency conversion and hedge convention, including forward points and cross-currency basis where relevant;
- collateral, funding, financing, tax, and transaction-cost assumptions.

A raw yield spread is descriptive. A currency-hedged total-return differential requires matched holding periods, a declared hedge instrument and roll convention, and realized or consistently modelled hedge costs. Neither statistic is automatically an arbitrage profit.

## 5. Validation gates

Reject or quarantine a record if any of the following applies:

- country code is not in the canonical panel;
- instrument identifier, measure, source, or timestamp is absent;
- numeric value is non-finite;
- unit or currency is inconsistent with the instrument metadata;
- observation or availability timestamp cannot be parsed;
- source vintage is missing;
- duplicate key conflicts exist for the same instrument, measure, observation time, and source vintage;
- value violates a documented instrument-specific domain rule.

Do not impose a universal positive-yield constraint: negative yields can be economically valid. Do not infer zero from a missing value. Distinguish missing, stale, provisional, revised, and rejected observations.

## 6. Suggested normalized keys

A raw-record uniqueness key is:

`(source_name, source_series_id, instrument_id, measure, observation_time, source_vintage)`

A project-level observation identity is:

`(country_code, instrument_id, measure, observation_time, source_vintage)`

If two sources disagree, retain both source records and resolve them through an explicit source-priority or reconciliation policy. Never silently select one.

## 7. Data layers

Keep the following layers separate:

1. **Raw:** immutable source payload or downloaded file, retrieval metadata, checksum, and license/access notes.
2. **Validated:** parsed records with schema and quality checks; rejected records remain traceable.
3. **Normalized:** standardized units, timestamps, identifiers, and conventions, with transformations recorded.
4. **Analytical:** matched curves, spreads, FX-hedged returns, features, and pair-level panels.
5. **Research output:** model estimates, signals, portfolio simulations, and evaluation results.

Every derived field should have a reproducible transformation and versioned code reference.

## 8. Not yet specified

The project has not yet selected the exact sovereign instruments, benchmark maturities, data providers, sampling frequency, source hierarchy, market calendars, or FX-hedge instruments for each country. These decisions must be made before constructing a cross-country investable return panel. Access restrictions, sanctions, local regulations, and settlement constraints must be assessed independently for each instrument and jurisdiction.

## 9. Acceptance criteria for the first data-ingestion implementation

The first ingestion module should demonstrate:

- exact match to the 17-member registry;
- schema validation and finite-number checks;
- preservation of source and retrieval metadata;
- deterministic duplicate detection;
- explicit UTC normalization without losing source-time information;
- no implicit forward fill or fabricated values;
- reproducible quarantine output for invalid records;
- unit tests covering valid, invalid, duplicate, stale, revised, and missing observations.

Only after these tests pass should the project add country-specific acquisition adapters.
