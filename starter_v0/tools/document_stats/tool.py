from __future__ import annotations

import re
from typing import Any


def document_stats(text: str = "") -> dict[str, Any]:
    """
    Thống kê các thông tin cơ bản của một văn bản.
    """

    words = text.split()

    word_count = len(words)
    character_count = len(text)

    sentence_count = len(
        re.findall(r"[.!?]+", text)
    )

    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    paragraph_count = len(paragraphs)

    # Trung bình một người đọc khoảng 200 từ/phút
    reading_time = 0 if word_count == 0 else max(1, round(word_count / 200))

    return {
        "tool": "document_stats",
        "word_count": word_count,
        "character_count": character_count,
        "sentence_count": sentence_count,
        "paragraph_count": paragraph_count,
        "estimated_reading_time": f"{reading_time} phút",
    }