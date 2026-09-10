# Learn LanceDB, one throw at a time

Small runnable lessons on [LanceDB](https://lancedb.com), the embedded vector database.
Each lesson is a notebook you can run in the browser — no install — or locally with `uv`.

Every lesson runs code first, then looks at what it left on disk. Lance is a directory
format before it is a database; once you can read the fragments and manifests, the
rest (versioning, indexes, compaction) stops being magic.

## Lessons

| # | Notebook | What you learn | Open |
|---|---|---|---|
| 1 | [first table](lessons/01-basics/lesson1_first_table.ipynb) | table = directory; one write = one txn + one manifest + one fragment | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/01-basics/lesson1_first_table.ipynb) |
| 2 | [vectors](lessons/01-basics/lesson2_vectors.ipynb) | `fixed_size_list<float>` column, `search()`, `_distance`, L2 vs cosine | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Soul-Brews-Studio/lancedb-oracle/blob/main/lessons/01-basics/lesson2_vectors.ipynb) |

More coming: filters and hybrid search, IVF_PQ index, versions and compaction, TypeScript side by side.

## Run locally

```sh
cd lessons/01-basics
just setup      # uv sync + register Jupyter kernel
just run 1      # execute lesson 1, print every cell's output
just lab        # JupyterLab on http://localhost:8888
just tree       # see what the lesson wrote to disk
```

The `.py` files are the source; notebooks are generated from them with
[jupytext](https://jupytext.readthedocs.io) (`just nb`). Edit the `.py`, not the `.ipynb`.

## About

This repo is the home of **Lance Oracle**, an AI-assisted learning notebook kept by
[Nat](https://github.com/nazt). Lessons are written and run with Claude; the `ψ/` directory
is the oracle's memory (plans, retrospectives, handoffs) and is not part of the course.

License: MIT.
