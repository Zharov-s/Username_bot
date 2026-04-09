from __future__ import annotations

from html import escape

from app.services.lookup_service import LookupResult


def welcome_text(source_name: str) -> str:
    return (
        "Здравствуйте. Это privacy-safe бот для законной обработки номеров телефонов.\n\n"
        f"Я ищу данные только в разрешённом источнике: <b>{escape(source_name)}</b>.\n"
        "Я не выполняю скрытый поиск, парсинг, OSINT-скрапинг, deanonymization и не извлекаю данные о третьих лицах из чужих систем.\n\n"
        "Что можно делать:\n"
        "• /import — импортировать свой CSV-список с opt-in\n"
        "• отправить один номер сообщением — найти username/nickname\n"
        "• /lookup_file — загрузить TXT/CSV со списком номеров для пакетной проверки\n"
        "• /stats — посмотреть количество доступных записей\n"
        "• /cancel — отменить текущий режим\n"
        "• /help — подробная инструкция"
    )


def help_text(source_name: str, privacy_email: str) -> str:
    return (
        "Как пользоваться ботом\n\n"
        f"1) Сначала импортируйте собственный легальный источник <b>{escape(source_name)}</b> командой /import.\n"
        "   Формат CSV: <code>phone,username,nickname,consent_status</code>\n"
        "   Пример строки: <code>+79991234567,ivan_petrov,Иван Петров,opt_in</code>\n\n"
        "2) Для одиночной проверки просто отправьте один номер телефона текстом.\n\n"
        "3) Для пакетной проверки используйте /lookup_file и затем загрузите TXT или CSV со списком номеров.\n\n"
        "Важно:\n"
        "• я не показываю данные без подтверждённого opt-in\n"
        "• я не ищу информацию вне разрешённого источника\n"
        "• я не храню исходные загруженные файлы после обработки\n"
        f"• вопросы по privacy: {escape(privacy_email)}"
    )


def import_instructions(source_name: str) -> str:
    return (
        f"Загрузите CSV-файл для источника <b>{escape(source_name)}</b>.\n\n"
        "Обязательная колонка: <code>phone</code>\n"
        "Необязательные колонки: <code>username</code>, <code>nickname</code>, <code>consent_status</code>\n\n"
        "Бот импортирует только записи с <code>consent_status=opt_in</code> и с указанным username или nickname.\n"
        "Пример строки:\n"
        "<code>+79991234567,ivan_petrov,Иван Петров,opt_in</code>"
    )


def lookup_file_instructions(limit: int) -> str:
    return (
        "Загрузите TXT или CSV со списком номеров для пакетной проверки.\n"
        "TXT: один номер в строке.\n"
        "CSV: колонка <code>phone</code> или номер в первом столбце.\n\n"
        f"Максимум номеров за один файл: <b>{limit}</b>."
    )


def single_lookup_success(result: LookupResult, source_name: str) -> str:
    parts = [f"<b>Результат для {escape(result.phone_e164)}</b>"]
    if result.username:
        parts.append(f"username: <code>@{escape(result.username)}</code>")
    if result.nickname:
        parts.append(f"nickname: <code>{escape(result.nickname)}</code>")
    parts.append(f"источник: <b>{escape(source_name)}</b>")
    return "\n".join(parts)


def single_lookup_refusal(result: LookupResult, source_name: str) -> str:
    return (
        f"<b>Результат для {escape(result.phone_e164)}</b>\n"
        f"{escape(result.reason or 'Нет доступного результата.')}\n"
        f"Поиск выполняется только в разрешённом источнике <b>{escape(source_name)}</b>."
    )


def import_summary_text(processed_rows: int, imported_rows: int, rejected_rows: int, rejected_preview: list[str]) -> str:
    base = (
        "<b>Импорт завершён</b>\n"
        f"Обработано строк: <b>{processed_rows}</b>\n"
        f"Импортировано/обновлено: <b>{imported_rows}</b>\n"
        f"Отклонено: <b>{rejected_rows}</b>"
    )
    if not rejected_preview:
        return base

    preview = "\n".join(f"• {escape(item)}" for item in rejected_preview)
    return f"{base}\n\nПервые причины отклонения:\n{preview}"


def stats_text(total_records: int, source_name: str) -> str:
    return (
        f"В источнике <b>{escape(source_name)}</b> сейчас доступно записей с opt-in: <b>{total_records}</b>."
    )


def bulk_summary_text(results: list[LookupResult], rejected_count: int) -> str:
    found = sum(1 for item in results if item.found)
    total = len(results)
    lines = [
        "<b>Пакетная проверка завершена</b>",
        f"Нормализовано номеров: <b>{total}</b>",
        f"Найдено результатов: <b>{found}</b>",
        f"Отклонено на этапе разбора файла: <b>{rejected_count}</b>",
    ]

    preview_items = []
    for item in results[:10]:
        if item.found:
            parts = [escape(item.phone_e164)]
            if item.username:
                parts.append(f"@{escape(item.username)}")
            if item.nickname:
                parts.append(escape(item.nickname))
            preview_items.append(" — ".join(parts))
        else:
            preview_items.append(f"{escape(item.phone_e164)} — нет доступного результата")

    if preview_items:
        lines.append("")
        lines.append("Первые результаты:")
        lines.extend(f"• {item}" for item in preview_items)

    lines.append("")
    lines.append("Полная выгрузка приложена CSV-файлом.")
    return "\n".join(lines)


GENERIC_ERROR_TEXT = (
    "Произошла внутренняя ошибка. Попробуйте ещё раз позже. "
    "Если ошибка повторяется, проверьте настройки .env и подключение к базе данных."
)

UNKNOWN_INPUT_TEXT = (
    "Я ожидаю либо один номер телефона текстом, либо файл после команды /import или /lookup_file.\n"
    "Команда /help покажет примеры."
)

CANCELLED_TEXT = "Текущий режим отменён."
FILE_TOO_LARGE_TEXT = "Файл слишком большой для безопасной обработки."
UNSUPPORTED_FILE_TEXT = "Неподдерживаемый тип файла."
