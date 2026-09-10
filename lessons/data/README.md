# Lesson data

`nat_posts.jsonl` — 11 of Nat's own public Facebook posts (2026-05 to 2026-08), his words
only, no other people named. Each row has a `topic` and a hand-made 3-dim `vector` whose
axes mean `[memory, agents, hardware]`, so every distance in a lesson can be checked by hand.
Real embeddings replace these vectors in lesson 7.

Lessons load it with:

```python
from lesson_data import load
rows = load("nat_posts.jsonl")   # local file, or fetched from GitHub when running in Colab
```
