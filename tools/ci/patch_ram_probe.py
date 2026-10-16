#!/usr/bin/env python3
"""Read-only, low-noise memory attribution probes for the pinned Ruffle source.

Apply after patch_owned_fws.py. Source patch edits only the temporary Actions
checkout. The resulting experimental binary is safe to run without a disk cache.
Counts are *allocation events*, never claimed to be current live heap bytes.
"""
import sys
from pathlib import Path
root=Path(sys.argv[1])
def edit(path, old, new, n=1):
    p=root/path
    s=p.read_text()
    if s.count(old)!=n:
        raise RuntimeError(f'{path}: expected {n} exact anchors, found {s.count(old)}: {old[:95]!r}')
    p.write_text(s.replace(old,new,n))
    print("instrumented",path,old[:65])

helper=String.raw if False else None
module=r'''//! SSF2 allocation-attribution experiments.
 //! These are cumulative observed creation/growth events, NOT live memory.
use std::sync::atomic::{AtomicU64, Ordering};

#[derive(Clone, Copy, Debug)]
pub enum Kind {
    ByteArrayImported,
    ByteArrayGrow,
    ByteArrayInflate,
    BitmapRawPixels,
    BitmapCompressed,
    BitmapDecoded,
}
struct Metric {
    events: AtomicU64,
    bytes: AtomicU64,
    max_single: AtomicU64,
}
impl Metric {
    const fn new() -> Self {
        Self {
            events: AtomicU64::new(0),
            bytes: AtomicU64::new(0),
            max_single: AtomicU64::new(0),
        }
    }
}
static IMPORTED: Metric = Metric::new();
static GROWN: Metric = Metric::new();
static INFLATE: Metric = Metric::new();
static RAW_PIXELS: Metric = Metric::new();
static COMPRESSED: Metric = Metric::new();
static DECODED: Metric = Metric::new();

pub fn record(kind: Kind, size: usize) {
    if size == 0 {
        return;
    }
    let (label, metric) = match kind {
        Kind::ByteArrayImported => ("ByteArray.import", &IMPORTED),
        Kind::ByteArrayGrow => ("ByteArray.growth", &GROWN),
        Kind::ByteArrayInflate => ("ByteArray.inflate", &INFLATE),
        Kind::BitmapRawPixels => ("BitmapData.CPU_RGBA", &RAW_PIXELS),
        Kind::BitmapCompressed => ("SWF.Bitmap.compressed", &COMPRESSED),
        Kind::BitmapDecoded => ("SWF.Bitmap.decoded_rgba", &DECODED),
    };
    let bytes = size as u64;
    let old = metric.bytes.fetch_add(bytes, Ordering::Relaxed);
    let total = old.saturating_add(bytes);
    let count = metric.events.fetch_add(1, Ordering::Relaxed) + 1;
    metric.max_single.fetch_max(bytes, Ordering::Relaxed);
    const INTERVAL: u64 = 16 * 1024 * 1024;
    const LARGE: u64 = 4 * 1024 * 1024;
    if bytes >= LARGE || total / INTERVAL != old / INTERVAL {
        eprintln!(
            "[SSF2-RAM] category={} event_bytes={} total_event_bytes={} events={} largest_event_bytes={}",
            label, bytes, total, count, metric.max_single.load(Ordering::Relaxed)
        );
    }
}
'''
p=root/"core/src/memory_probe.rs"
if p.exists(): raise RuntimeError("memory_probe module already exists")
p.write_text(module)
edit("core/src/lib.rs","mod library;","mod library;\nmod memory_probe;")

path="core/src/avm2/bytearray.rs"
edit(path,"""    pub fn from_vec(context: &mut UpdateContext<'_>, bytes: Vec<u8>) -> ByteArrayStorage {
        ByteArrayStorage {""","""    pub fn from_vec(context: &mut UpdateContext<'_>, bytes: Vec<u8>) -> ByteArrayStorage {
        crate::memory_probe::record(crate::memory_probe::Kind::ByteArrayImported, bytes.capacity());
        ByteArrayStorage {""")
