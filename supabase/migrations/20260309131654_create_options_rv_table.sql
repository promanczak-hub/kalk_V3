-- Monolit 2: Utrata Wartości Opcji Fabrycznych (lata 0-7)
-- Tabela: samar_class_options_rv
-- Klucz: samar_class_id + engine_type_id + year

CREATE TABLE IF NOT EXISTS samar_class_options_rv (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES samar_classes(id) ON DELETE CASCADE,
    engine_type_id INTEGER NOT NULL REFERENCES engines(id) ON DELETE CASCADE,
    year INTEGER NOT NULL CHECK (year >= 0 AND year <= 7),
    options_rv_percent NUMERIC(6,4) NOT NULL DEFAULT 0,
    UNIQUE(samar_class_id, engine_type_id, year)
);

INSERT INTO samar_class_options_rv (samar_class_id, engine_type_id, year, options_rv_percent)
VALUES

ON CONFLICT (samar_class_id, engine_type_id, year) DO UPDATE SET options_rv_percent = EXCLUDED.options_rv_percent;
