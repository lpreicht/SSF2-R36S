#!/usr/bin/env python3
"""Select OpenGL ES 2.0 instead of desktop GL 4.1 in portable SDL frontend."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/"sdl2test-u/src/main.rs"
s=p.read_text()
replacements=[
    ("gl_attr.set_context_profile(GLProfile::Core);","gl_attr.set_context_profile(GLProfile::GLES);"),
    ("gl_attr.set_context_version(4, 1);","gl_attr.set_context_version(2, 0);")
]
for old,new in replacements:
    n=s.count(old)
    if n!=1:
        raise SystemExit(f"Expected exactly one {old!r}; found {n}")
    s=s.replace(old,new)
p.write_text(s)
print("R36S portable SDL renderer now requests OpenGL ES 2.0")
