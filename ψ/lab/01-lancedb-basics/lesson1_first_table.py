import lancedb

# 1. "connect" = pick a directory. No server, no socket. Just a folder.
db = lancedb.connect("./data/lesson1")

# 2. Create table from plain dicts. Schema inferred (Arrow types).
rows = [
    {"id": 1, "repo": "lance-indexer", "lang": "ts", "stars": 3},
    {"id": 2, "repo": "session-dream", "lang": "ts", "stars": 7},
    {"id": 3, "repo": "arra-memory-py", "lang": "py", "stars": 1},
]
tbl = db.create_table("repos", data=rows, mode="overwrite")

# 3. Read back. to_pandas / to_arrow / to_list all work.
print("schema:\n", tbl.schema, "\n")
print("all rows:\n", tbl.to_pandas(), "\n")

# 4. Filter = SQL-ish where clause, pushed down to the file scan.
print("ts only:\n", tbl.search().where("lang = 'ts'").to_pandas(), "\n")

# 5. Append. Lance writes a NEW fragment, never rewrites old ones.
tbl.add([{"id": 4, "repo": "lanceglass", "lang": "ts", "stars": 2}])
print("count after add:", tbl.count_rows())
print("version:", tbl.version)
