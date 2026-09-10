#!/usr/bin/env python3
"""fbx engine — load a Facebook export zip into LanceDB tables from a YAML spec, then query with SQL.

    engine.py load  fbx.yml            # zip -> Lance tables
    engine.py query fbx.yml <name>     # run a named query from the YAML
    engine.py sql   fbx.yml "<sql>"    # ad-hoc SQL over the tables
    engine.py tables fbx.yml           # list tables and row counts
    engine.py export fbx.yml <name|sql> out.{jsonl,csv,md}

Field paths: dotted, with [*] to fan out over lists (a.b[*].c -> list of c).
A field that resolves to a one-element list is unwrapped; empty -> null.
Derive expressions are Python evaluated per row with helpers from_unix(), regex().
"""
import datetime as dt
import fnmatch
import json
import os
import re
import sys
import zipfile

os.environ.setdefault("LANCE_LOG", "error")
from pathlib import Path, PurePosixPath

import duckdb
import lancedb
import yaml


def fix(s):
    if not isinstance(s, str):
        return s
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def decode_deep(o):
    if isinstance(o, dict):
        return {k: decode_deep(v) for k, v in o.items()}
    if isinstance(o, list):
        return [decode_deep(v) for v in o]
    return fix(o)


def resolve(obj, path: str):
    """a.b[*].c over dicts and lists. Returns list when [*] appears, else scalar or None."""
    if path == "$":
        return obj
    parts = re.findall(r"[^.\[\]]+|\[\*\]", path)
    cur = [obj]
    fanned = False
    for p in parts:
        nxt = []
        if p == "[*]":
            fanned = True
            for c in cur:
                if isinstance(c, list):
                    nxt.extend(c)
        else:
            for c in cur:
                if isinstance(c, dict) and p in c:
                    nxt.append(c[p])
        cur = nxt
    cur = [c for c in cur if c is not None]
    if not fanned:
        return cur[0] if cur else None
    return cur


def unwrap(v):
    if isinstance(v, list):
        if len(v) == 0:
            return None
        if len(v) == 1 and not isinstance(v[0], (list, dict)):
            return v[0]
    return v


HELPERS = {
    "from_unix": lambda ts: dt.datetime.fromtimestamp(ts, dt.timezone.utc).astimezone().isoformat(timespec="minutes") if ts else None,
    "regex": lambda s, pat: (m.group(1) if (s and (m := re.search(pat, s))) else None),
}


_compiled: dict = {}


def derive(row: dict, spec: dict):
    for name, expr in (spec or {}).items():
        code = _compiled.get(expr) or _compiled.setdefault(expr, compile(expr, f"<derive {name}>", "eval"))
        env = {**HELPERS, **row}
        try:
            row[name] = eval(code, {"__builtins__": {}}, env)
        except Exception as e:
            raise SystemExit(f"derive {name!r}: {expr!r} failed on row {row.get('ts')}: {e}")
    return row


def load_dataset(z: zipfile.ZipFile, name: str, ds: dict, decode: bool):
    files = sorted(n for n in z.namelist() if fnmatch.fnmatch(n, ds["glob"]))
    if not files:
        print(f"  {name}: no files match {ds['glob']}", file=sys.stderr)
        return []
    rows = []
    for fname in files:
        root = json.loads(z.read(fname))
        if decode:
            root = decode_deep(root)
        ctx = {}
        for k, expr in (ds.get("context") or {}).items():
            if expr == "@dir":
                ctx[k] = PurePosixPath(fname).parent.name
            elif expr == "@file":
                ctx[k] = PurePosixPath(fname).name
            else:
                ctx[k] = unwrap(resolve(root, expr))
        for rec in resolve(root, ds.get("records", "$")) or []:
            row = dict(ctx)
            for col, path in ds["fields"].items():
                row[col] = unwrap(resolve(rec, path))
            rows.append(derive(row, ds.get("derive")))
    print(f"  {name}: {len(rows)} rows from {len(files)} files", file=sys.stderr)
    return rows


def normalize(rows):
    """Lance infers the schema from the first rows; make list columns and nulls consistent."""
    cols = {}
    for r in rows:
        for k, v in r.items():
            if isinstance(v, list):
                cols[k] = "list"
            elif v is not None and cols.get(k) != "list":
                cols[k] = "scalar"
    for r in rows:
        for k, kind in cols.items():
            v = r.get(k)
            if kind == "list":
                r[k] = [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v is not None else [])
            elif k not in r:
                r[k] = None
    return rows


def cmd_load(cfg: dict):
    src = Path(cfg["source"]).expanduser()
    db = lancedb.connect(str(Path(cfg["lance"]).expanduser()))
    decode = cfg.get("decode") == "latin1-utf8"
    with zipfile.ZipFile(src) as z:
        for name, ds in cfg["datasets"].items():
            rows = normalize(load_dataset(z, name, ds, decode))
            if rows:
                db.create_table(name, data=rows, mode="overwrite")
    print(f"-> {cfg['lance']}", file=sys.stderr)


def connect(cfg: dict):
    db = lancedb.connect(str(Path(cfg["lance"]).expanduser()))
    con = duckdb.connect()
    for name in db.list_tables().tables if hasattr(db.list_tables(), "tables") else db.list_tables():
        con.register(name, db.open_table(name).to_arrow())
    return con


def cmd_sql(cfg: dict, sql: str):
    con = connect(cfg)
    df = con.sql(sql).df()
    import pandas as pd
    for c in df.columns:
        if pd.api.types.is_string_dtype(df[c]):
            df[c] = df[c].map(lambda v: v[:90].replace("\n", " ") if isinstance(v, str) else v)
    try:
        with pd.option_context("display.max_rows", 500, "display.width", 250, "display.max_colwidth", 95):
            print(df.to_string(index=False))
    except BrokenPipeError:
        pass


def cmd_export(cfg: dict, name: str, out: str):
    sql = cfg["queries"].get(name, name)
    df = connect(cfg).sql(sql).df()
    path = Path(out).expanduser()
    ext = path.suffix.lower()
    if ext == ".jsonl":
        with open(path, "w", encoding="utf-8") as f:
            for rec in df.to_dict("records"):
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    elif ext == ".csv":
        df.to_csv(path, index=False)
    elif ext == ".md":
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {name}\n\n{len(df)} rows\n\n")
            for rec in df.to_dict("records"):
                head = " · ".join(str(rec[c]) for c in df.columns if c != "text" and rec[c] is not None)
                f.write(f"## {head}\n\n")
                if "text" in rec and rec["text"]:
                    f.write(str(rec["text"]).strip() + "\n\n")
    else:
        sys.exit("export: use .jsonl, .csv or .md")
    print(f"{len(df)} rows -> {path}", file=sys.stderr)


def cmd_tables(cfg: dict):
    db = lancedb.connect(str(Path(cfg["lance"]).expanduser()))
    names = db.list_tables().tables if hasattr(db.list_tables(), "tables") else db.list_tables()
    for n in names:
        t = db.open_table(n)
        print(f"{n:<12} {t.count_rows():>6} rows  v{t.version}  {[f.name for f in t.schema]}")


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, cfg_path, *rest = sys.argv[1:]
    cfg = yaml.safe_load(open(cfg_path))
    if cmd == "load":
        cmd_load(cfg)
    elif cmd == "query":
        cmd_sql(cfg, cfg["queries"][rest[0]])
    elif cmd == "sql":
        cmd_sql(cfg, rest[0])
    elif cmd == "export":
        cmd_export(cfg, rest[0], rest[1])
    elif cmd == "tables":
        cmd_tables(cfg)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
