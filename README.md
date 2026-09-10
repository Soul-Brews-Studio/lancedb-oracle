# Learn LanceDB, one throw at a time

Small runnable lessons on [LanceDB](https://lancedb.com), the embedded vector database.
Each lesson is a notebook you can run in the browser — no install — or locally with `uv`.

Every lesson runs code first, then looks at what it left on disk. Lance is a directory
format before it is a database; once you can read the fragments and manifests, the
rest (versioning, indexes, compaction) stops being magic.

Code and comments are in English; the explanation cells between them are in Thai
(อธิบายเป็นภาษาไทย โค้ดเป็นอังกฤษ). Lessons 1–6 use 3-dimension vectors and 5 rows so
every number can be checked by hand. From lesson 7 on, the data is
[11 of Nat's own posts](lessons/data/README.md) — real Thai text, same rows in every lesson.

## Part 1 — the database

| # | Notebook | What you learn | Open |
|---|---|---|---|
| 1 | [first table](lessons/01-first-table/first_table.ipynb) | table = directory; one write = one txn + one manifest + one fragment | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/01-first-table/first_table.ipynb) |
| 2 | [vectors](lessons/02-vectors/vectors.ipynb) | `fixed_size_list<float>` column, `search()`, `_distance`, L2 vs cosine | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/02-vectors/vectors.ipynb) |
| 3 | [ORM style](lessons/03-orm/orm.ipynb) | Pydantic `LanceModel`, `Vector(n)`, objects in and out, validation before disk | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/03-orm/orm.ipynb) |
| 4 | [CRUD](lessons/04-crud/crud.ipynb) | `update`, `delete`, `merge_insert` upsert; `_deletions/` on disk | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/04-crud/crud.ipynb) |
| 5 | [query & join](lessons/05-query-join/query_join.ipynb) | `where` / `select` / `limit`; no JOIN in Lance — pandas merge and DuckDB over Arrow | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/05-query-join/query_join.ipynb) |
| 6 | [migration](lessons/06-migration/migration.ipynb) | `add_columns`, `alter_columns`, `drop_columns`; why int→float cast fails; `checkout` + `restore` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/06-migration/migration.ipynb) |

## Part 2 — search

| # | Notebook | What you learn | Open |
|---|---|---|---|
| 7 | [real embeddings](lessons/07-embeddings/embeddings.ipynb) | `SourceField` / `VectorField` auto-embed; hand vectors vs MiniLM neighbor by neighbor; PCA plot | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/07-embeddings/embeddings.ipynb) |
| 8 | [full-text search](lessons/08-fts/fts.ipynb) | `create_index(col, config=FTS(...))`, BM25 `_score`; Thai needs the `icu` tokenizer | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/08-fts/fts.ipynb) |
| 9 | [hybrid search](lessons/09-hybrid/hybrid.ipynb) | `query_type="hybrid"` + `RRFReranker`; vector, FTS, hybrid side by side; RRF by hand | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/09-hybrid/hybrid.ipynb) |
| 10 | [compaction](lessons/10-compaction/compaction.ipynb) | ten writes → nine fragments; `compact_files` then `cleanup_old_versions` (both → `optimize()`); index staleness | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/10-compaction/compaction.ipynb) |
| 11 | [IVF_PQ index](lessons/11-ivf-pq/ivf_pq.ipynb) | 50k vectors; `create_index("vector", config=IvfPq(...))`; recall vs `nprobes` and `refine_factor` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/11-ivf-pq/ivf_pq.ipynb) |
| 12 | [Python vs TypeScript](lessons/12-typescript/typescript.ipynb) | same directory opened by `@lancedb/lancedb` from bun; API names side by side | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/12-typescript/typescript.ipynb) |

## Part 3 — agent memory

| # | Notebook | What you learn | Open |
|---|---|---|---|
| 13 | [multi-table memory](lessons/13-multi-table-memory/multi_table_memory.ipynb) | episodic / semantic / procedural tables; one vector into all three; DuckDB join skill → fact → event | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/13-multi-table-memory/multi_table_memory.ipynb) |
| 14 | [prefilter vs postfilter](lessons/14-prefilter-postfilter/prefilter_postfilter.ipynb) | `where(..., prefilter=True\|False)`; postfilter returns nothing when top-k misses the filter | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/14-prefilter-postfilter/prefilter_postfilter.ipynb) |
| 15 | [scalar indexes](lessons/15-scalar-index/scalar_index.ipynb) | `create_index(col, config=Bitmap()\|BTree())`; `explain_plan()` before and after | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/15-scalar-index/scalar_index.ipynb) |
| 16 | [chunking](lessons/16-chunking/chunking.ipynb) | 40-char chunks with 10-char overlap on Thai; `parent_id`; retrieve the chunk, show the parent | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/16-chunking/chunking.ipynb) |
| 17 | [retention](lessons/17-retention/retention.ipynb) | `delete` hides, `optimize(cleanup_older_than=...)` destroys; `checkout(1)` before and after | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/17-retention/retention.ipynb) |
| 18 | [concurrent writers](lessons/18-concurrent-writers/concurrent_writers.ipynb) | two processes × 20 `merge_insert` on one table; no lost writes; one manifest per commit | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/18-concurrent-writers/concurrent_writers.ipynb) |
| 19 | [DuckDB & Polars](lessons/19-duckdb-polars/duckdb_polars.ipynb) | `to_polars()`, DuckDB over Arrow, `pylance` reading the directory with no lancedb import | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/19-duckdb-polars/duckdb_polars.ipynb) |
| 20 | [object store](lessons/20-object-store/object_store.ipynb) | same code on local dir and S3 (moto); `storage_options` keys; Cloud tradeoffs | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/20-object-store/object_store.ipynb) |

## API drift caught by running (lancedb 0.38.0)

| Deprecated | Since | Use instead | Lesson |
|---|---|---|---|
| `create_fts_index(...)` | 0.25 | `create_index(col, config=FTS(...))` | 8 |
| `create_scalar_index(col, index_type=...)` | 0.25 | `create_index(col, config=BTree()\|Bitmap())` | 15 |
| `compact_files()`, `cleanup_old_versions()` | 0.21 | `optimize(cleanup_older_than=..., delete_unverified=...)` | 10, 17 |
| `alter_columns(data_type=...)` int→float | — | refused; `add_columns(CAST)` → `drop_columns` → rename | 6 |

## Run locally

```sh
cd lessons
just setup      # uv sync + register Jupyter kernel
just run 1      # execute lesson 1, print every cell's output
just all        # every lesson in order
just lab        # JupyterLab on http://localhost:8888
just tree 4     # see what lesson 4 wrote to disk
```

The `.py` files are the source; notebooks are generated from them with
[jupytext](https://jupytext.readthedocs.io) (`just nb`). Edit the `.py`, not the `.ipynb`.
Lesson 12 also needs [bun](https://bun.sh); lesson 7 and 9 download a 470 MB multilingual model on first run.

## Tools

`tools/fbx/` — a small YAML-declared engine that loads a Facebook data export zip into
LanceDB tables and queries them with DuckDB SQL. Built while looking for lesson data;
documented in [`tools/fbx/fbx.yml`](tools/fbx/fbx.yml).

## About

This repo is the home of **Lance Oracle**, an AI-assisted learning notebook kept by
[Nat](https://github.com/nazt). Lessons are written and run with Claude; the `ψ/` directory
is the oracle's memory (plans, retrospectives, handoffs) and is not part of the course.

License: MIT.
