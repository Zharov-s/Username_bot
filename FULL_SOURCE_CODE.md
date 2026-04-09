# Full source code

## `.env.example`
```
BOT_TOKEN=<токен от @BotFather>
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/legal_username_bot
LOG_LEVEL=INFO

# Только этот разрешённый источник данных используется для поиска
ALLOWED_SOURCE_NAME=ваш разрешённый CSV-источник с opt-in

# Ограничения и privacy-настройки
BOT_RATE_LIMIT_PER_MINUTE=20
MAX_BULK_NUMBERS=200
MAX_IMPORT_ROWS=5000
MAX_UPLOAD_SIZE_BYTES=2000000
DEFAULT_REGION=RU
PRIVACY_CONTACT_EMAIL=privacy@example.com

```

## `README.md`
```markdown
# Legal Username Lookup Bot

Production-ready Telegram-бот на Python `3.11+` для **законной** обработки телефонных номеров с возвратом только тех `username` / `nickname`, которые доступны в разрешённом источнике данных.

## Что делает этот бот

Бот:

- ищет данные **только** в источнике `ваш разрешённый CSV-источник с opt-in`;
- работает только с вашими собственными данными и записями с подтверждённым `opt-in`;
- умеет импортировать ваш CSV-список;
- умеет принимать один номер или список номеров;
- отдаёт только `username` / `nickname`, которые уже есть в разрешённом источнике;
- не делает скрытый поиск, не скрапит сайты, не занимается OSINT и deanonymization.

## Что бот не делает

Бот **не**:

- не ищет данные о посторонних людях;
- не обходит настройки приватности Telegram;
- не достаёт username из чужих адресных книг, слитых баз, парсеров, серых API и неавторизованных CRM;
- не раскрывает информацию без подтверждённого права на обработку.

---

## Архитектура проекта

```text
legal_username_bot/
├── .env.example
├── README.md
├── requirements.txt
├── run.py
├── schema.sql
├── samples/
│   ├── contacts_import.csv
│   └── lookup_numbers.txt
└── app/
    ├── __init__.py
    ├── bot.py
    ├── config.py
    ├── logging_config.py
    ├── main.py
    ├── db/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── models.py
    │   ├── repositories.py
    │   └── session.py
    ├── services/
    │   ├── __init__.py
    │   ├── import_service.py
    │   ├── lookup_service.py
    │   ├── parsers.py
    │   └── rate_limit.py
    ├── telegram/
    │   ├── __init__.py
    │   ├── handlers.py
    │   ├── messages.py
    │   └── states.py
    └── utils/
        ├── __init__.py
        ├── files.py
        ├── phone.py
        └── security.py
