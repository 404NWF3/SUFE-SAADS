# WP1-2 Module Contract

## 1. Module Position

`WP1-2` is a consumer-side planning module inside the larger `SAADS` project.

Its current responsibility is to consume structured attack feed data and turn that data into a validated security test plan package plus persisted planning artifacts.

It is not currently responsible for:

- environment build automation
- runtime execution of attack scripts
- evidence collection and scoring loops
- database-backed job scheduling

## 2. Core Responsibilities

`WP1-2` is responsible for:

1. reading structured attack feed data
2. normalizing that data into a stable internal format
3. understanding the threat and scope
4. generating a test package
5. validating the generated package
6. finalizing a planning verdict
7. persisting planning artifacts locally

## 3. Runtime Entry Contract

The current operational entrypoint is:

`python -m saads_wp12.run_feed_once`

This entrypoint:

1. pulls attack references from the configured feed provider
2. deduplicates by `attack_id` using a local registry file
3. loads the full feed item before invoking the graph
4. invokes the main graph once per unseen attack
5. stores successful results in the dedup registry

The local single-item debug entrypoint remains:

`python -m saads_wp12.run_local`

## 4. Mainline Contract

The business mainline is defined by:

- `saads_wp12/agent.py`
- `saads_wp12/graphs/main_graph.py`

The graph flow is:

1. `ingest_intel`
2. `normalize_intel`
3. `understand_threat_subgraph`
4. `generate_test_package_subgraph`
5. `validate_test_package`
6. `finalize_plan_result`
7. `persist_plan_artifacts`

## 5. Database Boundary

`WP1-2` may read feed data through adapter-style providers such as:

- `MockAttackFeedProvider`
- `LocalAttackFeedProvider`
- `DbAttackFeedProvider`

The graph itself should remain independent from direct database infrastructure imports.

## 6. Deduplication Contract

Deduplication is now file-based, not job-table-based.

Default registry path:

- `artifacts/processed_attack_ids.json`

Failed runs must not be recorded as processed.

## 7. Primary Outputs

The primary outputs of `WP1-2` are:

- `*_state_raw.json`
- `*_state_presentation.json`
- `*_plan.md`

These are written under:

- `artifacts/<run_id>/`

## 8. Repository Layering

The repository should be organized around:

- `graphs/`
- `nodes/`
- `engines/`
- `data/`
- `reporting/`
- `state.py`
