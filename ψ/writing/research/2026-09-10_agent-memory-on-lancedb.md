---
title: Agent memory on LanceDB — intensive survey
date: 2026-09-10
author: lancedb-oracle
kind: research
---

# Agent memory on LanceDB

Context: the fleet already has LanceDB-backed memory in production shape —
a 835 MB session-transcript table (`session-dream`, one of six indexers over
the same `~/.claude/projects` corpus), MCP `remember`/`recall`/`forget`
servers, and two `arra-memory` forks that traded Cloudflare Workers
deployment for LanceDB's native module. See
`ψ/inbox/handoff/2026-09-10_digger-lancedb-fleet-survey.md`. This note asks:
how does the wider world build LLM-agent memory on LanceDB, and what should
an oracle-fleet schema look like.

## 1. Memory architectures and where they map onto LanceDB tables

The 2026 agent-memory literature converges on a small set of memory *kinds*,
each with a natural table shape:

- **Episodic memory** — "what happened, when, with whom, with what
  outcome." A time-series log: append-only rows, one per event/turn/tool
  call. Retrieved by full-text + vector + time-range filter together.
- **Semantic memory** — facts and entities extracted from episodes, often
  with temporal validity bounds ("this was true from t0 to t1"). This is
  the layer **Zep/Graphiti** builds as a knowledge graph rather than a flat
  table — LanceDB has no native graph layer, so a semantic-memory table on
  LanceDB is usually a *fact* row (subject, predicate, object, confidence,
  valid_from, valid_to, source_episode_id) rather than a graph traversal
  structure. **Cognee** takes the ECL (Extract-Cognify-Load) approach:
  episodes get processed into a graph *and* a vector index side by side —
  LanceDB would sit at the "Load" vector-index end of that pipeline, not
  replace the graph.
- **Procedural memory** — learned skills/routines, closer to versioned
  documents (a `skills` table with content + version) than to vector
  search; LanceDB is a reasonable store but adds little over files.
