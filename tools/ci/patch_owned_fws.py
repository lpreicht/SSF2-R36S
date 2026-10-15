#!/usr/bin/env python3
"""Patch pinned aweigit Ruffle fork: retain owned FWS buffers on Loader.loadBytes.

For development experiments only. No SSF2 game contents are added to the repo.
Every source edit checks its anchor before changing any file.
"""
from pathlib import Path

root = Path(__import__("sys").argv[1])

def rewrite(path, old, new, count=1):
    p = root / path
    text = p.read_text()
    n = text.count(old)
    if n != count:
        raise RuntimeError(f"{path}: expected {count} occurrence(s), found {n}: {old[:80]!r}")
    p.write_text(text.replace(old, new, count))
    print("patched", path, old[:75])

# 1. Move the existing SWF body parser into a helper that accepts an already owned Vec.
read_path = root / "swf/src/read.rs"
content = read_path.read_text()
func = content.index("pub fn decompress_swf<'a")
start = content.index("    let mut reader = Reader::new(&data, version);", func)
end = content.index("\n}\n", start) + 3
parse_body = content[start:end]
assert "Ok(SwfBuf {" in parse_body
assert content[func:end].count("    let mut reader = Reader::new(&data, version);") == 2
existing_func = content[func:start]
existing_func += "    parse_uncompressed_swf_data(data, compression, version, uncompressed_len)\n}\n"
owned_func = r"""
/// Avoid duplicating the large already-uncompressed FWS payload in memory.
/// CWS and ZWS retain the ordinary validated decompressor.
pub fn decompress_swf_owned(mut bytes: Vec<u8>) -> Result<SwfBuf> {
    if bytes.len() >= 8 && bytes.starts_with(b"FWS") {
        let version = bytes[3];
        if version == 0 {
            return Err(Error::invalid_data("Invalid SWF version"));
        }
        let uncompressed_len = u32::from_le_bytes(bytes[4..8].try_into().unwrap());
        // Remove the 8-byte FWS header in-place: avoids another allocation,
        // preserving the existing parser's usual data layout.
        bytes.drain(..8);
        if bytes.len() as u64 + 8 != uncompressed_len as u64 {
            log::warn!("SWF length doesn't match header, may be corrupt");
        }
        parse_uncompressed_swf_data(bytes, Compression::None, version, uncompressed_len)
    } else {
        decompress_swf(&bytes[..])
    }
}

fn parse_uncompressed_swf_data(
    mut data: Vec<u8>,
    compression: Compression,
    version: u8,
    uncompressed_len: u32,
) -> Result<SwfBuf> {
"""
# parse_body currently ends with closing '}' for original function; use it
content=content[:func]+existing_func+owned_func+parse_body+content[end:]
read_path.write_text(content)
print("patched", read_path)

# 2. Add an owned pathway without altering semantics of existing from_data call sites.
p = root / "core/common/src/tag_utils.rs"
s = p.read_text()
beg=s.index("    pub fn from_data(")
ending=s.index("    /// Construct a movie based on a loaded image",beg)
normal=s[beg:ending]
assert "swf_data: &[u8]" in normal and "swf::read::decompress_swf(swf_data)?" in normal
owned=normal.replace("pub fn from_data(", "pub fn from_data_owned(")
owned=owned.replace("swf_data: &[u8]", "swf_data: Vec<u8>")
owned=owned.replace("swf::read::decompress_swf(swf_data)?", "swf::read::decompress_swf_owned(swf_data)?")
assert owned!=normal
s=s[:ending]+"    /// Consume an owned SWF buffer to avoid a second allocation for FWS data.\n"+owned+s[ending:]
p.write_text(s)
print("patched",p)

# 3. Transfer already copied Loader.loadBytes Vec directly into SwfMovieData.
# AVM2 ByteArray still retains its own storage, preserving AS3-visible semantics.
p=root/"core/src/loader.rs"
s=p.read_text()
replaces=[
(
"""            && let Ok(data) = extract_swz(data)""",
"""            && let Ok(data) = extract_swz(&data)"""
),
(
"""                let bitmap = ruffle_render::utils::decode_define_bits_jpeg(data, None)?;""",
"""                let bitmap = ruffle_render::utils::decode_define_bits_jpeg(&data, None)?;"""
),
(
"""                &body,
                url.to_string(),
                status,""",
"""                body,
                url.to_string(),
                status,"""
),
(
"""            let movie = SwfMovie::from_data(&bytes, "file:///".into(), loader_url)?;""",
"""            let movie = SwfMovie::from_data_owned(bytes, "file:///".into(), loader_url)?;"""
),
(
"""        MovieLoader::movie_loader_data(handle, uc, &bytes, "file:///".into(), 0, false, loader_url)""",
"""        MovieLoader::movie_loader_data(handle, uc, bytes, "file:///".into(), 0, false, loader_url)"""
),
(
"""        data: &[u8],
        url: String,
        status: u16,
        redirected: bool,
        loader_url: Option<String>,
    ) -> Result<(), Error> {
        let sniffed_type = ContentType::sniff(data);""",
"""        mut data: Vec<u8>,
        url: String,
        status: u16,
        redirected: bool,
        loader_url: Option<String>,
    ) -> Result<(), Error> {
        let sniffed_type = ContentType::sniff(&data);"""
),
(
"""            return Self::movie_loader_data(handle, uc, &data, url, status, redirected, loader_url);""",
"""            return Self::movie_loader_data(handle, uc, data, url, status, redirected, loader_url);"""
),
(
"""                let mut movie = SwfMovie::from_data(data, url.clone(), loader_url.clone())?;""",
"""                let mut movie = SwfMovie::from_data_owned(
                    std::mem::take(&mut data),
                    url.clone(),
                    loader_url.clone(),
                )?;"""
),
(
"""                data.len(),
            ));

            // Expose 'bytesTotal'""",
"""                length,
            ));

            // Expose 'bytesTotal'"""
)]
for old,new in replaces:
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f"loader.rs: unexpected {n} matches: {old[:100]!r}")
    s=s.replace(old,new,1)
p.write_text(s)
print("patched",p)
print("Owned-FWS experiment applied; run cargo check and SWF tests before packaging.")
