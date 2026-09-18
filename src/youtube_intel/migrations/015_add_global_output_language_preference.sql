-- M8A: one explicit global user output-language preference.
-- The YAML/config general.output_language remains the bootstrap/default.
-- Historical generated artifacts keep their recorded generation-time language.

CREATE TABLE global_output_language_preferences (
    preference_key TEXT PRIMARY KEY CHECK (preference_key = 'global'),
    output_language TEXT NOT NULL CHECK (output_language IN ('zh-CN', 'en')),
    updated_at TEXT NOT NULL
);
