from __future__ import annotations

import re

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{5,32}$")


class PhoneValidationError(ValueError):
    pass


def normalize_phone(raw_phone: str, default_region: str = "RU") -> str:
    value = (raw_phone or "").strip()
    if not value:
        raise PhoneValidationError("Номер пустой.")

    try:
        parsed = phonenumbers.parse(value, default_region)
    except NumberParseException as exc:
        raise PhoneValidationError("Не удалось разобрать номер.") from exc

    if not phonenumbers.is_possible_number(parsed) or not phonenumbers.is_valid_number(parsed):
        raise PhoneValidationError("Номер некорректен или неполон.")

    return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)


def normalize_username(raw_username: str | None) -> str | None:
    if raw_username is None:
        return None

    value = raw_username.strip()
    if not value:
        return None

    if value.startswith("@"):
        value = value[1:]

    if not USERNAME_RE.fullmatch(value):
        raise ValueError("Поле username должно быть похоже на Telegram username: 5-32 символа, буквы, цифры, подчёркивание.")

    return value


def normalize_nickname(raw_nickname: str | None) -> str | None:
    if raw_nickname is None:
        return None

    value = raw_nickname.strip()
    if not value:
        return None

    if len(value) > 255:
        raise ValueError("Поле nickname слишком длинное.")

    return value
