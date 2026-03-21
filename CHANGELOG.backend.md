# Backend Changelog

## 2026-03-21
- Phase 4 dedup vector memory now uses per-record `upsert_record()` with stable Qdrant point ids instead of rebuilding the entire collection inside the candidate loop.
- Dedup bootstrap now normalizes missing semantic signature fields on existing stable records once per run so in-memory scoring and vector recall stay consistent.
- Added Phase 4 regression coverage for incremental vector-memory sync, stable-id overwrite behavior, and startup normalization of legacy stable records.
