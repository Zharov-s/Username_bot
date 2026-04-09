from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from aiogram.types import User
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import ContactRecord
from app.db.repositories import AuditRepository, ContactRepository, UserRepository
from app.utils.security import sha256_hex


@dataclass(slots=True)
class LookupResult:
    phone_e164: str
    found: bool
    username: str | None = None
    nickname: str | None = None
    reason: str | None = None


class LookupService:
    def __init__(
        self,
        settings: Settings,
        user_repo: UserRepository,
        contact_repo: ContactRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self.settings = settings
        self.user_repo = user_repo
        self.contact_repo = contact_repo
        self.audit_repo = audit_repo

    async def lookup_one(
        self,
        session: AsyncSession,
        telegram_user: User,
        phone_e164: str,
    ) -> LookupResult:
        owner = await self.user_repo.get_or_create(session, telegram_user)
        record = await self.contact_repo.find_consented_by_phone(
            session=session,
            owner_user_id=owner.id,
            source_name=self.settings.allowed_source_name,
            phone_e164=phone_e164,
        )

        result = self._build_result(phone_e164, record)
        await self.audit_repo.add(
            session=session,
            owner_user_id=owner.id,
            action="lookup_one",
            success=result.found,
            target_hash=sha256_hex(phone_e164),
            details={
                "source_name": self.settings.allowed_source_name,
                "found": result.found,
            },
        )
        return result

    async def lookup_many(
        self,
        session: AsyncSession,
        telegram_user: User,
        phones: list[str],
    ) -> list[LookupResult]:
        owner = await self.user_repo.get_or_create(session, telegram_user)
        found_records = await self.contact_repo.find_consented_by_phones(
            session=session,
            owner_user_id=owner.id,
            source_name=self.settings.allowed_source_name,
            phone_e164_list=phones,
        )

        results = [self._build_result(phone, found_records.get(phone)) for phone in phones]

        await self.audit_repo.add(
            session=session,
            owner_user_id=owner.id,
            action="lookup_many",
            success=True,
            details={
                "source_name": self.settings.allowed_source_name,
                "requested": len(phones),
                "found": sum(1 for item in results if item.found),
            },
        )
        return results

    def export_results_csv(self, results: list[LookupResult]) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=["phone_e164", "status", "username", "nickname", "note"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "phone_e164": result.phone_e164,
                    "status": "found" if result.found else "not_found_or_not_permitted",
                    "username": f"@{result.username}" if result.username else "",
                    "nickname": result.nickname or "",
                    "note": result.reason or "",
                }
            )
        return buffer.getvalue().encode("utf-8-sig")

    @staticmethod
    def _build_result(phone_e164: str, record: ContactRecord | None) -> LookupResult:
        if record and (record.username or record.nickname):
            return LookupResult(
                phone_e164=phone_e164,
                found=True,
                username=record.username,
                nickname=record.nickname,
            )

        return LookupResult(
            phone_e164=phone_e164,
            found=False,
            reason="Нет доступного результата в разрешённом источнике или нет подтверждённого opt-in.",
        )
