# apps — the same tiny app in every runtime

One script per runtime, identical behaviour, so the APIs can be diffed side by side:

1. connect to `./data`
2. create `posts` from `lessons/data/nat_posts.jsonl` (11 rows, 3-dim hand vectors)
3. `mergeInsert("id")` — update p11, insert p12
4. vector search nearest to `[1, 0, 0]`, then the same with `where topic = 'hardware'`
5. print fragments / manifests / txn / bytes on disk

| runtime | package | version | run |
|---|---|---|---|
| [bun](bun/) | `@lancedb/lancedb` | 0.38.0 | `cd apps/bun && bun install && bun start` |
| [node](node/) | `@lancedb/lancedb` | 0.27.2 (fleet pin) | `cd apps/node && npm install && npm start` |
| [python](python/) | `lancedb` | 0.38.0 | `cd apps/python && uv sync && uv run main.py` |
| rust | `lancedb` crate | — | planned |

Every runtime writes the same directory layout; any of them can open a table the other wrote.

## Measured: 0.27.2 vs 0.38.0 (2026-09-10)

- `apps/bun/index.ts` and `apps/node/index.mjs` are the same code minus `Bun.file` → `readFileSync`. Zero API changes were needed for `connect`, `createTable`, `mergeInsert`, `vectorSearch`, `where`, `countRows`, `version`.
- Cross-version reads both ways: 0.38 opens the 0.27.2 table and 0.27.2 opens the 0.38 table — 12 rows, version 2, nearest `p02` in both.
- On disk, 0.38 writes `_versions/latest_version_hint.json`; 0.27.2 does not (same absence lesson 20 saw on S3). Manifests are a few bytes different (694/732 vs 799/845); fragments within 2%.
- Python 0.38.0 and bun 0.38.0 write byte-identical directories (9412 bytes). Method names differ only in case: `merge_insert` / `mergeInsert`, `when_matched_update_all` / `whenMatchedUpdateAll`, `search(q)` / `vectorSearch(q)`, `to_pandas()` / `toArray()`. Python is sync; TS is `await` everywhere.
- The Python-side deprecations the lessons hit (`create_fts_index`, `create_scalar_index`, `compact_files`/`cleanup_old_versions`) are not exercised by this app — the next step is to add an FTS index to both and see whether 0.27.2's TS API differs there.
