# Country-data validation engine

**Status:** Initial standard-library implementation. This module validates and classifies observation records; it does not acquire market data or establish instrument comparability.

## Package

The implementation is in `src/countrydata/`:

- `panel.py` loads the canonical CSV registry and enforces its 17-member shape, unique ISO2 identifiers, and non-empty fields.
- `schema.py` parses mappings into immutable `Observation` records. ISO-8601 timestamps must be parseable; their supplied offsets are retained. UTC-normalized timestamp views are available without overwriting the originals.
- `validation.py` checks panel membership, finite numeric values, currency-code shape, explicit timestamp offsets, quality status, and availability/retrieval ordering.
- `validate_batch` quarantines repeated raw-source keys deterministically and returns accepted and quarantined records separately.

## Important policy boundaries

1. Negative yields are permitted. No universal positive-yield constraint is imposed.
2. A currency code is syntax-checked but is not forced to equal the country's national currency. Foreign-currency issuance can exist; instrument metadata must determine denomination.
3. Different sources sharing a project-level observation identity are retained. They are not silently collapsed or arbitrarily quarantined. Source priority and reconciliation are later normalization policies.
4. A record explicitly marked `rejected` is quarantined. `missing`, `stale`, `provisional`, and `revised` remain distinct statuses and are not silently converted to valid observations.
5. Quarantine is an in-memory validation result in this stage. Durable quarantine storage and raw-payload/checksum retention are future ingestion-layer work.
6. This stage does not impose instrument-specific value bounds, validate ISO codes against an external standards registry, or prove that a source series actually describes the declared instrument.

## Run tests

From the repository root:

~~~bash
PYTHONPATH=src python -m unittest discover -s tests -v
~~~

The test suite uses only Python's standard library and is compatible with the repository's Python 3.10–3.12 CI matrix.
