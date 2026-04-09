from __future__ import annotations

import asyncio
import logging

from app.bot import create_bot, create_dispatcher, set_bot_commands
from app.config import get_settings
from app.db.repositories import AuditRepository, ContactRepository, ImportBatchRepository, UserRepository
from app.db.session import create_engine_from_settings, create_session_factory, init_db
from app.logging_config import setup_logging
from app.services.import_service import ImportService
from app.services.lookup_service import LookupService

logger = logging.getLogger(__name__)


async def async_main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    engine = create_engine_from_settings(settings)
    session_factory = create_session_factory(engine)
    await init_db(engine)

    user_repo = UserRepository()
    contact_repo = ContactRepository()
    import_batch_repo = ImportBatchRepository()
    audit_repo = AuditRepository()

    import_service = ImportService(
        settings=settings,
        user_repo=user_repo,
        contact_repo=contact_repo,
        import_batch_repo=import_batch_repo,
        audit_repo=audit_repo,
    )
    lookup_service = LookupService(
        settings=settings,
        user_repo=user_repo,
        contact_repo=contact_repo,
        audit_repo=audit_repo,
    )

    bot = create_bot(settings)
    dp = create_dispatcher(settings)
    await bot.delete_webhook(drop_pending_updates=True)
    await set_bot_commands(bot)

    logger.info("Bot started in polling mode")
    try:
        await dp.start_polling(
            bot,
            settings=settings,
            session_factory=session_factory,
            import_service=import_service,
            lookup_service=lookup_service,
        )
    finally:
        await bot.session.close()
        await engine.dispose()


def run() -> None:
    asyncio.run(async_main())
