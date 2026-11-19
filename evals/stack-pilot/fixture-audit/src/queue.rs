use tokio::sync::mpsc;
use tokio::task::JoinHandle;

/// Starts the worker task and returns the sender that feeds it.
pub fn start() -> (mpsc::UnboundedSender<String>, JoinHandle<usize>) {
    let (tx, mut rx) = mpsc::unbounded_channel();
    let worker = tokio::spawn(async move {
        let mut done = 0;
        while let Some(job) = rx.recv().await {
            println!("job: {job}");
            done += 1;
        }
        done
    });
    (tx, worker)
}
