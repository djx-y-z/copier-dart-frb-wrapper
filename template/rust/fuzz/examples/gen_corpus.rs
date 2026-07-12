//! Seed-corpus generator for the fuzz targets — EXTEND ME.
//!
//! libFuzzer explores much faster when it starts from structurally-correct
//! inputs instead of discovering your wire formats blind. This program writes
//! such seeds to `corpus/<target>/` (the directory `cargo fuzz` picks up
//! automatically). Run it via `make fuzz-seed`; the Fuzz CI workflow runs it
//! before every fuzzing session.
//!
//! As you add fuzz targets, add a section per target that produces VALID
//! serializations of the objects that target parses, using your library's own
//! API. For example, for a `keys` target that deserializes key material:
//!
//! ```ignore
//! if let Ok(key_pair) = KeyPair::generate() {
//!     if let Ok(bytes) = key_pair.serialize() {
//!         write_seed(&base.join("keys"), "key_pair", &bytes);
//!     }
//! }
//! ```
//!
//! If a target dispatches on a selector byte (`match data[0] % N`), prefix
//! each seed with the selector the payload corresponds to.

use std::fs;
use std::path::Path;

fn write_seed(dir: &Path, name: &str, bytes: &[u8]) {
    if let Err(e) = fs::create_dir_all(dir) {
        eprintln!("skip {}: {}", dir.display(), e);
        return;
    }
    let path = dir.join(name);
    if let Err(e) = fs::write(&path, bytes) {
        eprintln!("skip {}: {}", path.display(), e);
    } else {
        println!("wrote {} ({} bytes)", path.display(), bytes.len());
    }
}

fn main() {
    let base = std::env::args().nth(1).unwrap_or_else(|| "corpus".to_string());
    let base = Path::new(&base);

    // --- example target (fuzz_targets/example.rs) ---
    // The placeholder target feeds bytes to the init function as a UTF-8
    // string, so plain strings are already valid seeds. REPLACE this section
    // (together with the target itself) with seeds for your real parsers.
    write_seed(&base.join("example"), "ascii", b"hello");
    write_seed(&base.join("example"), "unicode", "\u{03c0}\u{2205}\u{1f980}".as_bytes());
    write_seed(&base.join("example"), "empty", b"");

    println!("Seed corpus generation complete.");
}