```

### Как работают модули

#### `app/config.py`
Читает настройки из `.env`.

#### `app/logging_config.py`
Включает консольное логирование.

#### `app/db/models.py`
Модели БД:
- `BotUser` — владелец данных и пользователь бота;
- `ContactRecord` — разрешённые контакты с `phone_e164`, `username`, `nickname`, `consent_status`;
- `ImportBatch` — журнал импортов;
- `AuditLog` — журнал операций без хранения лишних персональных данных.

#### `app/db/repositories.py`
Слой доступа к БД:
- создание/обновление пользователя;
- upsert контактов;
- поиск одного и многих номеров;
- подсчёт записей;
- аудит.

#### `app/services/parsers.py`
Безопасный разбор файлов:
- CSV импорта разрешённого источника;
- TXT/CSV для пакетного lookup;
- нормализация кодировок;
- проверка лимитов.

#### `app/services/import_service.py`
Импортирует ваш CSV только если:
- номер валиден;
- есть `opt_in`;
- есть хотя бы `username` или `nickname`.

#### `app/services/lookup_service.py`
Ищет только по разрешённому источнику `ваш разрешённый CSV-источник с opt-in` в рамках данных **конкретного пользователя бота**.  
То есть пользователь А не может получить записи пользователя Б.

#### `app/services/rate_limit.py`
In-memory rate limiting на пользователя.

#### `app/telegram/handlers.py`
Команды и сообщения:
- `/start`
- `/help`
- `/import`
- `/lookup_file`
- `/stats`
- `/cancel`
- обычное текстовое сообщение с одним номером

#### `app/utils/phone.py`
Валидация и нормализация номеров через `phonenumbers`.

#### `app/utils/security.py`
SHA-256 хеш для аудита вместо хранения номера в логе.

---

## Команды бота

### `/start`
Показывает приветствие и ограничения.

### `/help`
Показывает справку.

### `/import`
Переводит бота в режим загрузки CSV-источника.

### `/lookup_file`
Переводит бота в режим загрузки списка номеров для пакетной проверки.

### `/stats`
Показывает, сколько записей с `opt-in` у вас доступно.

### `/cancel`
Сбрасывает текущий режим.

### Обычный текст с номером
Если вы отправляете один номер телефона, бот:
1. валидирует его,
2. нормализует в E.164,
3. ищет совпадение только в разрешённом источнике,
4. возвращает найденный `username` / `nickname`, либо вежливый отказ.

---

## Форматы данных

## 1) Импорт разрешённого источника

Команда: `/import`

Поддерживается CSV с заголовками.

Обязательная колонка:
- `phone`

Необязательные:
- `username`
- `nickname`
- `consent_status`

Пример:

```csv
phone,username,nickname,consent_status
+79991234567,ivan_petrov,Иван Петров,opt_in
+447700900123,maria_data,Мария,opt_in
+12025550123,,Support Team,opt_in
```

Правила:
- импортируются только строки с `consent_status=opt_in`;
- если `username` и `nickname` пустые — строка отклоняется;
- если номер некорректен — строка отклоняется;
- дубликаты по номеру внутри файла схлопываются;
- исходный файл не хранится.

## 2) Пакетная проверка номеров

Команда: `/lookup_file`

Поддерживается:
- `.txt` — один номер в строке;
- `.csv` — колонка `phone` или номер в первом столбце.

Пример TXT:

```txt
+79991234567
+447700900123
+12025550123
```

---

## Логика безопасности

1. Поиск идёт **только** по `ваш разрешённый CSV-источник с opt-in`.
2. Бот хранит только необходимое:
   - нормализованный номер,
   - username/nickname,
   - статус согласия,
   - технический аудит.
3. В аудит пишется хеш номера, а не номер в открытом виде.
4. Без `opt-in` результат не возвращается.
5. Нет внешнего парсинга, скрытых API, OSINT или deanonymization.
6. Данные из одного Telegram-пользователя не доступны другому.
7. Неподдерживаемые или слишком большие файлы отклоняются.
8. Есть rate limiting и централизованная обработка ошибок.

---

## Пошаговый запуск с нуля на `macOS/Linux или VPS`

### Шаг 1. Установите Python `3.11+`
Проверьте:

```bash
python --version
```

или

```bash
python3 --version
```

### Шаг 2. Создайте Telegram-бота через BotFather

1. Откройте Telegram.
2. Найдите `@BotFather`.
3. Отправьте команду `/newbot`.
4. Укажите имя бота.
5. Укажите username бота, который оканчивается на `bot`.
6. BotFather пришлёт токен.

Этот токен и есть значение для:

```env
BOT_TOKEN=<токен от @BotFather>
```

### Шаг 3. Скопируйте проект

```bash
git clone <ваш_репозиторий_или_папка_с_проектом>
cd legal_username_bot
```

Если вы просто распаковали архив:

```bash
cd legal_username_bot
```

### Шаг 4. Создайте виртуальное окружение

```bash
python -m venv .venv
```

Активируйте его.

На Windows:

```bash
.venv\Scripts\activate
```

На macOS/Linux:

```bash
source .venv/bin/activate
```

### Шаг 5. Установите зависимости

```bash
pip install -r requirements.txt
```

### Шаг 6. Подготовьте `.env`

Скопируйте пример:

```bash
cp .env.example .env
```

На Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Откройте `.env` и заполните значения:

```env
BOT_TOKEN=<токен от @BotFather>
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/legal_username_bot
LOG_LEVEL=INFO
ALLOWED_SOURCE_NAME=ваш разрешённый CSV-источник с opt-in
BOT_RATE_LIMIT_PER_MINUTE=20
MAX_BULK_NUMBERS=200
MAX_IMPORT_ROWS=5000
MAX_UPLOAD_SIZE_BYTES=2000000
DEFAULT_REGION=RU
PRIVACY_CONTACT_EMAIL=privacy@example.com
```

### Шаг 7. Создайте и настройте БД

Бот использует SQLAlchemy и умеет сам создать таблицы при первом запуске.

Вам нужно только:
1. установить и запустить вашу `PostgreSQL`,
2. создать пустую базу,
3. указать её URL в `DATABASE_URL`.

После старта бота таблицы создадутся автоматически.

### Шаг 8. Запустите бота вручную из терминала

```bash
python run.py
```

Если всё заполнено правильно, бот стартует в polling-режиме.

### Шаг 9. Проверьте, что бот работает

1. Откройте Telegram.
2. Найдите своего бота.
3. Нажмите `Start` или отправьте `/start`.
4. Должно прийти приветственное сообщение.

### Шаг 10. Протестируйте импорт разрешённого источника

1. Отправьте команду `/import`.
2. Прикрепите файл `samples/contacts_import.csv`.
3. Бот должен сообщить:
   - сколько строк обработано,
   - сколько импортировано,
   - сколько отклонено.

### Шаг 11. Протестируйте один номер

После импорта отправьте сообщением:

```text
+79991234567
```

Ожидаемый ответ:

```text
Результат для +79991234567
username: @ivan_petrov
nickname: Иван Петров
источник: ваш разрешённый CSV-источник с opt-in
```

### Шаг 12. Протестируйте список номеров

1. Отправьте `/lookup_file`
2. Прикрепите `samples/lookup_numbers.txt`

Бот:
- покажет сводку;
- отправит CSV с результатами.

---

## Ожидаемый диалог с ботом

### Сценарий 1. Первый запуск

**Пользователь:**
```text
/start
```

**Бот:**
```text
Здравствуйте. Это privacy-safe бот для законной обработки номеров телефонов.
Я ищу данные только в разрешённом источнике: ваш разрешённый CSV-источник с opt-in.
...
```

### Сценарий 2. Импорт источника

**Пользователь:**
```text
/import
```

**Бот:**
```text
Загрузите CSV-файл для источника ваш разрешённый CSV-источник с opt-in.
```

**Пользователь:**
`прикрепляет contacts_import.csv`

**Бот:**
```text
Импорт завершён
Обработано строк: 5
Импортировано/обновлено: 3
Отклонено: 2
```

### Сценарий 3. Один номер

**Пользователь:**
```text
+447700900123
```

**Бот:**
```text
Результат для +447700900123
username: @maria_data
nickname: Мария
источник: ваш разрешённый CSV-источник с opt-in
```

### Сценарий 4. Номер без законного результата

**Пользователь:**
```text
+79990000000
```

**Бот:**
```text
Результат для +79990000000
Нет доступного результата в разрешённом источнике или нет подтверждённого opt-in.
Поиск выполняется только в разрешённом источнике ваш разрешённый CSV-источник с opt-in.
```

---

## Типичные ошибки и как исправить

### Ошибка: бот не запускается
Проверьте:
- заполнен ли `BOT_TOKEN`;
- правильно ли указан `DATABASE_URL`;
- установлены ли зависимости;
- активировано ли виртуальное окружение.

### Ошибка: `Unauthorized`
Токен бота неверный. Скопируйте новый токен из BotFather.

### Ошибка подключения к БД
Проверьте:
- запущена ли ваша `PostgreSQL`;
- существует ли база;
- верный ли логин, пароль, порт, хост в `DATABASE_URL`.

### Бот не отвечает на сообщения
Проверьте:
- процесс всё ещё работает;
- бот не запущен второй копией одновременно;
- токен не используется другим приложением в polling-режиме.

### Импорт отклоняет строки
Проверьте:
- колонку `phone`;
- корректность номера;
- `consent_status=opt_in`;
- наличие `username` или `nickname`.

### Файл не принимается
Проверьте:
- расширение `.csv` или `.txt`;
- размер файла;
- кодировку UTF-8 или CP1251.

---

## Полный исходный код файлов

Ниже перечислены ключевые файлы проекта. Полный код уже находится в проекте:

- `run.py`
- `requirements.txt`
- `.env.example`
- `schema.sql`
- все файлы внутри `app/`
- тестовые примеры в `samples/`

Вы можете просто скопировать проект целиком и запускать.

---

## Ограничения и законное использование

Этот бот предназначен **только** для законной обработки номеров, на которые у вас есть право обработки и подтверждённое основание.

Прямые ограничения:

- бот не предназначен для поиска данных о посторонних людях;
- используйте только номера, на обработку которых у вас есть право и согласие;
- запрещены скрытый сбор данных, OSINT-скрапинг и deanonymization;
- запрещено использовать слитые базы, серые API, неавторизованные CRM и парсеры;
- если номер нельзя обработать легально и подтверждённо, бот обязан отказать.

---

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

После этого:
1. `/start`
2. `/import`
3. загрузите `samples/contacts_import.csv`
4. отправьте один номер или `/lookup_file`

Готово.

```

