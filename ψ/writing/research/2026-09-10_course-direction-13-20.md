# Course direction: lessons 13-20 (agent memory)

**Question**: lessons 1-6 cover disk format, vectors, ORM, CRUD, query+join, migration.
TODO.md already plans 7-12 (real embeddings, FTS, hybrid, compaction, IVF_PQ, Python-vs-TS).
None of the twelve teach the shape the fleet actually needs: LanceDB as the memory
store behind agents reading an 835 MB session-transcript table and MCP memory
servers on `@lancedb/lancedb`. What comes next to close that gap?

**Method**: read lessons 1-6 and TODO.md for style and scale (Thai explanation /
English code, `# %%` cells, single-digit rows, 3-dim vectors, grow data only when
a concept demands it — IVF_PQ is the one exception already planned). Verified every
API name below against docs.lancedb.com and the lancedb/lancedb GitHub repo (search
+ fetch, listed in Sources) rather than recalling from training data — TODO.md's own
rule ("Never promise `IVF_HNSW_FLAT`") is a reminder that guessed API names are wrong
often enough to matter here.

## Ranking

Ordered by what it unlocks for an agent-memory system, not by difficulty. Multi-table
design has to come first — every later lesson (filtering, indexing, retention) needs
tables shaped like real memory before it means anything. Storage backend comes last:
it's a deployment choice, not a concept the others depend on.

## L13 — Multi-table memory: episodic / semantic / procedural

