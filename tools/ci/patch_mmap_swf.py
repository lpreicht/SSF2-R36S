#!/usr/bin/env python3
"""Optional disk-backed SWF movie storage, protected by an explicit runtime flag.

Must run after tools/ci/patch_owned_fws.py, against the pinned Ruffle fork.
No user files are changed by this patch; it only changes source in CI.
Disk I/O is DISABLED unless SSF2_MMAP_CACHE_DIR points to an existing directory.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1])
def exact(path,old,new,expected=1):
    p=root/path
    s=p.read_text()
    found=s.count(old)
    if found != expected:
        raise RuntimeError(f"{path}: expected {expected} matches, found {found} for {old[:70]!r}")
    p.write_text(s.replace(old,new))
    print("Patched",path)

exact("core/common/Cargo.toml","[dependencies]","""[features]
default = []
disk-mmap-experiment = ["dep:memmap2", "dep:tempfile"]

[dependencies]
memmap2 = { workspace = true, optional = true }
tempfile = { workspace = true, optional = true }""")
exact("core/Cargo.toml",'[features]\ndefault = []','[features]\ndefault = []\ndisk-mmap-experiment = ["ruffle_common/disk-mmap-experiment"]')
path="core/common/src/tag_utils.rs"
p=root/path
s=p.read_text()
anchor="pub type SwfStream<'a> = swf::read::Reader<'a>;"
assert s.count(anchor)==1
helper=r'''
/// Immutable SWF data. With the experimental feature enabled, larger
/// already-parsed FWS bodies can live in a read-only file-backed mapping.
/// Each mapping is ref-counted; the anonymous backing file is reclaimed
/// when the last mapping disappears, including after a process crash.
///
/// This is NOT a general game memory optimizer: AVM2 ByteArray and decoded
/// bitmap allocations remain separately owned by the Flash emulator.
#[derive(Clone, Debug)]
enum SwfStorage {
    Heap(Vec<u8>),
    #[cfg(feature = "disk-mmap-experiment")]
    Mapped(std::sync::Arc<memmap2::Mmap>),
}
impl From<Vec<u8>> for SwfStorage {
    fn from(data: Vec<u8>) -> Self {
        Self::Heap(data)
    }
}
impl AsRef<[u8]> for SwfStorage {
    fn as_ref(&self) -> &[u8] {
        match self {
            Self::Heap(data) => data.as_slice(),
            #[cfg(feature = "disk-mmap-experiment")]
            Self::Mapped(mapped) => mapped.as_ref(),
        }
    }
}
impl SwfStorage {
    fn maybe_disk(data: Vec<u8>) -> Self {
        #[cfg(feature = "disk-mmap-experiment")]
        {
            use std::io::Write;
            use std::sync::atomic::{AtomicU64, Ordering};
            const MIN_BYTES: usize = 128 * 1024;
            const MAX_BYTES: u64 = 1024 * 1024 * 1024;
            static RESERVED: AtomicU64 = AtomicU64::new(0);
            let len = data.len() as u64;
            if data.len() >= MIN_BYTES {
                if let Some(folder) = std::env::var_os("SSF2_MMAP_CACHE_DIR") {
                    let folder = std::path::PathBuf::from(folder);
                    if folder.is_dir() && len <= MAX_BYTES &&
                        RESERVED.fetch_update(Ordering::SeqCst, Ordering::SeqCst,
                            |used| used.checked_add(len).filter(|total| *total <= MAX_BYTES)
                        ).is_ok()
                    {
                        let result: std::io::Result<memmap2::Mmap> = (|| {
                            let mut file = tempfile::tempfile_in(&folder)?;
                            file.write_all(&data)?;
                            // Make pages clean before attempting to reclaim them.
                            file.sync_all()?;
                            // SAFETY: This process exclusively owns the anonymous file.
                            // After mapping, it is never written to or resized.
                            unsafe { memmap2::MmapOptions::new().map(&file) }
                        })();
                        match result {
                            Ok(mapped) => {
                                // This frontend initializes env_logger, not a tracing subscriber.
                                // Use stderr for observable per-resource diagnostics on ArkOS.
                                eprintln!(
                                    "[SSF2-CACHE] mapped {} bytes; cumulative reserved {} bytes",
                                    len,
                                    RESERVED.load(Ordering::SeqCst)
                                );
                                return Self::Mapped(std::sync::Arc::new(mapped));
                            },
                            Err(error) => {
                                RESERVED.fetch_sub(len, Ordering::SeqCst);
                                eprintln!(
                                    "[SSF2-CACHE] failed for {} bytes: {}",
                                    len, error
                                );
                            }
                        }
                    }
                }
            }
        }
        Self::Heap(data)
    }
}
#[cfg(all(test, feature = "disk-mmap-experiment"))]
mod disk_mmap_experiment_tests {
    use super::*;
    #[test]
    fn storage_mmap_preserves_content_and_cleans_up_backing_file() {
        use std::io::Write;
        let folder = tempfile::tempdir().expect("writable temp dir");
        let data = (0..262144usize).map(|n| (n % 251) as u8).collect::<Vec<_>>();
        let mut file = tempfile::tempfile_in(folder.path()).expect("tempfile");
        file.write_all(&data).expect("write");
        file.sync_all().expect("sync");
        let map = unsafe { memmap2::MmapOptions::new().map(&file) }.expect("map");
        let stored = SwfStorage::Mapped(std::sync::Arc::new(map));
        assert_eq!(stored.as_ref(), data.as_slice());
        let clone = stored.clone();
        drop(stored);
        assert_eq!(clone.as_ref(), data.as_slice());
        drop(file);
        drop(clone);
        assert!(folder.path().read_dir().expect("contents").next().is_none());
    }
}
'''
s=s.replace(anchor,anchor+"\n"+helper)
assert s.count("    data: Vec<u8>,")==1
s=s.replace("    data: Vec<u8>,","    data: SwfStorage,")
for old,new,expected in [
 ("data: vec![],","data: Vec::new().into(),",3),
 ("data: Vec::new(),","data: Vec::new().into(),",1),
 ("data: compressed_data,","data: compressed_data.into(),",1),
 ("data: swf_buf.data,","data: SwfStorage::maybe_disk(swf_buf.data),",2),
 ("        &self.data\n","        self.data.as_ref()\n",1),
]:
    n=s.count(old)
    if n!=expected:
        raise RuntimeError(f"{path}: unexpected {n} occurrences, need {expected}, anchor={old!r}")
    s=s.replace(old,new)
s=s.replace("self.data.len()", "self.data.as_ref().len()")
p.write_text(s)
print("Patched",path)
print("Disk-backed SWF buffers: opt-in only, 1 GiB cumulative limit, conservative heap fallback.")
