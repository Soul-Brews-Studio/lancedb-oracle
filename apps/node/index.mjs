// Same tiny app as apps/bun, on Node with @lancedb/lancedb 0.27.2 — the fleet's pin.
// Run: npm install && npm start
import { connect } from "@lancedb/lancedb";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const posts = readFileSync("../../lessons/data/nat_posts.jsonl", "utf8")
  .split("\n").filter(Boolean).map((l) => JSON.parse(l));

// 1. connect = pick a folder. Same directory format Python wrote in the lessons.
const db = await connect("./data");
const tbl = await db.createTable("posts", posts, { mode: "overwrite" });
console.log(`created  rows=${await tbl.countRows()} version=${await tbl.version()}`);

// 2. upsert: p11 exists -> update; p12 is new -> insert
await tbl.mergeInsert("id")
  .whenMatchedUpdateAll()
  .whenNotMatchedInsertAll()
  .execute([
    { ...posts[10], topic: "hardware", text: posts[10].text + " (edited)" },
    { id: "p12", date: "2026-09-10", topic: "memory", vector: [0.95, 0.05, 0.0], text: "Lance Oracle เปิดสอน LanceDB บทที่ 1-20 แล้วครับ" },
  ]);
console.log(`upserted rows=${await tbl.countRows()} version=${await tbl.version()}`);

// 3. vector search: nearest to the "memory" direction, hardware only (prefilter)
const q = [1, 0, 0];
const near = await tbl.vectorSearch(q).limit(3).toArray();
const hard = await tbl.vectorSearch(q).where("topic = 'hardware'").limit(3).toArray();
const show = (rows) => console.table(rows.map((r) => ({
  id: r.id, topic: r.topic, _distance: r._distance.toFixed(2), text: String(r.text).slice(0, 40),
})));
console.log("nearest to [1,0,0]:"); show(near);
console.log("nearest, topic = hardware:"); show(hard);

// 4. disk: one manifest per commit, one fragment per write
const dir = "./data/posts.lance";
const count = (sub, ext) => readdirSync(join(dir, sub)).filter((f) => f.endsWith(ext)).length;
const bytes = (d) => readdirSync(d).reduce((n, f) => {
  const p = join(d, f); return n + (statSync(p).isDirectory() ? bytes(p) : statSync(p).size);
}, 0);
console.log(`disk     fragments=${count("data", ".lance")} manifests=${count("_versions", ".manifest")} txn=${count("_transactions", ".txn")} bytes=${bytes(dir)}`);

// 5. full-text search: icu tokenizer so Thai words split; "จอ" lives in p09 p10
//    0.27.2 ships lance-index 4.0.0, which has no icu tokenizer — fall back to ngram and say so
import { Index } from "@lancedb/lancedb";
let tokenizer = "icu";
try {
  await tbl.createIndex("text", { config: Index.fts({ baseTokenizer: "icu" }) });
} catch (e) {
  console.log(`icu      ${String(e.message).split("\n")[0].slice(0, 90)}`);
  tokenizer = "ngram";
  await tbl.createIndex("text", { config: Index.fts({ baseTokenizer: "ngram", ngramMinLength: 2, ngramMaxLength: 3 }) });
}
const fts = await tbl.search("จอ", "fts").limit(3).toArray();
console.log(`fts 'จอ' (${tokenizer}):`);
console.table(fts.map((r) => ({ id: r.id, topic: r.topic, _score: r._score.toFixed(2), text: String(r.text).slice(0, 40) })));
console.log(`indices  ${(await tbl.listIndices()).map((i) => `${i.name}:${i.indexType}`).join(" ")}`);