## `app/__init__.py`
```python

```

## `app/bot.py`
```python
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import Settings
from app.services.rate_limit import InMemoryRateLimiter, RateLimitMiddleware
from app.telegram.handlers import router


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(settings: Settings) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    limiter = InMemoryRateLimiter(limit_per_minute=settings.bot_rate_limit_per_minute)
    dp.message.middleware(RateLimitMiddleware(limiter))
    dp.include_router(router)
    return dp


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Запуск и краткая справка"),
        BotCommand(command="help", description="Подробная инструкция"),
        BotCommand(command="import", description="Импорт своего CSV-источника"),
        BotCommand(command="lookup_file", description="Проверка списка номеров"),
        BotCommand(command="stats", description="Статистика разрешённого источника"),
        BotCommand(command="cancel", description="Отменить текущий режим"),
    ]
    await bot.set_my_commands(commands)

```

## `app/config.py`
```python
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    database_url: str = Field(alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    allowed_source_name: str = Field(
        default="ваш разрешённый CSV-источник с opt-in",
        alias="ALLOWED_SOURCE_NAME",
    )

    bot_rate_limit_per_minute: int = Field(default=20, alias="BOT_RATE_LIMIT_PER_MINUTE")
    max_bulk_numbers: int = Field(default=200, alias="MAX_BULK_NUMBERS")
    max_import_rows: int = Field(default=5000, alias="MAX_IMPORT_ROWS")
    max_upload_size_bytes: int = Field(default=2_000_000, alias="MAX_UPLOAD_SIZE_BYTES")
    default_region: str = Field(default="RU", alias="DEFAULT_REGION")
    privacy_contact_email: str = Field(default="privacy@example.com", alias="PRIVACY_CONTACT_EMAIL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

```

