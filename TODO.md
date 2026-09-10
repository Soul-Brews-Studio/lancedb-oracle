# TODO — Lance Oracle

Index first. Full plan with sources and methods: `ψ/writing/lesson-plan.md`.

- [ ] L7 real embeddings — `get_registry().get("sentence-transformers")`, `SourceField`/`VectorField`, 5 sentences
- [ ] L8 full-text search — `create_fts_index`, `query_type="fts"`, `_score`, index dir on disk
- [ ] L9 hybrid — `query_type="hybrid"`, `RRFReranker`, `_relevance_score`
- [ ] L10 compaction + cleanup — `compact_files()` then `cleanup_old_versions()`; fragment count before/after
- [ ] L11 IVF_PQ — 5–10k random vectors, `create_index`, latency before/after (first lesson that grows)
- [ ] L12 Python vs TypeScript — open one table from both bindings
- [ ] `apps/` demo — same tiny app in python / node (0.27.2, fleet pin) / bun (0.38) / rust; diff the APIs
- [ ] Never promise `IVF_HNSW_FLAT` in Python — not in SDK (lancedb#3331)
- [ ] R1 — source map: `lancedb/lancedb` vs `lancedb/lance`, which layer owns what
- [ ] R2 — version archaeology 0.26 → 0.38; breaking changes per fleet repo
- [ ] R4 — fleet usage patterns: lance-indexer, session-dream, jsonl-oracle, arra-v5, omx-grokbot
- [ ] R3 — read manifest format from `lance` protos; confirm `u64::MAX - version` naming
- [ ] R5 — read nexus-oracle `search-bench/eval/*.json`, rerun one target, write the number
- [ ] R6 — correct digger: search-bench results exist; handoff to digger inbox
- [ ] Post `ψ/outbox/awaken_2026-09-10_fast.md` to arra-oracle-v3 as issue (Nat said later)
- [ ] `/awaken --soul-sync`

## Done
- [x] L1–L6 `lessons/01-basics` — table, vectors, ORM, CRUD, query+join, migration (2026-09-10)
- [x] Repo public, Colab badges, MIT (2026-09-10)
- [x] `/awaken --fast` — identity, soul, philosophy (2026-09-10)