**Concept**: one Lance table per memory kind, joined at query time — the same
pattern L5 used for `users`/`orders`, now applied to memory instead of e-commerce.
**Dataset**: three tables, 4-5 rows each, 3-dim vectors — `episodic` (session_id, ts,
text, vector), `semantic` (fact_id, text, vector), `procedural` (skill_id, steps,
vector).
**Look at**: three `.lance` directories side by side on disk; a DuckDB query
(`duckdb.sql` on the three `.to_arrow()` results, exactly L5's pattern) joining an
episodic row to the semantic facts it produced.
**API**: `db.create_table()` ×3, `table.search().where(...)`, `.to_arrow()`.

## L14 — Metadata filter + vector search: prefilter vs postfilter

**Concept**: `where()` takes a `prefilter` argument. Prefilter narrows the candidate
set *before* the vector search runs; postfilter (`prefilter=False`) runs the vector
search first and filters the top-k after — so a real match can be filtered out of a
small `k` before the metadata condition ever sees it. This is lesson-plan.md's U3
recall question, now answerable with a verified argument name instead of "which
loses results?"
**Dataset**: 5 rows, 3-dim vectors, one `agent` metadata column; pick a query vector
and `limit` small enough that pre/post filtering visibly return different rows.
**Look at**: two `.to_pandas()` outputs, same query and `where`, only `prefilter`
flipped — different row counts.
**API**: `table.search(vector).where("agent = 'X'", prefilter=True|False).limit(n)`.

## L15 — Scalar indexes: BTREE / BITMAP on metadata columns

**Concept**: `create_scalar_index` speeds up the metadata half of the query above.
BTREE for high-cardinality columns (timestamps, ids), BITMAP for low-cardinality
ones (agent name, memory type) — default is BTREE if `index_type` is omitted.
**Dataset**: reuse L13/L14's table, ~10-20 rows so an index is created at all.
**Look at**: an `_indices/` directory appears on disk after `create_scalar_index`;
compare with an index that wasn't there in L1-L14.
**API**: `table.create_scalar_index("agent", index_type="BITMAP")`,
`table.create_scalar_index("created_at")` (BTREE default).

## L16 — Chunking transcripts before embedding

**Concept**: a transcript is one long string; a memory row is a chunk. Chunk size
and overlap are a design choice made in Python before anything touches LanceDB —
this lesson is deliberately not a new API surface, it's showing that the join
between chunks (`parent_id`) is the same foreign-key-less pattern from L5.
**Dataset**: one ~500-character fake transcript, chunked into 3 overlapping pieces
by hand (character slicing, not a library — keeps it checkable by hand per the
course rule).
**Look at**: a printed table of chunks showing the overlapping characters
duplicated between chunk *n* and *n+1*; reassembling via
`table.search().where("parent_id = X").to_pandas()` sorted by `chunk_index`.
**API**: plain `table.add(rows)`; no new LanceDB call, the concept is the design,
not the syntax.

## L17 — Time-based queries and retention

**Concept**: `where()` on a timestamp column for "what happened this week", then
physically reclaiming space for what should be forgotten: `delete()` marks rows
gone, `compact_files()` rewrites fragments without them, `cleanup_old_versions()`
removes the old manifests so deleted data is actually gone from disk, not just
unreferenced.
**Dataset**: 5-8 rows with `created_at` spanning a fake week (`datetime` literals);
delete rows older than a cutoff.
**Look at**: file/version count before and after `compact_files()` +
`cleanup_old_versions()` — same check the course already runs in L1 and the planned
L10, applied to a retention policy instead of raw compaction.
**API**: `table.delete("created_at < timestamp '2026-09-05'")`,
`table.compact_files()`, `table.cleanup_old_versions()` (accepts an `older_than`
duration and a `delete_unverified` flag per docs.lancedb.com/tables/versioning and
lancedb/lancedb#2470/#3125 — `delete_unverified=True` is explicitly documented as
unsafe unless no other process touches the table, which sets up L18).

## L18 — Concurrent writers: what breaks

**Concept**: the fleet's real failure mode — multiple oracle agents writing memory
at once. Concurrent `add()`/append is fine at high concurrency. Concurrent
`update`/`delete`/`merge_insert` frequently conflict: LanceDB uses optimistic
concurrency, retries a bounded number of times, then raises (observed error text:
"Commit conflict for version N: Failed to commit the transaction after 20
retries", lancedb/lancedb#2426).
**Dataset**: the L17 table; two Python processes (`multiprocessing` or two
`subprocess` calls) both run `merge_insert` against overlapping keys at the same
moment.
**Look at**: one process's exception text on screen; `table.list_versions()`
afterward showing only one write landed, or both landed serialized — the honest
answer, measured, not assumed.
**API**: `table.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(rows)`.

## L19 — Reading a Lance table from DuckDB and Polars directly

**Concept**: memory doesn't have to be read back through `lancedb`'s Python client
at all — DuckDB's `lance` extension attaches the table directory as SQL, and Polars
reads the same table as a lazy frame. Useful for oracle debugging/ad-hoc analysis
without spinning up the whole MCP server.
**Dataset**: L13's `episodic` table on disk, untouched.
**Look at**: the same row count and same top row, produced three ways — LanceDB
Python `.to_pandas()`, DuckDB SQL, Polars `.collect()` — a cross-tool proof rather
than a claim.
**API**: DuckDB — `INSTALL lance; LOAD lance; ATTACH './data/lesson19' AS ns (TYPE
LANCE); SELECT * FROM ns.main.episodic LIMIT 5;`. Polars —
`table.to_polars().collect()` (returns a `LazyFrame`; `.collect()` materializes it).

## L20 — Object store backend and LanceDB Cloud tradeoffs

**Concept**: identical `create_table`/`search` code, three backends — local disk,
S3-compatible object store, LanceDB Cloud — with different tradeoffs for the
fleet's concurrent-writer problem from L18 (S3 needs external locking or accepts
conflicts; Cloud manages that server-side).
**Dataset**: the same 5-row table from L1, connected three ways; S3 leg can run
against a local MinIO container (`storage_options={"endpoint": "http://localhost:9000",
"allow_http": "true", ...}`) so it's runnable without real AWS credentials.
**Look at**: one comparison table (who owns conflict resolution, who pays for
compute, cold-start latency) written from what actually happened in the run, not
from the docs alone.
**API**: `lancedb.connect("./data")`; `lancedb.connect("s3://bucket/path",
storage_options={"aws_access_key_id": ..., "aws_region": ...})`;
`lancedb.connect(uri="db://project-slug", api_key=..., region="us-east-1")`.

## Notes on confidence

Every method name above (`create_scalar_index`, `merge_insert` +
`when_matched_update_all`/`when_not_matched_insert_all`, `prefilter`,
`storage_options`, `db://` + `api_key`/`region`, `to_polars`, the DuckDB `lance`
extension's `ATTACH ... TYPE LANCE`) was confirmed against docs.lancedb.com or
lancedb/lancedb GitHub in this session — not recalled. `cleanup_old_versions`'s
exact parameter list (`older_than`, `delete_unverified`) is corroborated by the
docs' versioning page plus two GitHub issues discussing its danger, but I did not
find its literal signature in the API reference; L17's script should print
`help(table.cleanup_old_versions)` first and treat that as the ground truth, same
discipline as L6's "read the error, don't guess" moment.

## Sources

- https://docs.lancedb.com/indexing/scalar-index
- https://docs.lancedb.com/search/filtering
- https://lancedb.com/docs/tables/update/
- https://docs.lancedb.com/storage/configuration
- https://docs.lancedb.com/tables/versioning
- https://docs.lancedb.com/integrations/data/duckdb
- https://github.com/lancedb/lancedb/blob/main/docs/src/python/polars_arrow.md
- https://github.com/lancedb/lancedb/issues/2426
- https://github.com/lancedb/lancedb/issues/2470
- https://github.com/lancedb/lancedb/issues/3125
- https://github.com/lancedb/lancedb/issues/1597
- https://github.com/lancedb/lancedb/issues/3095
- https://lancedb.github.io/lancedb/python/python/
