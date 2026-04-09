from __future__ import annotations

import json
from typing import Iterable

from aiogram.types import User
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog, BotUser, ConsentStatus, ContactRecord, ImportBatch


class UserRepository:
    async def get_or_create(self, session: AsyncSession, telegram_user: User) -> BotUser:
        query = select(BotUser).where(BotUser.telegram_id == telegram_user.id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        if user is None:
            user = BotUser(
                telegram_id=telegram_user.id,
                telegram_username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )
            session.add(user)
            await session.flush()
            return user

        user.telegram_username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        await session.flush()
        return user


class ContactRepository:
    async def upsert_contacts(
        self,
        session: AsyncSession,
        owner_user_id: int,
        source_name: str,
        rows: list[dict[str, str | None]],
    ) -> int:
        if not rows:
            return 0

        phones = [str(row["phone_e164"]) for row in rows]
        query = select(ContactRecord).where(
            ContactRecord.owner_user_id == owner_user_id,
            ContactRecord.source_name == source_name,
            ContactRecord.phone_e164.in_(phones),
        )
        result = await session.execute(query)
        existing = {record.phone_e164: record for record in result.scalars().all()}

        imported = 0
        for row in rows:
            phone = str(row["phone_e164"])
            record = existing.get(phone)
            if record is None:
                record = ContactRecord(
                    owner_user_id=owner_user_id,
                    source_name=source_name,
                    phone_e164=phone,
                )
                session.add(record)

            record.username = row.get("username")
            record.nickname = row.get("nickname")
            record.consent_status = ConsentStatus.OPT_IN
            imported += 1

        await session.flush()
        return imported

    async def find_consented_by_phone(
        self,
        session: AsyncSession,
        owner_user_id: int,
        source_name: str,
        phone_e164: str,
    ) -> ContactRecord | None:
        query = select(ContactRecord).where(
            ContactRecord.owner_user_id == owner_user_id,
            ContactRecord.source_name == source_name,
            ContactRecord.phone_e164 == phone_e164,
            ContactRecord.consent_status == ConsentStatus.OPT_IN,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def find_consented_by_phones(
        self,
        session: AsyncSession,
        owner_user_id: int,
        source_name: str,
        phone_e164_list: Iterable[str],
    ) -> dict[str, ContactRecord]:
        phones = list(phone_e164_list)
        if not phones:
            return {}

        query = select(ContactRecord).where(
            ContactRecord.owner_user_id == owner_user_id,
            ContactRecord.source_name == source_name,
            ContactRecord.phone_e164.in_(phones),
            ContactRecord.consent_status == ConsentStatus.OPT_IN,
        )
        result = await session.execute(query)
        records = result.scalars().all()
        return {record.phone_e164: record for record in records}

    async def count_for_owner(self, session: AsyncSession, owner_user_id: int, source_name: str) -> int:
        query = select(func.count(ContactRecord.id)).where(
            ContactRecord.owner_user_id == owner_user_id,
            ContactRecord.source_name == source_name,
            ContactRecord.consent_status == ConsentStatus.OPT_IN,
        )
        result = await session.execute(query)
        return int(result.scalar_one())


class ImportBatchRepository:
    async def create(
        self,
        session: AsyncSession,
        owner_user_id: int,
        source_name: str,
        original_filename: str,
        processed_rows: int,
        imported_rows: int,
        rejected_rows: int,
    ) -> ImportBatch:
        batch = ImportBatch(
            owner_user_id=owner_user_id,
            source_name=source_name,
            original_filename=original_filename,
            processed_rows=processed_rows,
            imported_rows=imported_rows,
            rejected_rows=rejected_rows,
        )
        session.add(batch)
        await session.flush()
        return batch


class AuditRepository:
    async def add(
        self,
        session: AsyncSession,
        owner_user_id: int,
        action: str,
        success: bool,
        target_hash: str | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        payload = json.dumps(details, ensure_ascii=False, sort_keys=True) if details is not None else None
        log = AuditLog(
            owner_user_id=owner_user_id,
            action=action,
            success=success,
            target_hash=target_hash,
            details_json=payload,
        )
        session.add(log)
        await session.flush()
        return log
