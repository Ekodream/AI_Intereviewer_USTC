import glob
import json
import os
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.rag_engine import build_vector_store

DATA_ROOT = ROOT / "data"
VECTOR_ROOT = ROOT / "vector_db"

# Keep compatibility with existing app defaults in main.py.
DOMAIN_ALIAS = {
    "cs_ai": "cs ai",
}


def _on_rm_error(func, path, _exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _iter_qa_files(folder: Path) -> list[Path]:
    paths = [Path(p) for p in glob.glob(str(folder / "qa_*.jsonl"))]
    return sorted(paths)


def _load_docs(folder: Path) -> list[dict]:
    docs: list[dict] = []
    for path in _iter_qa_files(folder):
        with path.open("r", encoding="utf-8-sig") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                obj = json.loads(line)
                content = f"{obj.get('question', '')}\n{obj.get('answer', '')}"
                metadata = {
                    "topic": obj.get("topic", ""),
                    "difficulty": obj.get("difficulty", ""),
                    "type": obj.get("type", ""),
                    "source_file": path.name,
                }
                docs.append({"content": content, "metadata": metadata})
    return docs


def _resolve_domain_name(data_folder_name: str) -> str:
    return DOMAIN_ALIAS.get(data_folder_name, data_folder_name)


def build_all_vectors() -> list[tuple[str, int, str]]:
    if not DATA_ROOT.exists():
        raise SystemExit(f"Data root not found: {DATA_ROOT}")

    VECTOR_ROOT.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, int, str]] = []

    for folder in sorted([p for p in DATA_ROOT.iterdir() if p.is_dir()]):
        docs = _load_docs(folder)
        if not docs:
            continue

        domain = _resolve_domain_name(folder.name)
        target = VECTOR_ROOT / domain
        if target.exists():
            shutil.rmtree(target, onerror=_on_rm_error)

        db_path = build_vector_store(
            docs=docs,
            domain=domain,
            persist_dir=str(VECTOR_ROOT),
            chunk_size=800,
            chunk_overlap=50,
        )
        results.append((domain, len(docs), db_path))

    return results


def main():
    results = build_all_vectors()
    if not results:
        raise SystemExit("No qa_*.jsonl files found under data/*")

    print("Built vector stores:")
    for domain, count, path in results:
        print(f"- {domain}: {count} docs -> {path}")


if __name__ == "__main__":
    main()
