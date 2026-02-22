from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    target_dir = repo_root / "context_sources"
    out_md = repo_root / "docs" / "CONTEXT" / "FILE_MANIFEST.md"

    files = sorted(p for p in target_dir.rglob("*") if p.is_file())

    lines: list[str] = []
    lines.append("# File Manifest")
    lines.append("")
    lines.append("Deterministic checksum manifest for copied context sources.")
    lines.append("")
    lines.append("| Relative path | Size (bytes) | SHA256 |")
    lines.append("|---|---:|---|")

    for p in files:
        rel = p.relative_to(repo_root).as_posix()
        size = p.stat().st_size
        digest = sha256_file(p)
        lines.append(f"| `{rel}` | {size} | `{digest}` |")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {out_md}")


if __name__ == "__main__":
    main()
