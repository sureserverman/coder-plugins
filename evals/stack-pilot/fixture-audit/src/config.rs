use serde::Deserialize;

/// Settings read from `ingest.json`.
#[derive(Debug, Deserialize)]
pub struct Config {
    pub name: String,
    pub port: String,
    pub jobs: Vec<String>,
}

impl Config {
    pub fn from_json(text: &str) -> Result<Config, serde_json::Error> {
        serde_json::from_str(text)
    }
}
