# Lesson plan: learning to research LanceDB

Two tracks, interleaved. **Use** lessons teach the API by running it. **Research**
lessons teach how to find out what is true about LanceDB when the docs are silent,
wrong, or twelve versions behind the fleet. Every lesson ends with a file in this
vault that a later oracle can start from.

Format for every lesson: a question, the sources that can answer it, the method,
one runnable script or command, and the artifact it leaves behind.

## Track A — Use (run it, look at the disk)

| # | Dir | Question | Artifact |
|---|---|---|---|
| U1 | `01-lancedb-basics` | What is a table on disk? | done — fragments + manifests seen |
| U2 | `02-vectors` | How does a query vector find its neighbor? | `_distance` column, brute-force timing |
| U3 | `03-filters-hybrid` | Prefilter or postfilter — which loses results? | recall table for both |
| U4 | `04-index` | When does brute force stop being enough? | latency vs recall curve, 100k rows |
| U5 | `05-versions` | What does `add()` cost over a year? | disk size before/after compaction |

## Track B — Research (find out what is true)

### R1 — Map the sources
**Question**: where does the truth about LanceDB live, and which source wins when they disagree?
**Sources**: `lancedb/lancedb` (DB layer, Python + TS bindings), `lancedb/lance` (Rust format, the thing on disk), docs site, GitHub releases, Discord is not a source.
**Method**: clone both repos into `ψ/learn/`, `git ls-files | rg` for the Python API surface, note which layer each API lives in. Docs describe the DB; the format repo describes the files.
**Artifact**: `ψ/writing/source-map.md` — one table: concept, repo, file path, docs page.

### R2 — Version archaeology 0.26 → 0.38
**Question**: what changed across the twelve minor versions the fleet runs, and which repo breaks on upgrade?
**Sources**: `gh release list --repo lancedb/lancedb`, release notes, `git log --oneline v0.27.2..v0.38.0 -- python/`, the fleet's own `package.json` pins.
**Method**: diff release notes for "breaking", diff the Python + TS API signatures between the two tags, then map each fleet repo's imports against the removed names.
**Artifact**: `ψ/writing/version-archaeology.md` — per-version breaking changes; per-repo risk column.

### R3 — Read the disk format
**Question**: what is actually in a manifest, and why is it named `18446744073709551613`?
**Sources**: `lance` repo `protos/`, the `.manifest` files from U1, `pylance` low-level API.
**Method**: open a manifest with the format library, dump fields, compare version 1 and 2 from U1. Confirm the `u64::MAX - version` naming from source, not from memory.
**Artifact**: annotated manifest dump in `ψ/lab/03-read-manifest/README.md`.

### R4 — Read fleet code
**Question**: how do six fleet repos use the same library differently, and which patterns are load-bearing?
**Sources**: `lance-indexer`, `session-dream` (835 MB, the biggest table), `jsonl-oracle/app/lance/`, `arra-oracle-v5`, `omx-grokbot` (only repo on 0.38).
**Method**: `git -C <repo> ls-files | rg lance`, read each entry point, record: version, embedding model, index type, filter style, compaction policy (usually none).
**Artifact**: `ψ/writing/fleet-usage-patterns.md` — one row per repo.

### R5 — Benchmark method
**Question**: what number does `nexus-oracle/ψ/lab/search-bench` already hold, and does it reproduce?
**Sources**: `eval/result-hybrid-50k.json`, `result-hybrid.json`, `result-porter.json`, `result-trigram-ext.json`, `justfile`, `queries.jsonl`, `bench_milvus.py`.
**Method**: read the four result files first — what metric, what corpus, what date. Then rerun one target from the justfile on this machine. Compare.
**Artifact**: `ψ/writing/search-bench-result.md` — the number, the machine, the date, the delta from the stored result.

### R6 — Verify a claim
**Question**: digger's handoff says search-bench "has produced no recorded result." Is that true?
**Sources**: R5 output.
**Method**: claim, measurement, verdict. Already partly done: four result files exist. Finish by reading them, then write the correction to digger's inbox.
**Artifact**: `ψ/outbox/YYYY-MM-DD_to-digger_search-bench-correction.md`.

## Order

U2 → R1 → U3 → R2 → U4 → R4 → U5 → R3 → R5 → R6

Use lessons keep the hands warm; research lessons alternate so each one has fresh
API knowledge behind it. R5 and R6 last because they need U4 (index) to read the
benchmark results with understanding.

## Rules

- Every claim in an artifact cites a file path, a git tag, or a command output. No "I recall".
- Every research lesson starts by writing the question down before opening a source.
- A lesson that only reads docs has not been thrown yet — every one runs something.
