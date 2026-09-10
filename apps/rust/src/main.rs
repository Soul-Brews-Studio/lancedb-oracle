// Same tiny app as apps/bun, apps/node, apps/python — on Rust with the lancedb crate 0.38.0.
// Run: cargo run --release
use std::{fs, path::Path, sync::Arc};

use arrow_array::{
    types::Float32Type, Array, FixedSizeListArray, Float32Array, RecordBatch, RecordBatchIterator, RecordBatchReader,
    StringArray,
};
use arrow_schema::{DataType, Field, Schema};
use futures::TryStreamExt;
use lancedb::{database::CreateTableMode, query::{ExecutableQuery, QueryBase}, Table};
use serde::Deserialize;

#[derive(Deserialize, Clone)]
struct Post { id: String, date: String, topic: String, vector: Vec<f32>, text: String }

fn schema() -> Arc<Schema> {
    Arc::new(Schema::new(vec![
        Field::new("id", DataType::Utf8, false),
        Field::new("date", DataType::Utf8, false),
        Field::new("topic", DataType::Utf8, false),
        Field::new("vector", DataType::FixedSizeList(Arc::new(Field::new("item", DataType::Float32, true)), 3), false),
        Field::new("text", DataType::Utf8, false),
    ]))
}

// Rust has no dict rows: columns are built one Arrow array at a time.
fn batch(posts: &[Post]) -> RecordBatch {
    let col = |f: fn(&Post) -> &str| Arc::new(StringArray::from(posts.iter().map(f).collect::<Vec<_>>())) as _;
    let vectors = FixedSizeListArray::from_iter_primitive::<Float32Type, _, _>(
        posts.iter().map(|p| Some(p.vector.iter().map(|v| Some(*v)).collect::<Vec<_>>())), 3);
    RecordBatch::try_new(schema(), vec![
        col(|p| &p.id), col(|p| &p.date), col(|p| &p.topic), Arc::new(vectors), col(|p| &p.text),
    ]).unwrap()
}

fn reader(posts: &[Post]) -> Box<dyn RecordBatchReader + Send> {
    Box::new(RecordBatchIterator::new(vec![Ok(batch(posts))].into_iter(), schema()))
}

async fn show(tbl: &Table, filter: Option<&str>) -> lancedb::Result<()> {
    let mut q = tbl.vector_search(vec![1.0f32, 0.0, 0.0])?.limit(3);
    if let Some(f) = filter { q = q.only_if(f); }
    let batches: Vec<RecordBatch> = q.execute().await?.try_collect().await?;
    println!("{:<4} {:<9} {:>9}  text", "id", "topic", "_distance");
    for b in &batches {
        let get = |name: &str| b.column_by_name(name).unwrap().as_any().downcast_ref::<StringArray>().unwrap();
        let dist = b.column_by_name("_distance").unwrap().as_any().downcast_ref::<Float32Array>().unwrap();
        for i in 0..b.num_rows() {
            let text: String = get("text").value(i).chars().take(40).collect();
            println!("{:<4} {:<9} {:>9.2}  {}", get("id").value(i), get("topic").value(i), dist.value(i), text);
        }
    }
    Ok(())
}

#[tokio::main]
async fn main() -> lancedb::Result<()> {
    let raw = fs::read_to_string("../../lessons/data/nat_posts.jsonl").expect("read posts");
    let posts: Vec<Post> = raw.lines().filter(|l| !l.trim().is_empty()).map(|l| serde_json::from_str(l).unwrap()).collect();

    // 1. connect = pick a folder. Same directory format the other three runtimes wrote.
    let db = lancedb::connect("./data").execute().await?;
    let tbl = db.create_table("posts", reader(&posts)).mode(CreateTableMode::Overwrite).execute().await?;
    println!("created  rows={} version={}", tbl.count_rows(None).await?, tbl.version().await?);

    // 2. upsert: p11 exists -> update; p12 is new -> insert
    let mut edited = posts[10].clone();
    edited.text.push_str(" (edited)");
    let new = Post { id: "p12".into(), date: "2026-09-10".into(), topic: "memory".into(),
        vector: vec![0.95, 0.05, 0.0], text: "Lance Oracle เปิดสอน LanceDB บทที่ 1-20 แล้วครับ".into() };
    let mut mi = tbl.merge_insert(&["id"]);
    mi.when_matched_update_all(None).when_not_matched_insert_all();
    mi.execute(reader(&[edited, new])).await?;
    println!("upserted rows={} version={}", tbl.count_rows(None).await?, tbl.version().await?);

    // 3. vector search: nearest to the "memory" direction, then hardware only (prefilter)
    println!("nearest to [1,0,0]:");
    show(&tbl, None).await?;
    println!("nearest, topic = hardware:");
    show(&tbl, Some("topic = 'hardware'")).await?;

    // 4. disk: one manifest per commit, one fragment per write
    let dir = Path::new("data/posts.lance");
    let count = |sub: &str, ext: &str| fs::read_dir(dir.join(sub)).unwrap()
        .filter(|e| e.as_ref().unwrap().path().extension().map_or(false, |x| x == ext)).count();
    fn bytes(p: &Path) -> u64 {
        fs::read_dir(p).unwrap().map(|e| { let p = e.unwrap().path(); if p.is_dir() { bytes(&p) } else { p.metadata().unwrap().len() } }).sum()
    }
    println!("disk     fragments={} manifests={} txn={} bytes={}",
        count("data", "lance"), count("_versions", "manifest"), count("_transactions", "txn"), bytes(dir));
    Ok(())
}
