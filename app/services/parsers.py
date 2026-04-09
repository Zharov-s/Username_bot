from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path

from app.db.models import ConsentStatus
from app.utils.phone import PhoneValidationError, normalize_nickname, normalize_phone, normalize_username


CONTACT_PHONE_HEADERS = {"phone", "phone_number", "number", "msisdn"}
CONSENT_TRUE_VALUES = {"opt_in", "yes", "true", "1", "y", "да"}
CONSENT_FALSE_VALUES = {"no", "false", "0", "n", "нет", "revoked", "no_consent"}


@dataclass(slots=True)
class ParsedContactRow:
    row_number: int
    phone_e164: str
    username: str | None
    nickname: str | None


@dataclass(slots=True)
class RejectedRow:
    row_number: int
    reason: str


@dataclass(slots=True)
class ImportParseResult:
    rows: list[ParsedContactRow] = field(default_factory=list)
    rejected_rows: list[RejectedRow] = field(default_factory=list)


@dataclass(slots=True)
class LookupFileParseResult:
    phones: list[str] = field(default_factory=list)
    rejected_rows: list[RejectedRow] = field(default_factory=list)


def decode_bytes(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1251"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Файл должен быть в UTF-8 или CP1251.")


def sniff_dialect(sample: str) -> csv.Dialect:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def parse_consent(value: str | None) -> ConsentStatus:
    normalized = (value or "").strip().lower()
    if normalized in CONSENT_TRUE_VALUES:
        return ConsentStatus.OPT_IN
    if normalized in CONSENT_FALSE_VALUES or normalized == "":
        return ConsentStatus.NO_CONSENT
    raise ValueError("Неизвестное значение consent_status.")


def parse_import_contacts_csv(content: bytes, filename: str, max_rows: int, default_region: str) -> ImportParseResult:
    text = decode_bytes(content)
    if not text.strip():
        raise ValueError("Файл пуст.")

    if Path(filename).suffix.lower() != ".csv":
        raise ValueError("Для импорта источника используйте CSV-файл.")

    sample = text[:4096]
    dialect = sniff_dialect(sample)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV должен содержать заголовки колонок.")

    normalized_headers = {header.strip().lower() for header in reader.fieldnames if header}
    if "phone" not in normalized_headers and not CONTACT_PHONE_HEADERS.intersection(normalized_headers):
        raise ValueError("CSV должен содержать колонку phone.")

    result = ImportParseResult()
    dedup: dict[str, ParsedContactRow] = {}

    for index, row in enumerate(reader, start=2):
        if index - 1 > max_rows:
            raise ValueError(f"Слишком много строк. Лимит: {max_rows}.")

        try:
            raw_phone = pick_first_value(row, CONTACT_PHONE_HEADERS)
            phone_e164 = normalize_phone(raw_phone, default_region)
            consent_status = parse_consent(row.get("consent_status"))
            if consent_status != ConsentStatus.OPT_IN:
                raise ValueError("Нет подтверждённого opt-in consent_status.")

            username = normalize_username(row.get("username"))
            nickname = normalize_nickname(row.get("nickname"))

            if not username and not nickname:
                raise ValueError("Нужно указать хотя бы username или nickname.")
        except (KeyError, PhoneValidationError, ValueError) as exc:
            result.rejected_rows.append(RejectedRow(row_number=index, reason=str(exc)))
            continue

        dedup[phone_e164] = ParsedContactRow(
            row_number=index,
            phone_e164=phone_e164,
            username=username,
            nickname=nickname,
        )

    result.rows = list(dedup.values())
    return result


def parse_lookup_file(content: bytes, filename: str, max_rows: int, default_region: str) -> LookupFileParseResult:
    text = decode_bytes(content)
    if not text.strip():
        raise ValueError("Файл пуст.")

    extension = Path(filename).suffix.lower()
    if extension == ".txt":
        return parse_lookup_txt(text, max_rows=max_rows, default_region=default_region)
    if extension == ".csv":
        return parse_lookup_csv(text, max_rows=max_rows, default_region=default_region)
    raise ValueError("Поддерживаются только .txt и .csv для списка номеров.")


def parse_lookup_txt(text: str, max_rows: int, default_region: str) -> LookupFileParseResult:
    result = LookupFileParseResult()
    seen: set[str] = set()

    for index, raw_line in enumerate(text.splitlines(), start=1):
        if index > max_rows:
            raise ValueError(f"Слишком много строк. Лимит: {max_rows}.")

        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        try:
            phone_e164 = normalize_phone(line, default_region)
        except PhoneValidationError as exc:
            result.rejected_rows.append(RejectedRow(row_number=index, reason=str(exc)))
            continue

        if phone_e164 not in seen:
            seen.add(phone_e164)
            result.phones.append(phone_e164)

    return result


def parse_lookup_csv(text: str, max_rows: int, default_region: str) -> LookupFileParseResult:
    result = LookupFileParseResult()
    dialect = sniff_dialect(text[:4096])

    stream = io.StringIO(text)
    reader = csv.reader(stream, dialect=dialect)
    rows = list(reader)
    if not rows:
        raise ValueError("CSV пуст.")

    header = [cell.strip().lower() for cell in rows[0]]
    has_header = bool(CONTACT_PHONE_HEADERS.intersection(header))

    seen: set[str] = set()
    iterable = rows[1:] if has_header else rows

    phone_index = 0
    if has_header:
        for candidate in CONTACT_PHONE_HEADERS:
            if candidate in header:
                phone_index = header.index(candidate)
                break

    for index, row in enumerate(iterable, start=2 if has_header else 1):
        if index - (1 if has_header else 0) > max_rows:
            raise ValueError(f"Слишком много строк. Лимит: {max_rows}.")
        if not row:
            continue

        raw_phone = row[phone_index].strip() if phone_index < len(row) else ""
        if not raw_phone:
            result.rejected_rows.append(RejectedRow(row_number=index, reason="Пустой номер."))
            continue

        try:
            phone_e164 = normalize_phone(raw_phone, default_region)
        except PhoneValidationError as exc:
            result.rejected_rows.append(RejectedRow(row_number=index, reason=str(exc)))
            continue

        if phone_e164 not in seen:
            seen.add(phone_e164)
            result.phones.append(phone_e164)

    return result


def pick_first_value(row: dict[str, str | None], aliases: set[str]) -> str:
    for key, value in row.items():
        if key and key.strip().lower() in aliases:
            return (value or "").strip()
    raise KeyError("Не найдена колонка phone.")
