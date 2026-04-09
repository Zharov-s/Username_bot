from __future__ import annotations

import io
from pathlib import Path

from aiogram import Bot
from aiogram.types import Document


def detect_extension(filename: str | None) -> str:
    if not filename:
        return ""
    return Path(filename).suffix.lower()


async def download_document_bytes(bot: Bot, document: Document) -> bytes:
    buffer = io.BytesIO()
    await bot.download(document, destination=buffer)
    return buffer.getvalue()
