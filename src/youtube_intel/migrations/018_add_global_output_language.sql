-- V1 M8: one persisted global preferred output language.
-- YAML/config remains the bootstrap default only when no explicit user preference exists.

CREATE TABLE global_user_settings (
    settings_key TEXT PRIMARY KEY NOT NULL CHECK (settings_key = 'global'),
    output_language TEXT NOT NULL CHECK (output_language IN ('zh-CN', 'en')),
    updated_at TEXT NOT NULL
);
