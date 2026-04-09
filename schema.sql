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