edit(path,"""    pub fn set_length(&mut self, new_len: usize) {
        self.bytes.resize(new_len, 0);""","""    pub fn set_length(&mut self, new_len: usize) {
        let old_capacity = self.bytes.capacity();
        self.bytes.resize(new_len, 0);
        let growth = self.bytes.capacity().saturating_sub(old_capacity);
        crate::memory_probe::record(crate::memory_probe::Kind::ByteArrayGrow, growth);""")
edit(path,"""        if self.len() < (item + 1) {
            self.bytes.resize(item + 1, 0)
        }""","""        if self.len() < (item + 1) {
            self.set_length(item + 1);
        }""")
edit(path,"""    pub fn swap_storage_with(&mut self, new_data: &mut Vec<u8>) {
        self.position.set(0);""","""    pub fn swap_storage_with(&mut self, new_data: &mut Vec<u8>) {
        crate::memory_probe::record(crate::memory_probe::Kind::ByteArrayImported, new_data.capacity());
        self.position.set(0);""")
# Only the decompressor result, not the compression method.
edit(path,"""        if let Some(error) = error {
            tracing::warn!("ByteArray.decompress: {}", error);
            None
        } else {
            Some(buffer)
        }""","""        if let Some(error) = error {
            tracing::warn!("ByteArray.decompress: {}", error);
            None
        } else {
            crate::memory_probe::record(crate::memory_probe::Kind::ByteArrayInflate, buffer.capacity());
            Some(buffer)
        }""")

path="core/src/bitmap/bitmap_data.rs"
edit(path,"""    pub fn new(width: u32, height: u32, transparency: bool, fill_color: u32) -> Self {
        Self {
            pixels: vec![""","""    pub fn new(width: u32, height: u32, transparency: bool, fill_color: u32) -> Self {
        crate::memory_probe::record(
            crate::memory_probe::Kind::BitmapRawPixels,
            (width as usize).saturating_mul(height as usize)
                .saturating_mul(std::mem::size_of::<Color>()),
        );
        Self {
            pixels: vec![""")
edit(path,"""    pub fn new_with_pixels(
        width: u32,
        height: u32,
        transparency: bool,
        pixels: Vec<Color>,
    ) -> Self {
        Self {
            pixels,""","""    pub fn new_with_pixels(
        width: u32,
        height: u32,
        transparency: bool,
        pixels: Vec<Color>,
    ) -> Self {
        crate::memory_probe::record(
            crate::memory_probe::Kind::BitmapRawPixels,
            pixels.capacity().saturating_mul(std::mem::size_of::<Color>()),
        );
        Self {
            pixels,""")

path="core/src/character.rs"
edit(path,"""    pub fn new(compressed: CompressedBitmap) -> Self {
        Self {
            compressed,""","""    pub fn new(compressed: CompressedBitmap) -> Self {
        let byte_count = match &compressed {
            CompressedBitmap::Jpeg { data, alpha, .. } => {
                data.capacity() + alpha.as_ref().map_or(0, Vec::capacity)
            }
            CompressedBitmap::Lossless(data) => data.data.len(),
        };
        crate::memory_probe::record(crate::memory_probe::Kind::BitmapCompressed, byte_count);
        Self {
            compressed,""")
edit(path,"""        let decoded = self.compressed.decode()?;
        let new_handle = backend.register_bitmap(decoded)?;""","""        let decoded = self.compressed.decode()?;
        crate::memory_probe::record(
            crate::memory_probe::Kind::BitmapDecoded,
            (decoded.width() as usize).saturating_mul(decoded.height() as usize)
                .saturating_mul(4),
        );
        let new_handle = backend.register_bitmap(decoded)?;""")
print("SSF2 RAM attribution source patch ready; no disk cache and no game assets bundled.")
