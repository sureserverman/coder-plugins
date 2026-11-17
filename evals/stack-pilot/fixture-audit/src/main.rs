use ingest::{config::Config, port, queue};

#[tokio::main]
async fn main() {
    let text = std::fs::read_to_string("ingest.json").expect("read ingest.json");
    let config = Config::from_json(&text).expect("parse ingest.json");
    let port = port::parse_port(&config.port).unwrap_or_else(|_| port::default_port());
    println!("{} on port {port}", config.name);
    let (tx, worker) = queue::start();
    for job in config.jobs {
        tx.send(job).expect("worker is running");
    }
    drop(tx);
    let done = worker.await.expect("worker finished");
    println!("{done} job(s) done");
}
