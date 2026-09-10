# TODO — Lance Oracle

Index first. Full plan with sources and methods: `ψ/writing/lesson-plan.md`.

- [ ] U4 `lessons/04-index` — create IVF_PQ index on 100k vectors; measure brute-force vs indexed latency and recall; look at `_indices/` on disk
- [ ] U2 `lessons/02-vectors` — vector column, `search(vec)`, `_distance`; needed to read U4 output
- [ ] U3 `lessons/03-filters-hybrid` — prefilter vs postfilter recall, FTS index, hybrid
- [ ] R1 — source map: `lancedb/lancedb` vs `lancedb/lance`, which layer owns what
- [ ] R2 — version archaeology 0.26 → 0.38; breaking changes per fleet repo
- [ ] U5 `lessons/05-versions` — checkout, restore, compaction, disk size
- [ ] R4 — fleet usage patterns: lance-indexer, session-dream, jsonl-oracle, arra-v5, omx-grokbot
- [ ] R3 — read manifest format from `lance` protos; confirm `u64::MAX - version` naming
- [ ] R5 — read nexus-oracle `search-bench/eval/*.json`, rerun one target, write the number
- [ ] R6 — correct digger: search-bench results exist; handoff to digger inbox
- [ ] Post `ψ/outbox/awaken_2026-09-10_fast.md` to arra-oracle-v3 as issue (Nat said later)
- [ ] `/awaken --soul-sync`

## Done
- [x] U1 `lessons/01-lancedb-basics` — table, fragments, manifests (2026-09-10)
- [x] `/awaken --fast` — identity, soul, philosophy (2026-09-10)
