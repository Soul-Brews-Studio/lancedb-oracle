import { connect } from "@lancedb/lancedb";

const db = await connect("./data");
const tbl = await db.openTable("users");

const count = await tbl.countRows();
const schema = (await tbl.schema()).fields.map((f) => `${f.name}:${f.type}`);
const rows = await tbl.query().where("plan != 'free'").limit(10).toArray();

console.log("ts      count:", String(count));
console.log("ts      schema:", JSON.stringify(schema));
console.log("ts      where :", JSON.stringify(rows.map((r) => r.name)));
