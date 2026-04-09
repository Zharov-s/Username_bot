from __future__ import annotations

from dataclasses import dataclass

from aiogram.types import User
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.repositories import AuditRepository, ContactRepository, ImportBatchRepository, UserRepository
from app.services.parsers import ImportParseResult, parse_import_contacts_csv


@dataclass(slots=True)
class ImportSummary:
    processed_rows: int
    imported_rows: int
    rejected_rows: int
    rejected_preview: list[str]


class ImportService:
    def __init__(
        self,
        settings: Settings,
        user_repo: UserRepository,
        contact_repo: ContactRepository,
        import_batch_repo: ImportBatchRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.settings = settings
        self.user_repo = user_repo
        self.contact_repo = contact_repo
        self.import_batch_repo = import_batch_repo
        self.audit_repo = audit_repo

    async def import_contacts(
        self,
        session: AsyncSession,
        telegram_user: User,
        content: bytes,
        filename: str,
    ) -> ImportSummary:
        owner = await self.user_repo.get_or_create(session, telegram_user)
        parsed: ImportParseResult = parse_import_contacts_csv(
            content=content,
            filename=filename,
            max_rows=self.settings.max_import_rows,
            default_region=self.settings.default_region,
        )

        prepared_rows = [
            {
                "phone_e164": item.phone_e164,
                "username": item.username,
                "nickname": item.nickname,
            }
            for item in parsed.rows
        ]

        imported_rows = await self.contact_repo.upsert_contacts(
            session=session,
            owner_user_id=owner.id,
            source_name=self.settings.allowed_source_name,
            rows=prepared_rows,
        )

        processed_rows = len(parsed.rows) + len(parsed.rejected_rows)
        rejected_rows = len(parsed.rejected_rows)

        await self.import_batch_repo.create(
            session=session,
            owner_user_id=owner.id,
            source_name=self.settings.allowed_source_name,
            original_filename=filename,
            processed_rows=processed_rows,
            imported_rows=imported_rows,
            rejected_rows=rejected_rows,
        )

        await self.audit_repo.add(
            session=session,
            owner_user_id=owner.id,
            action="import_contacts",
            success=True,
            details={
                "filename": filename,
                "processed_rows": processed_rows,
                "imported_rows": imported_rows,
                "rejected_rows": rejected_rows,
                "source_name": self.settings.allowed_source_name,
            },
        )

        rejected_preview = [
            f"Строка {item.row_number}: {item.reason}"
            for item in parsed.rejected_rows[:10]
        ]

        return ImportSummary(
            processed_rows=processed_rows,
            imported_rows=imported_rows,
            rejected_rows=rejected_rows,
            rejected_preview=rejected_preview,
        )
