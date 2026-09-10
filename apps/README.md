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
| node | `@lancedb/lancedb` | 0.27.2 (fleet pin) | planned |
| python | `lancedb` | 0.38.0 | planned |
| rust | `lancedb` crate | — | planned |

Every runtime writes the same directory layout; any of them can open a table the other wrote.
