use std::error::Error;

/// Parses a TCP port such as `"8080"`.
pub fn parse_port(text: &str) -> Result<u16, Box<dyn Error>> {
    let port: u16 = text.trim().parse()?;
    if port == 0 {
        return Err("port 0 is reserved".into());
    }
    Ok(port)
}

/// The port used when the config names none.
pub fn default_port() -> u16 {
    parse_port("8080").unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_a_port() {
        assert_eq!(parse_port("80").unwrap(), 80);
    }
}
