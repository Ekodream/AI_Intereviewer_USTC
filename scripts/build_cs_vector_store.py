import glob
import json
import os
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.rag_engine import build_vector_store

DATA_DIR_CANDIDATES = [
    ROOT / "data" / "cs ai",
    ROOT / "data" / "cs",
]
PERSIST_DIR = ROOT / "vector_db"
DOMAIN = "cs ai"


def resolve_data_dir() -> Path:
    for candidate in DATA_DIR_CANDIDATES:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return DATA_DIR_CANDIDATES[0]


def load_docs() -> list[dict]:
    data_dir = resolve_data_dir()
    docs = []
    for path in glob.glob(str(data_dir / "qa_*.jsonl")):
        with open(path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                content = f"{obj.get('question','')}\n{obj.get('answer','')}"
                metadata = {
                    "topic": obj.get("topic", ""),
                    "difficulty": obj.get("difficulty", ""),
                }
                docs.append({"content": content, "metadata": metadata})
    return docs


def _on_rm_error(func, path, exc_info):
    # Handle read-only files on Windows when removing existing vector store
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def main():
    docs = load_docs()
    if not docs:
        checked = ", ".join(str(p) for p in DATA_DIR_CANDIDATES)
        raise SystemExit(f"No docs found. Checked: {checked}")
    target_dir = PERSIST_DIR / DOMAIN
    if target_dir.exists():
        shutil.rmtree(target_dir, onerror=_on_rm_error)
    db_path = build_vector_store(
        docs=docs,
        domain=DOMAIN,
        persist_dir=str(PERSIST_DIR),
        chunk_size=800,
        chunk_overlap=50,
    )
    print(f"Vector store built at: {db_path}")


if __name__ == "__main__":
    main()
