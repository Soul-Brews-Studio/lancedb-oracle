# Learn LanceDB, one throw at a time

Small runnable lessons on [LanceDB](https://lancedb.com), the embedded vector database.
Each lesson is a notebook you can run in the browser — no install — or locally with `uv`.

Every lesson runs code first, then looks at what it left on disk. Lance is a directory
format before it is a database; once you can read the fragments and manifests, the
rest (versioning, indexes, compaction) stops being magic.

## Lessons

| # | Notebook | What you learn | Open |
|---|---|---|---|
| 1 | [first table](lessons/01-first-table/first_table.ipynb) | table = directory; one write = one txn + one manifest + one fragment | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/01-first-table/first_table.ipynb) |
| 2 | [vectors](lessons/02-vectors/vectors.ipynb) | `fixed_size_list<float>` column, `search()`, `_distance`, L2 vs cosine | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/02-vectors/vectors.ipynb) |
| 3 | [ORM style](lessons/03-orm/orm.ipynb) | Pydantic `LanceModel`, `Vector(n)`, objects in and out, validation before disk | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/03-orm/orm.ipynb) |
| 4 | [CRUD](lessons/04-crud/crud.ipynb) | `update`, `delete`, `merge_insert` upsert; `_deletions/` on disk | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/04-crud/crud.ipynb) |
| 5 | [query & join](lessons/05-query-join/query_join.ipynb) | `where` / `select` / `limit`; no JOIN in Lance — pandas merge and DuckDB over Arrow | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/05-query-join/query_join.ipynb) |
| 6 | [migration](lessons/06-migration/migration.ipynb) | `add_columns`, `alter_columns`, `drop_columns`; why int→float cast fails; `checkout` + `restore` | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/06-migration/migration.ipynb) |
| 7 | [real embeddings](lessons/07-embeddings/embeddings.ipynb) | `SourceField` / `VectorField` auto-embed; hand vectors vs model, neighbor by neighbor; query by text | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/07-embeddings/embeddings.ipynb) |
| 13 | [multi-table memory](lessons/13-multi-table-memory/multi_table_memory.ipynb) | episodic / semantic / procedural tables; same vector into all three; DuckDB join skill → fact → event | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/13-multi-table-memory/multi_table_memory.ipynb) |
| 14 | [prefilter vs postfilter](lessons/14-prefilter-postfilter/prefilter_postfilter.ipynb) | `where(..., prefilter=True\|False)` with vector search; postfilter can return nothing when top-k misses the filter | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/14-prefilter-postfilter/prefilter_postfilter.ipynb) |

Lessons 8–12 (FTS, hybrid, compaction, IVF_PQ, TypeScript) are planned and will fill the gap.
From lesson 7 on, the data is [11 of Nat's own posts](lessons/data/README.md) — real Thai text, same rows in every lesson.

Code and comments are in English; the explanation cells between them are in Thai
(อธิบายเป็นภาษาไทย โค้ดเป็นอังกฤษ). Small tables — 3 dimensions, 5 rows — so every
number can be checked by hand.

More coming: filters and hybrid search, IVF_PQ index, versions and compaction, TypeScript side by side.

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

## About

This repo is the home of **Lance Oracle**, an AI-assisted learning notebook kept by
[Nat](https://github.com/nazt). Lessons are written and run with Claude; the `ψ/` directory
is the oracle's memory (plans, retrospectives, handoffs) and is not part of the course.

License: MIT.
