# 36-Country Arbitrage

**A research framework connecting international monetary and sovereign-market relationships with graph theory, Ramsey theory, and a 17-state market architecture across 36 central-bank jurisdictions.**

[![Unit tests](https://github.com/TheRealoliGARCH/36CountryArbitrage/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/TheRealoliGARCH/36CountryArbitrage/actions/workflows/unit-tests.yml)

> **Research status:** This repository is a mathematical, economic, and institutional research project. The Ramsey-theoretic result described below is an exact theorem. Its interpretation as an economy of central-bank jurisdictions is a modelling framework, not a theorem about actual cooperation, market behaviour, monetary-policy coordination, or profitable arbitrage. The repository's treatises should be read with that distinction in view.

## Research programme

The project studies a 36-jurisdiction monetary and financial network through several connected lenses:

- international monetary economics and sovereign financial conditions;
- bilateral relationships and network representations;
- combinatorial graph theory and Ramsey theory;
- the institutional and operational architecture of a multi-market system;
- the 17-State Market framework for market-state processing, governance, and retrospective evaluation.

The current centrepiece is the treatise:

**[2. The Complete Treatise on a Ramsey R(3, 9) Economy of Central Bank Governors (PDF)](https://github.com/TheRealoliGARCH/36CountryArbitrage/blob/main/2.%20The%20Complete%20Treatise%20on%20a%20Ramsey%20R(3,%209)%20Economy%20of%20Central%20Bank%20Governors.pdf)**

It places the exact Ramsey number R(3, 9) = 36 in dialogue with a constructed panel of 36 central-bank jurisdictions. The mathematical theorem supplies a combinatorial constraint; the economic interpretation requires an explicit definition of the relationships being classified and empirical validation.

## The 36-jurisdiction panel

The panel, arranged in alphabetical order, is:

| No. | Jurisdiction | No. | Jurisdiction | No. | Jurisdiction |
|---:|---|---:|---|---:|---|
| 1 | Argentina | 13 | Ireland | 25 | Russia |
| 2 | Australia | 14 | Israel | 26 | Saudi Arabia |
| 3 | Austria | 15 | Italy | 27 | Singapore |
| 4 | Belgium | 16 | Japan | 28 | South Korea |
| 5 | Brazil | 17 | Luxembourg | 29 | Spain |
| 6 | Canada | 18 | Mexico | 30 | Sweden |
| 7 | China | 19 | Netherlands | 31 | Switzerland |
| 8 | Denmark | 20 | New Zealand | 32 | Thailand |
| 9 | France | 21 | North Korea (DPRK) | 33 | Türkiye |
| 10 | Germany | 22 | Norway | 34 | United Arab Emirates |
| 11 | India | 23 | Pakistan | 35 | United Kingdom |
| 12 | Indonesia | 24 | Poland | 36 | United States |

The panel is a research selection, not a claim that these 36 jurisdictions form a single monetary union or possess identical institutional powers. In particular, jurisdictions sharing the euro participate in the Eurosystem framework; national central banks do not each independently set a national policy rate.

## Ramsey-theoretic foundation

The classical Ramsey number R(3, 9) is the smallest integer n such that every red-blue colouring of the edges of the complete graph K_n contains either a red complete subgraph on three vertices or a blue complete subgraph on nine vertices.

The exact result is:

**R(3, 9) = 36.**

Consequently:

- every two-colouring of the 630 edges of K_36 contains a monochromatic K_3 in one colour or a monochromatic K_9 in the other;
- there exists a two-colouring of K_35 with neither a monochromatic K_3 nor a monochromatic K_9;
- the complete undirected graph K_36 has 36 vertices and 630 unordered edges;
- it has 1,260 directed arcs if each undirected pair is represented in both directions;
- it contains 7,140 unordered three-vertex subsets.

These are combinatorial facts. Their use in an economic model depends on how vertices, edges, colours, and cliques are operationally defined.

### Economic interpretation: requirements

An economic application must specify, before classifying the graph:

1. **Vertices:** the jurisdictional units included in the panel and the institutional meaning of each unit.
2. **Edges:** whether an edge represents a potential bilateral relationship, an observed exposure, a legal arrangement, a financial flow, or another measurable connection.
3. **Colours:** the binary rule used to classify each edge, including thresholds, time horizon, data source, and treatment of missing or ambiguous observations.
4. **Time:** whether the graph is static, rolling-window, or time-varying.
5. **Inference:** how uncertainty, classification error, and structural changes are handled.

A complete graph is a representation of all possible pairs in the selected panel. It does not assert that all 630 bilateral relationships are active, liquid, legally accessible, or economically significant. Nor does the two-colour Ramsey theorem directly establish results for three or more colours.

## Network dimensions

For 36 vertices, the basic combinatorial quantities are:

| Object | Expression | Count |
|---|---:|---:|
| Jurisdictions / vertices | n | 36 |
| Unordered bilateral pairs | n(n-1)/2 | 630 |
| Directed bilateral arcs, without self-loops | n(n-1) | 1,260 |
| Unordered triads | n(n-1)(n-2)/6 | 7,140 |

These counts define the size of the potential analytical space. They are not counts of observed transactions, central-bank agreements, currency pairs, or investable arbitrage opportunities.

## Connection to the 17-State Market

The repository also retains the earlier 17-State Market treatises. The 17-State Market is a proposed market-processing and governance architecture. Its states are grouped into five functional layers:

| Layer | States | Function |
|---|---|---|
| Price Formation | O, H, L, C | Open, high, low, and close observations |
| Market Intelligence | V, I, R, A | Data validation, introspection, reflection, and arbitrage assessment |
| Transaction Operations | E, Q, S | Execution, clearing, and settlement |
| Institutional Governance | K, D, U, J | Risk assessment, delisting, suspension, and re-listing |
| Learning and Evaluation | T, M | Retrospection and model revision |

The 36-jurisdiction graph and the 17-state market architecture describe different dimensions of the research programme. The former represents jurisdictional relationships; the latter represents a proposed sequence of market states and governance functions. They should not be conflated or treated as a one-to-one mapping.

## Publications in this repository

1. **[The Complete Treatise on the Seventeen-State Market (PDF)](https://github.com/TheRealoliGARCH/36CountryArbitrage/blob/main/0.%20The%20Complete%20Treatise%20on%20the%20Seventeen-State%20Market.pdf)** — introduces the 17-state market architecture.
2. **[The Complete Treatise on Extensions to the Seventeen-State Market (PDF)](https://github.com/TheRealoliGARCH/36CountryArbitrage/blob/main/1.%20The%20Complete%20Treatise%20on%20Extensions%20to%20the%20Seventeen-State%20Market.pdf)** — develops extensions to that architecture.
3. **[The Complete Treatise on a Ramsey R(3, 9) Economy of Central Bank Governors (PDF)](https://github.com/TheRealoliGARCH/36CountryArbitrage/blob/main/2.%20The%20Complete%20Treatise%20on%20a%20Ramsey%20R(3,%209)%20Economy%20of%20Central%20Bank%20Governors.pdf)** — connects the 36-jurisdiction panel to the exact Ramsey R(3, 9) result and explores its economic and institutional interpretations.

## Research principles and limitations

- **Separate theorem from application.** The exact Ramsey number is a mathematical result; economic conclusions require additional premises and evidence.
- **Define the edge before colouring it.** A binary classification must have a documented operational meaning and reproducible rule.
- **Do not infer cooperation from a clique.** A monochromatic clique is a graph-theoretic structure, not proof of policy coordination or a treaty.
- **Do not infer arbitrage from a rate differential.** An executable opportunity requires comparable instruments, currency and funding treatment, bid-ask prices, transaction costs, market access, and risk controls.
- **Respect institutional structure.** Central-bank mandates, monetary unions, legal authority, and operational arrangements differ across jurisdictions.
- **Preserve data provenance.** Record source, timestamp, vintage, revisions, missingness, and transformation rules.
- **Test out of sample.** Empirical claims should use chronological validation, robustness checks, and transparent uncertainty estimates.
- **Treat network counts as potential topology.** A complete graph does not imply that every edge is observed or tradable.

The GDP-coverage figure discussed in the research process is a provisional estimate, not a verified headline statistic. A defensible percentage requires a single consistent data vintage, reference year, nominal-GDP definition, and world-GDP denominator across all 36 jurisdictions.

## Repository structure

~~~text
.
├── .github/                 # Repository workflows
├── config/                  # Configuration
├── docs/                    # Supporting documentation
├── src/                     # Source code
├── tests/                   # Tests
├── 0. The Complete Treatise on the Seventeen-State Market.pdf
├── 1. The Complete Treatise on Extensions to the Seventeen-State Market.pdf
├── 2. The Complete Treatise on a Ramsey R(3, 9) Economy of Central Bank Governors.pdf
├── LICENSE
└── README.md
~~~

The code and test directories are retained as part of the wider research repository. Their presence should not be interpreted as evidence that a live 36-jurisdiction arbitrage engine, real-time central-bank data pipeline, or production trading system has been implemented.

## Intended next steps

1. Formalize one or more economically meaningful edge definitions.
2. Specify reproducible binary colouring rules and their treatment of uncertainty.
3. Build a time-indexed data model for the 36-jurisdiction panel.
4. Test the stability of graph classifications across time windows and alternative thresholds.
5. Distinguish descriptive network structure from causal or predictive claims.
6. Where relevant, construct comparable sovereign and monetary-market measures, including currency, duration, credit, liquidity, and funding adjustments.
7. Connect validated outputs to the 17-State Market architecture only after explicit interface and governance specifications are defined.

## License

See [LICENSE](LICENSE).