## `app/db/__init__.py`
```python

```

## `app/db/base.py`
```python
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(AsyncAttrs, DeclarativeBase):
    pass

```

## `app/db/models.py`
```python
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import BigInteger, DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utcnow


class ConsentStatus(str, Enum):
    OPT_IN = "opt_in"
    NO_CONSENT = "no_consent"
    REVOKED = "revoked"


class BotUser(Base):
    __tablename__ = "bot_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    contacts: Mapped[list["ContactRecord"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    imports: Mapped[list["ImportBatch"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class ContactRecord(Base):
    __tablename__ = "contact_records"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "source_name", "phone_e164", name="uq_contact_owner_source_phone"),
        Index("ix_contact_owner_source_phone", "owner_user_id", "source_name", "phone_e164"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_name: Mapped[str] = mapped_column(String(255), index=True)
    phone_e164: Mapped[str] = mapped_column(String(32), index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consent_status: Mapped[ConsentStatus] = mapped_column(
        SQLEnum(ConsentStatus, name="consent_status", native_enum=False, length=32),
        default=ConsentStatus.OPT_IN,
    )
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped["BotUser"] = relationship(back_populates="contacts")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    source_name: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["BotUser"] = relationship(back_populates="imports")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_owner_action_created", "owner_user_id", "action", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("bot_users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(64), index=True)
    success: Mapped[bool] = mapped_column(default=True)
    target_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped["BotUser"] = relationship(back_populates="audit_logs")

```

## `app/db/repositories.py`
```python
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

```

## `app/db/session.py`
```python
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.db.base import Base


def create_engine_from_settings(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        future=True,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()

```

## `app/logging_config.py`
```python
from __future__ import annotations

import logging
from logging.config import dictConfig


def setup_logging(level: str = "INFO") -> None:
    normalized = level.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": normalized,
                    "formatter": "standard",
                }
            },
            "root": {"handlers": ["console"], "level": normalized},
        }
    )
    logging.getLogger(__name__).info("Logging initialized with level=%s", normalized)

```

