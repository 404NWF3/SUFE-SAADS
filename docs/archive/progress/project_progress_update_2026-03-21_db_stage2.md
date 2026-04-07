# WP1-2 Progress Update: Stage-2 Database Integration

## 1. Purpose

This document records the project state after completing the stage-2 database-integration milestone.

The goal of this milestone was not to merge `WP1-2` back into the main repository yet. Instead, the goal was:

- keep `WP1-2` as a locally independent development repository
- consume real upstream threat-intelligence feed data from the main SAADS database path
- do so through a thin adapter boundary that can still be merged back cleanly later

## 2. What Was Achieved

`WP1-2` now supports two feed modes:

- `mock`
  - deterministic local development
  - smoke tests
  - no dependency on the main repository database path
- `db`
  - reads real feed rows from the main SAADS database capability
  - uses the main repository `db` module as an external capability provider

This means the repository is no longer limited to mock-only upstream inputs.

## 3. Integration Path

The current stage-2 data path is:

```text
WP1-2 graph
  -> AttackFeedProvider abstraction
  -> DbAttackFeedProvider
  -> main-repo db.UnitOfWork(read_only=True)
  -> Wp12FeedService
  -> wp11.v_wp12_attack_feed
```

That path preserves the original boundary rules:

- `WP1-2` does not write raw SQL
- `WP1-2` does not reimplement the main-project `db` layer
- `WP1-2` keeps database integration inside the `data/` adapter boundary

## 4. Design Rationale

The adapter-based implementation was chosen for three reasons:

### 4.1 Keep Local Development Independent

The repository still needs to support local development without forcing every task to depend on a live database or on the full main-repo code tree.

### 4.2 Preserve Merge-Back Cleanliness

The current code should be able to merge back into the main repository without later throwing away the architecture. By isolating the database path behind `AttackFeedProvider`, the graph logic remains unchanged across environments.

### 4.3 Respect the Existing Main-Repo `db` Boundary

The main repository already defines:

- `connection.py`
- `UnitOfWork`
- `ReadModelRepository`
- `Wp12FeedService`

So the correct move was to consume those capabilities rather than bypass or duplicate them.

## 5. Code-Level Changes in WP1-2

The following local-repository changes were introduced to enable stage-2 integration:

- `saads_wp12/data/db_feed_provider.py`
  - new database-backed feed adapter
  - loads the main-repo `db` modules at runtime
  - reads feed rows through `UnitOfWork` and `Wp12FeedService`
  - maps upstream `Wp12AttackFeedRow` objects into local `Wp12AttackFeedItem`
- `saads_wp12/data/feed_provider.py`
  - provider factory now selects between `mock` and `db` mode
- `saads_wp12/nodes/intel.py`
  - now depends on the provider abstraction instead of constructing the mock provider directly
- `saads_wp12/config.py`
  - now supports feed-mode and main-repo backend-path configuration
- `saads_wp12/run_local.py`
  - now keeps the demo attack identifier only in mock mode
  - database mode defaults to consuming a real feed item

## 6. Runtime Configuration

The stage-2 path is activated by runtime configuration, not by changing graph code.

Typical configuration includes:

```env
WP12_FEED_SOURCE=db
SAADS_MAIN_BACKEND_PATH=C:\Users\Administrator\Desktop\saads-main\backend
POSTGRES_HOST=...
POSTGRES_PORT=5432
POSTGRES_DB=...
POSTGRES_SCHEMA=wp11
POSTGRES_USER=...
POSTGRES_PASSWORD=...
```

Mock mode remains available simply by leaving `WP12_FEED_SOURCE` unset or setting it to `mock`.

## 7. Validation Results

The following validations were completed during this milestone:

1. existing smoke tests still pass in mock mode
2. the provider factory switches correctly into database mode
3. `WP1-2` can read a real feed item from the upstream database path
4. the local graph entrypoint can run successfully with a real database-backed input

A successful database-backed local run now returns output shaped like:

```json
{
  "run_id": "run-...",
  "attack_id": "<real uuid from db feed>",
  "attack_family": "prompt_injection",
  "env_status": "ready",
  "pass_rate": 0.8,
  "pass_rate_threshold": 0.8,
  "llm_mode": "rule",
  "verdict": "pass",
  "persistence_path": "artifacts\\run-....json"
}
```