- **Working memory** — the current context window, not persisted, or
  persisted as a short-lived high-recency table (the "constant 10-message
  window" in the dual-process architectures found in the search).

**MemGPT/Letta**'s core idea — the agent manages its own paging between
"core" (always-in-context) memory and "archival" (searchable, out-of-context)
memory — maps cleanly onto two LanceDB tables of different retention: a tiny
`core_memory` table read in full every turn, and a large `archival_memory`
table that only the agent's own `recall` tool queries. **mem0** layers a
vector store for semantic retrieval plus an optional graph layer for
entity-level memory; mem0 does not yet support LanceDB natively as a vector
backend (open feature request, see Sources) — today the only path in is via
mem0's generic LangChain vector-store adapter, which forces the LanceDB
collection to be named `mem0`. **LangMem** runs a background "manager" that
periodically extracts and consolidates memories from conversation — this is
an argument for LanceDB's `merge_insert` (§2) as the consolidation
primitive, since consolidation is fundamentally an upsert-by-key operation.

**Anthropic's own memory tool** (Claude Managed Agents, shipped this cycle)
deliberately rejects the vector-DB model: memory is a mounted filesystem the
agent edits with its normal file tools, split into a read-only
standards/conventions store and a per-session read-write store, with audit
trails and version history built on the filesystem's own versioning. It is
worth naming as the counter-architecture: no embeddings, no ANN index,
just files plus discipline about what gets written. For a fleet already
running LanceDB (native module, version pinned, indexed), the tradeoff is
recall-by-similarity (LanceDB) vs. recall-by-agent-judgment-of-file-paths
(memory tool) — they are not mutually exclusive; a `core_memory`-style file
store for identity/standards plus a LanceDB `archival_memory` table for
searchable history is a defensible hybrid.

## 2. LanceDB features that matter for memory specifically

- **Versioning as audit log.** Every write (add/update/delete/restore)
  creates a new table version; `list_versions()`, `checkout(version)`,
  `restore(version)`, and git-like `tags` (`table.tags.create(label,
  version)`) give a free audit trail of what an agent believed and when —
  relevant because episodic memory is inherently an audit log. Caveat:
  tagged versions survive cleanup, everything else is prunable, and **100
  versions is not 100 copies of the data but is 100x the manifest metadata
  overhead**, which slows queries if versions are never cleaned
  (`cleanup_old_versions(older_than=...)`).
- **`merge_insert` for dedup/consolidation.** `table.merge_insert("key")
  .when_matched_update_all().when_not_matched_insert_all().execute(new)` is
  the upsert primitive — exactly what a LangMem-style consolidation pass or
  a `remember()` tool with idempotent keys needs. Two sharp edges found in
  open issues: `merge_insert` **silently fails to match** after
  `optimize()` is run on a table with a scalar index on the merge key
  (lancedb#3177), and merge_insert with a pandas frame against a
  pydantic-defined table schema errors on field-mismatch (lancedb#2366).
  Anyone building `remember(id, ...)` as upsert should test the exact
  optimize→merge_insert sequence they intend to run in production.
- **FTS + vector hybrid recall.** `create_fts_index()` on the text column
  plus the existing vector index enables `query_type="hybrid"`
  (Python) or chained `.fullTextSearch().nearestTo()` (TS). Default
  reranker is `RRFReranker()` (reciprocal rank fusion); a
  `LinearCombinationReranker` (0.7 vector / 0.3 FTS by default) is also
  built in, and custom rerankers (Cohere, cross-encoder) subclass
  `Reranker.rerank_hybrid()`. This is the retrieval half of essentially
  every real project surveyed below.
- **Scalar indexes on timestamp/agent-id/tag columns.** BTREE for
  high-cardinality sortable columns (timestamps, UUIDs, agent/session ids —
  supports `<`, `>`, `between`); BITMAP for low-cardinality columns
  (category, tag, memory-type enums). These make `WHERE agent_id = ? AND
  ts > ?` prefilters on a hybrid search cheap instead of a full scan.
  Updating a scalar index after append/delete requires calling
  `optimize()` — it is not automatic — and while a rebuild is in flight,
  queries fall back to brute force on the unindexed tail unless
  `fast_search=True` is set to search only the indexed portion.
  `index_stats()` reports how many rows are still unindexed.
- **Multimodal columns / embedding registry.** `EmbeddingFunctionRegistry`
  lets a table schema declare "this column embeds with model X," and
  LanceDB auto-embeds on insert; `TextEmbeddingFunction` vs. the more
  general `EmbeddingFunction` base class is the text/multimodal split.
  Useful for a fleet where different oracles may want different embedding
  models per memory type without hand-rolling the embed step.
- **`optimize()` for long-running append workloads.** Two distinct jobs
  hide under one call: file compaction (merges small fragments — does
  *not* shrink data, can transiently grow it) and index optimization
  (folds new rows into the existing ANN/scalar index). A memory table that
  appends constantly (every agent turn) needs a periodic `optimize()` or
  index staleness and fragment count both grow unbounded.

## 3. Real projects using LanceDB as agent memory

| Project | What it is | Language | LanceDB ver. | Link |
|---|---|---|---|---|
| **agent-memory-mcp** (adamrdrew) | MCP server, hybrid BM25+vector, RRF fusion, exponential time-decay scoring (30-day half-life, `evergreen`/`never-forget` tags exempt), local ONNX embeddings (Xenova/all-MiniLM-L6-v2) | TypeScript/Node | not pinned in README | github.com/adamrdrew/agent-memory-mcp |
| **memory-lancedb-pro** (CortexReach) | OpenClaw memory plugin — single `memories` table, scope isolation (`global`/`agent:<id>`/`user:<id>`/`project:<id>`), hybrid retrieval → cross-encoder rerank (Jina/SiliconFlow/Voyage/Pinecone) → Weibull lifecycle-decay boost → length norm → hard min-score cutoff | TypeScript | `>=0.26.2`, needs AVX2 for native cosine (AVX-only CPUs fall back to JS cosine) | github.com/CortexReach/memory-lancedb-pro |
| **LanceDB's own Hermes-agent post** | first-party "semantic memory" plugin walkthrough (remember/recall/forget), cites CrewAI's LanceDB integration at "2B+ agent executions" | — | — | lancedb.com/blog/semantic-memory-for-hermes-agent-with-lancedb |
| **official lancedb-mcp-server** | reference MCP server, minimal, meant as a template rather than production memory | — | — | github.com/lancedb/lancedb-mcp-server |
| **mcp-server-lancedb** (kyryl-opens-ml) | basic store/retrieve MCP server | Python | — | github.com/kyryl-opens-ml/mcp-server-lancedb |
| **SimpleMem** (aiming-lab) | "lifelong memory," text+multimodal, dockerized, LanceDB + separate user DB persisted to a host volume | — | — | github.com/aiming-lab/SimpleMem |

**memory-lancedb-pro's schema is the most complete public example found** —
it is close to a direct answer to "what columns does an oracle-memory table
need":

```
id (uuid) · text (FTS) · vector (float[]) · category (enum) ·
scope (string) · importance (float 0-1) · timestamp (int64 ms) ·
metadata (JSON: l0_abstract/l1_overview/l2_content/memory_category/
tier/access_count/confidence/last_accessed_at)
```

Its `scope` column (`global`, `agent:<id>`, `user:<id>`, `project:<id>`)
plus a per-agent access-control map is the direct answer to "how does a
fleet of oracles share one memory store without leaking" — worth copying
verbatim into any fleet-wide table design. It also documents cross-process
file locking (with an optional Redis lock) as the concurrency answer for
multiple agent processes writing the same table — relevant given the fleet
already runs many concurrent oracle sessions.

mem0 does not have a native LanceDB backend (open issue, §5); Zep/Graphiti
and Cognee are graph-first and would use LanceDB only as the vector-index
component of a larger pipeline, not as their primary store.

## 4. Failure modes reported in issues/discussions

- **Concurrent writers.** "Too many concurrent writers" errors on delete,
  specifically after repeated `compact_files()` calls following every
  create/update (lancedb#3086) — the reporter's CRUD pattern (S3+DynamoDB
  backend) triggered it, suggesting write-heavy memory loops that compact
  aggressively are the risk case, not occasional writes.
- **Index staleness after append is by design, not a bug** — LanceDB
  documents that new rows are unindexed until `optimize()` runs, and
  queries brute-force the unindexed tail by default. The actual bug class
  is *silent* staleness: merge_insert silently failing to match rows after
  `optimize()` was run on a scalar-indexed merge key (lancedb#3177) — a
  consolidation pass could think it deduped when it actually inserted
  duplicates.
- **Memory/version growth.** Confirmed both ways: compaction can
  *temporarily increase* disk usage (old fragments stay referenced by
  older still-valid versions until those versions are cleaned), and
  version count itself imposes metadata overhead independent of data size
  — 100 versions is "100x the manifest metadata" even with no duplicated
  rows. For an append-every-turn memory table, an explicit
  `cleanup_old_versions()` cadence is not optional past a certain write
  rate.
- **Embedding dimension changes are destructive by default.** Changing a
  `FixedSizeList` dimension (e.g. 384→1024, switching embedding models) is
  documented as "not a compatible cast" — the sanctioned workaround is
  add-new-column → drop-old-column → rename, i.e. a manual schema
  migration, not an automatic re-embed. OpenClaw's own memory-lancedb
  plugin has an open issue for exactly this: **switching embedding space
  requires a destructive rebuild** (openclaw#19434) — precisely the
  scenario the fleet should expect if an oracle ever swaps embedding
  providers on a live memory table. A second live case: OpenClaw
  configSchema needing an explicit allowlist update to add
  `gemini-embedding-001` as a supported model (openclaw#17650) shows this
  isn't hypothetical — it's an active support burden for LanceDB-memory
  plugin maintainers.
- **Cloudflare/edge incompatibility, confirmed twice independently.**
  lancedb#1056 (open since March 2024, no maintainer resolution as of this
  survey): importing LanceDB's JS package under Next.js `runtime=edge`
  fails with "vectordb is not defined" — reporter explicitly calls it "a
  hard blocker for anyone using CF workers." Separately, openclaw#13409
  shows the *packaging* version of the same root cause outside pure edge
  runtimes: a plugin host that bundles extensions and resolves modules
  from its own dist directory breaks `@lancedb/lancedb`'s
  platform-specific native binary resolution (arm64 vs x86_64) even in a
  normal Node process, with every workaround the reporter tried (local
  node_modules, global install, copying binaries) failing. Two failure
  modes, same underlying fact: **the native module needs a real Node
  process with a resolvable, platform-matched binary — anything that
  virtualizes or bundles that away breaks it.** This directly corroborates
  what digger already found in the fleet's own arra-memory forks
  (dig #227).

## 5. A concrete recommended schema for oracle-fleet memory

Given the fleet already runs many oracle sessions concurrently and needs
cross-oracle-safe isolation plus an audit trail:

```
table: memories
  id            uuid          -- primary key, merge_insert key
  oracle_id     string        -- BITMAP index (low cardinality: ~dozens of oracles)
  scope         string        -- BITMAP index: global | oracle:<id> | project:<id>
  kind          string        -- BITMAP index: episodic | semantic | procedural
  text          string        -- FTS index (create_fts_index)
  vector        float32[d]    -- ANN index; d fixed per embedding_model
  embedding_model string      -- so a dimension change is a filter, not a corruption
  importance    float32       -- 0-1, for decay-weighted ranking
  created_at    int64 (ms)    -- BTREE index
  last_accessed int64 (ms)    -- BTREE index, for decay scoring
  source_session string       -- links back to the JSONL session that produced it
  metadata      json string   -- free-form: confidence, tags, supersedes_id, etc.
```

Design decisions and tradeoffs:

- **One table, not one-per-oracle.** `scope`+`oracle_id` as BITMAP-indexed
  filter columns lets hybrid search prefilter to one oracle's own memories
  cheaply, while still allowing a fleet-wide query (e.g. "what has any
  oracle learned about LanceDB versioning") without a fan-out join across
  N tables. Cost: every write contends on the same table's version
  history — under heavy concurrent multi-oracle writes, watch for
  lancedb#3086-style "too many concurrent writers" if compaction runs
  aggressively; memory-lancedb-pro's cross-process (optionally Redis) lock
  is the mitigation pattern to copy.
- **`embedding_model` as a real column, not an assumption.** Given
  openclaw#19434 and lancedb#1281/#2231 (dimension mismatches are a
  recurring, not rare, failure), storing which model produced each vector
  lets a migration be "re-embed rows where embedding_model != current" run
  incrementally via `merge_insert`, rather than an all-or-nothing
  destructive rebuild.
- **`merge_insert` on `id` for all writes**, including "remember" calls
  that might repeat — makes the remember/recall/forget MCP triad
  idempotent at the storage layer instead of requiring the calling agent
  to dedup in application code. Test the `optimize()` → `merge_insert`
  ordering explicitly given lancedb#3177.
- **Version tags, not raw versions, as the audit interface.** Tag
  significant states (`table.tags.create("2026-09-10-pre-migration",
  version)`) rather than relying on numeric version retention, since
  untagged versions are exactly what `cleanup_old_versions()` is meant to
  prune — and prune it must run on a schedule, or the manifest-overhead
  cost compounds silently (as it already has in `session-dream`'s 835 MB
  table, which nobody has run `optimize()`/cleanup against, per the fleet
  survey).
- **This table lives in a real Node/Python process, never on an edge
  runtime.** Given two independent, unresolved confirmations
  (lancedb#1056, openclaw#13409) that the native module needs a
  platform-matched binary in an unvirtualized module-resolution path, any
  oracle-memory MCP server should assume a persistent local/VM process,
  not a Workers/edge deployment — consistent with digger's dig #227
  finding on the fleet's own arra-memory forks.

## Sources

- https://www.lancedb.com/blog/semantic-memory-for-hermes-agent-with-lancedb
- https://atlan.com/know/best-ai-agent-memory-frameworks-2026/
- https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks
- https://docs.lancedb.com/tables/versioning
- https://docs.lancedb.com/search/hybrid-search
- https://docs.lancedb.com/indexing/scalar-index
- https://lancedb.com/documentation/embeddings/embedding_functions/
- https://lancedb.com/documentation/embeddings/custom_embedding_function/
- https://github.com/adamrdrew/agent-memory-mcp
- https://github.com/CortexReach/memory-lancedb-pro
- https://github.com/lancedb/lancedb-mcp-server
- https://github.com/lancedb/lancedb/issues/1056
- https://github.com/lancedb/lancedb/issues/3086
- https://github.com/lancedb/lancedb/issues/3177
- https://github.com/lancedb/lancedb/issues/2366
- https://github.com/openclaw/openclaw/issues/13409
- https://github.com/openclaw/openclaw/issues/19434
- https://github.com/openclaw/openclaw/issues/17650
- https://github.com/mem0ai/mem0/issues/2212
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- https://claude.com/blog/claude-managed-agents-memory
