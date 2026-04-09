from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, Document, ErrorEvent, Message
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.db.repositories import ContactRepository, UserRepository
from app.db.session import session_scope
from app.services.import_service import ImportService
from app.services.lookup_service import LookupService
from app.services.parsers import parse_lookup_file
from app.telegram.messages import (
    CANCELLED_TEXT,
    FILE_TOO_LARGE_TEXT,
    GENERIC_ERROR_TEXT,
    UNKNOWN_INPUT_TEXT,
    bulk_summary_text,
    help_text,
    import_instructions,
    import_summary_text,
    lookup_file_instructions,
    single_lookup_refusal,
    single_lookup_success,
    stats_text,
    welcome_text,
)
from app.telegram.states import UploadStates
from app.utils.files import detect_extension, download_document_bytes
from app.utils.phone import PhoneValidationError, normalize_phone

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def command_start(
    message: Message,
    state: FSMContext,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await state.clear()
    if message.from_user is None:
        return

    async with session_scope(session_factory) as session:
        await UserRepository().get_or_create(session, message.from_user)

    await message.answer(welcome_text(settings.allowed_source_name))


@router.message(Command("help"))
async def command_help(message: Message, settings: Settings) -> None:
    await message.answer(help_text(settings.allowed_source_name, settings.privacy_contact_email))


@router.message(Command("cancel"))
async def command_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELLED_TEXT)


@router.message(Command("import"))
async def command_import(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.set_state(UploadStates.waiting_for_import_file)
    await message.answer(import_instructions(settings.allowed_source_name))


@router.message(Command("lookup_file"))
async def command_lookup_file(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.set_state(UploadStates.waiting_for_lookup_file)
    await message.answer(lookup_file_instructions(settings.max_bulk_numbers))


@router.message(Command("stats"))
async def command_stats(
    message: Message,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    if message.from_user is None:
        return

    async with session_scope(session_factory) as session:
        owner = await UserRepository().get_or_create(session, message.from_user)
        total = await ContactRepository().count_for_owner(
            session=session,
            owner_user_id=owner.id,
            source_name=settings.allowed_source_name,
        )

    await message.answer(stats_text(total, settings.allowed_source_name))


@router.message(UploadStates.waiting_for_import_file, F.document)
async def receive_import_file(
    message: Message,
    bot,
    state: FSMContext,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    import_service: ImportService,
) -> None:
    if message.from_user is None or message.document is None:
        return

    document = message.document
    try:
        await ensure_document_is_allowed(document, settings)
        content = await download_document_bytes(bot, document)
        async with session_scope(session_factory) as session:
            summary = await import_service.import_contacts(
                session=session,
                telegram_user=message.from_user,
                content=content,
                filename=document.file_name or "contacts.csv",
            )
    except ValueError as exc:
        await message.answer(str(exc))
        return

    await state.clear()
    await message.answer(
        import_summary_text(
            processed_rows=summary.processed_rows,
            imported_rows=summary.imported_rows,
            rejected_rows=summary.rejected_rows,
            rejected_preview=summary.rejected_preview,
        )
    )


@router.message(UploadStates.waiting_for_lookup_file, F.document)
async def receive_lookup_file(
    message: Message,
    bot,
    state: FSMContext,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    lookup_service: LookupService,
) -> None:
    if message.from_user is None or message.document is None:
        return

    document = message.document
    try:
        await ensure_document_is_allowed(document, settings)
        content = await download_document_bytes(bot, document)
        parsed = parse_lookup_file(
            content=content,
            filename=document.file_name or "numbers.txt",
            max_rows=settings.max_bulk_numbers,
            default_region=settings.default_region,
        )
    except ValueError as exc:
        await message.answer(str(exc))
        return

    async with session_scope(session_factory) as session:
        results = await lookup_service.lookup_many(
            session=session,
            telegram_user=message.from_user,
            phones=parsed.phones,
        )

    csv_bytes = lookup_service.export_results_csv(results)
    response_file = BufferedInputFile(csv_bytes, filename="lookup_results.csv")

    await state.clear()
    await message.answer(bulk_summary_text(results, rejected_count=len(parsed.rejected_rows)))
    await message.answer_document(response_file)


@router.message(F.document)
async def receive_document_without_state(message: Message) -> None:
    await message.answer(
        "Сначала выберите режим: /import для загрузки разрешённого источника или /lookup_file для пакетной проверки."
    )


@router.message(F.text & ~F.text.startswith("/"))
async def single_number_lookup(
    message: Message,
    settings: Settings,
    session_factory: async_sessionmaker[AsyncSession],
    lookup_service: LookupService,
) -> None:
    if message.from_user is None or message.text is None:
        return

    try:
        phone_e164 = normalize_phone(message.text, settings.default_region)
    except PhoneValidationError:
        await message.answer(UNKNOWN_INPUT_TEXT)
        return

    async with session_scope(session_factory) as session:
        result = await lookup_service.lookup_one(
            session=session,
            telegram_user=message.from_user,
            phone_e164=phone_e164,
        )

    if result.found:
        await message.answer(single_lookup_success(result, settings.allowed_source_name))
    else:
        await message.answer(single_lookup_refusal(result, settings.allowed_source_name))


@router.message()
async def fallback_message(message: Message) -> None:
    await message.answer(UNKNOWN_INPUT_TEXT)


@router.error()
async def on_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled error while processing update", exc_info=event.exception)
    if event.update.message:
        await event.update.message.answer(GENERIC_ERROR_TEXT)
    return True


async def ensure_document_is_allowed(document: Document, settings: Settings) -> None:
    if document.file_size and document.file_size > settings.max_upload_size_bytes:
        raise ValueError(FILE_TOO_LARGE_TEXT)

    extension = detect_extension(document.file_name)
    if extension not in {".csv", ".txt"}:
        raise ValueError("Поддерживаются только .csv и .txt файлы.")
