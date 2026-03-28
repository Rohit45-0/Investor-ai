from __future__ import annotations

import argparse

from app.chat.indexer import index_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index processed runs into Postgres for Opportunity Radar chat.")
    parser.add_argument("--run-label", help="Run label to index. Defaults to latest processed run.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = index_run(args.run_label)
    print(f"Run label: {result['run_label']}")
    print(f"Documents indexed: {result['documents_indexed']}")
    print(f"Chunks indexed: {result['chunks_indexed']}")
    print(f"Embedding model: {result['embedding_model']}")


if __name__ == "__main__":
    main()
