//! settings-tool: the library behind the `settings-tool` binary.

/// The line the binary prints when it starts.
pub fn banner(name: &str) -> String {
    format!("{name} ready")
}
