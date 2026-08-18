from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT_FILE = ROOT / "files.md"

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "node_modules",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".claude",
    ".github",
}

SKIP_FILES = {
    "collect_files.py",
    "files.md",
    "all_files.txt",
    "all_files.md",
    "package-lock.json",
}


def iter_project_files(root: Path):
    collected = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        parts = path.parts
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue

        if path.name in SKIP_FILES:
            continue

        collected.append(path)

    return sorted(collected, key=lambda p: p.relative_to(root).as_posix())


def is_text_file(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(1024)
    except Exception:
        return False

    return b"\x00" not in chunk


def write_output(files):
    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        out.write("# Collected Project Files\n\n")
        out.write(f"Root directory: `{ROOT.as_posix()}`\n\n")

        for file_path in files:
            rel_path = file_path.relative_to(ROOT).as_posix()
            out.write(f"## {rel_path}\n\n")
            out.write("~~~text\n")

            try:
                with file_path.open("r", encoding="utf-8", errors="replace") as source:
                    content = source.read()
                out.write(content)
            except Exception as exc:
                out.write(f"[ERROR reading file: {exc}]\n")

            if not content.endswith("\n"):
                out.write("\n")

            out.write("~~~\n\n")


if __name__ == "__main__":
    files = iter_project_files(ROOT)
    files = [path for path in files if is_text_file(path)]
    write_output(files)

    print(f"\n✅ Done! Total text files collected: {len(files)}")
    for path in files:
        print(f"  - {path.relative_to(ROOT).as_posix()}")