This confirms that the repository can already execute end-to-end with a real upstream feed item.

## 8. What Is Still Pending

This milestone does not mean the project is fully productionized yet.

Still pending:

1. better handling of sparse real feed rows
2. stronger contract checks between upstream read models and local state assumptions
3. real environment-build integration
4. real execution/evidence/scoring path beyond current mock execution logic
5. deeper LLM-backed implementations for more subgraph components

## 9. Updated Status Summary

The most accurate project summary after this milestone is:

**WP1-2 is now a runnable LangGraph security-evaluation prototype that supports both mock-mode local development and stage-2 real-database integration through a thin adapter boundary.**

This is important because it proves:

- the current repository can still evolve independently
- the upstream database contract is already usable
- the current architecture remains compatible with a future merge back into the main SAADS repository

## 10. Recommended Next Steps

The next practical priorities should be:

1. audit downstream nodes for hidden mock-data assumptions
2. harden the graph against partially filled real feed rows
3. document the operational difference between `mock` and `db` modes
4. continue replacing mock downstream integrations one by one

## 11. Minimal Scheduler Scaffold Added

After stage-2 database integration was proven to work end-to-end, the repository also added a minimal scheduler scaffold for the next automation step.

The goal of this scaffold is simple:

- keep `WP1-2` itself focused on processing one threat-intelligence item at a time
- add a separate outer loop that can register jobs, claim one pending job, invoke the graph, and store execution status

### 11.1 Database Table

A new SQL file was added:

- `docs/sql/wp12_eval_jobs.sql`

This file defines a minimal table under `wp11`:

- `wp11.wp12_eval_jobs`

The table tracks:

- which `attack_id` has already been registered as a job
- whether that job is `pending`, `running`, `done`, or `failed`
- the final `run_id` and `verdict` when a run completes
- the last error message when a run fails

### 11.2 Local Scheduler Scripts

Two local scheduler files were added:

- `saads_wp12/scheduler/job_store.py`
- `saads_wp12/scheduler/run_scheduler.py`

Their responsibilities are:

- `job_store.py`
  - read and update `wp11.wp12_eval_jobs`
  - register new feed rows as `pending`
  - claim the next `pending` job
  - mark a job as `done` or `failed`
- `run_scheduler.py`
  - read current feed rows from the main-repo database path
  - register any unseen items in `wp12_eval_jobs`
  - claim one pending job
  - invoke the existing `WP1-2` graph with that `attack_id`
  - write the result back into the job table

### 11.3 Current Scope

This is intentionally only a minimal first step.

It does **not** yet provide:

- multi-job batching
- priority scoring
- retry policies beyond a simple counter
- long-running monitoring service mode
- system-level scheduling (for example, Windows Task Scheduler)

Instead, it establishes the basic architecture needed for those later capabilities:

```text
database feed -> job table -> scheduler -> WP1-2 graph -> job status update
```

## 12. Minimal Automatic Polling Added

The scheduler scaffold has now been extended one step further so the repository can move from manual one-shot scheduling toward automatic database polling.

### 12.1 What Was Added

The scheduler now supports two additional behaviors:

- recycle stale `running` jobs back to `pending`
- optionally stay in a polling loop and keep checking the database feed repeatedly

### 12.2 Why This Matters

Without these two behaviors, the scheduler would still require too much manual intervention:

- a crashed run could leave a job stuck in `running`
- the operator would need to manually rerun the script each time a new feed item arrived

With the new behavior:

- obviously stale `running` jobs can be reclaimed
- the same scheduler entrypoint can now work either as a one-shot command or as a simple long-running poller

### 12.3 Runtime Controls

The following runtime flags now exist:

```env
WP12_SCHEDULER_LOOP=false
WP12_SCHEDULER_POLL_INTERVAL_SECONDS=300
WP12_SCHEDULER_STALE_RUNNING_SECONDS=600
```

Meaning:

- `WP12_SCHEDULER_LOOP=false`
  - run only one scheduler tick, then exit
- `WP12_SCHEDULER_LOOP=true`
  - keep polling the database in a loop
- `WP12_SCHEDULER_POLL_INTERVAL_SECONDS`
  - how many seconds to wait between polling rounds
- `WP12_SCHEDULER_STALE_RUNNING_SECONDS`
  - how long a job may stay in `running` before it is recycled back to `pending`
