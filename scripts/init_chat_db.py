from __future__ import annotations

from app.chat.db import ensure_chat_schema


def main() -> None:
    ensure_chat_schema()
    print("Chat schema ready.")


if __name__ == "__main__":
    main()
