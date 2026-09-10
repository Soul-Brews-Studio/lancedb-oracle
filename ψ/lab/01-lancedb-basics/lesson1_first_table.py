# %% [markdown]
# # Lesson 1 — first table
# A Lance table is a directory. No server. One write = one `.txn` + one `.manifest` + one data fragment.

# %%
import lancedb

# "connect" = pick a directory. No server, no socket. Just a folder.
db = lancedb.connect("./data/lesson1")

# %%
# Create table from plain dicts. Schema inferred (Arrow types).
rows = [
    {"id": 1, "repo": "lance-indexer", "lang": "ts", "stars": 3},
    {"id": 2, "repo": "session-dream", "lang": "ts", "stars": 7},
    {"id": 3, "repo": "arra-memory-py", "lang": "py", "stars": 1},
]
tbl = db.create_table("repos", data=rows, mode="overwrite")
tbl.schema

# %%
tbl.to_pandas()

# %%
# Filter = SQL-ish where clause, pushed down to the file scan.
tbl.search().where("lang = 'ts'").to_pandas()

# %%
# Append. Lance writes a NEW fragment, never rewrites old ones.
tbl.add([{"id": 4, "repo": "lanceglass", "lang": "ts", "stars": 2}])
print("count:", tbl.count_rows(), "| version:", tbl.version)

# %%
# Look at the disk: 2 txn, 2 manifests, 2 fragments.
# !find data/lesson1 -type f | sort