## `app/main.py`
```python
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

```

## `app/services/__init__.py`
```python

```

## `app/services/import_service.py`
```python
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

```

## `app/services/lookup_service.py`
```python
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

```

## `app/services/parsers.py`
```python
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

```

## `app/services/rate_limit.py`
```python
from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self.limit_per_minute = limit_per_minute
        self.window_seconds = 60.0
        self._events: dict[int, deque[float]] = defaultdict(deque)
        self._locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def allow(self, key: int) -> tuple[bool, int]:
        async with self._locks[key]:
            now = monotonic()
            bucket = self._events[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()

            if len(bucket) >= self.limit_per_minute:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limiter: InMemoryRateLimiter) -> None:
        super().__init__()
        self.limiter = limiter

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        allowed, retry_after = await self.limiter.allow(event.from_user.id)
        if not allowed:
            await event.answer(
                f"Слишком много запросов. Подождите примерно {retry_after} сек. и попробуйте снова."
            )
            return None

        return await handler(event, data)

```

## `app/telegram/__init__.py`
```python

```

## `app/telegram/handlers.py`
```python
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

```

## `app/telegram/messages.py`
```python
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

```

## `app/telegram/states.py`
```python
from aiogram.fsm.state import State, StatesGroup


class UploadStates(StatesGroup):
    waiting_for_import_file = State()
    waiting_for_lookup_file = State()

```

## `app/utils/__init__.py`
```python

```

## `app/utils/files.py`
```python
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

```

## `app/utils/phone.py`
```python
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

```

## `app/utils/security.py`
```python
from __future__ import annotations

import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

```

## `requirements.txt`
```text
aiogram>=3.20,<4.0
SQLAlchemy>=2.0,<3.0
pydantic>=2.7,<3.0
pydantic-settings>=2.2,<3.0
phonenumbers>=8.13,<9.0
python-dotenv>=1.0,<2.0
aiosqlite>=0.20,<1.0
asyncpg>=0.29,<1.0

```

## `run.py`
```python
from app.main import run

if __name__ == "__main__":
    run()

```

## `samples/contacts_import.csv`
```csv
phone,username,nickname,consent_status
+79991234567,ivan_petrov,Иван Петров,opt_in
+447700900123,maria_data,Мария,opt_in
+12025550123,,Support Team,opt_in
+79990000000,hidden_user,Без согласия,no
bad_phone,baduser,Некорректный,opt_in

```

## `samples/lookup_numbers.txt`
```text
+79991234567
+447700900123
+12025550123
+79990000000
+79995554433

```

## `schema.sql`
```sql
-- Справочная SQL-схема. В реальном запуске таблицы создаются автоматически через SQLAlchemy.
CREATE TABLE bot_users (
    id INTEGER PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    telegram_username VARCHAR(64),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE contact_records (
    id INTEGER PRIMARY KEY,
    owner_user_id INTEGER NOT NULL REFERENCES bot_users(id) ON DELETE CASCADE,
    source_name VARCHAR(255) NOT NULL,
    phone_e164 VARCHAR(32) NOT NULL,
    username VARCHAR(64),
    nickname VARCHAR(255),
    consent_status VARCHAR(32) NOT NULL,
    imported_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT uq_contact_owner_source_phone UNIQUE (owner_user_id, source_name, phone_e164)
);

CREATE INDEX ix_contact_owner_source_phone
    ON contact_records(owner_user_id, source_name, phone_e164);

CREATE TABLE import_batches (
    id INTEGER PRIMARY KEY,
    owner_user_id INTEGER NOT NULL REFERENCES bot_users(id) ON DELETE CASCADE,
    source_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    processed_rows INTEGER NOT NULL DEFAULT 0,
    imported_rows INTEGER NOT NULL DEFAULT 0,
    rejected_rows INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    owner_user_id INTEGER NOT NULL REFERENCES bot_users(id) ON DELETE CASCADE,
    action VARCHAR(64) NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    target_hash VARCHAR(128),
    details_json TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX ix_audit_owner_action_created
    ON audit_logs(owner_user_id, action, created_at);

```
