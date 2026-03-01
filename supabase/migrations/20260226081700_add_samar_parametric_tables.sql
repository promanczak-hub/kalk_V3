-- Table: samar_classes
-- Describes each SAMAR class and its independent configurable parameters

CREATE TABLE public.samar_classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    mileage_cutoff_threshold INTEGER NOT NULL DEFAULT 190000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: samar_class_depreciation_rates
-- Defines depreciation percentage per year for base vehicle and for options
CREATE TABLE public.samar_class_depreciation_rates (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    fuel_type_id INTEGER NOT NULL, -- 1=Petrol, 2=Diesel, 3=EV/PHEV
    year INTEGER NOT NULL, -- e.g. 0, 1, 2, 3...
    base_depreciation_percent DECIMAL(5, 4) NOT NULL DEFAULT 0.0000, -- e.g. 0.0800 for 8%
    options_depreciation_percent DECIMAL(5, 4) NOT NULL DEFAULT 0.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(samar_class_id, fuel_type_id, year)
);

-- Table: samar_class_mileage_corrections
-- Defines the correction multipliers below and above the threshold
CREATE TABLE public.samar_class_mileage_corrections (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    fuel_type_id INTEGER NOT NULL,
    under_threshold_percent DECIMAL(6, 5) NOT NULL DEFAULT 0.00000,
    over_threshold_percent DECIMAL(6, 5) NOT NULL DEFAULT 0.00000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(samar_class_id, fuel_type_id)
);

-- Table: paint_types
-- E.g. Base, Metallic, Pearl
CREATE TABLE public.paint_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: paint_parsing_rules
-- Keywords or regexes to map Gemini text to a PaintType
CREATE TABLE public.paint_parsing_rules (
    id SERIAL PRIMARY KEY,
    paint_type_id INTEGER NOT NULL REFERENCES public.paint_types(id) ON DELETE CASCADE,
    keyword_regex VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Table: samar_class_paint_adjustments
-- Configurable impact (+/-) of a paint type on the RV for a given Samar Class
CREATE TABLE public.samar_class_paint_adjustments (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    paint_type_id INTEGER NOT NULL REFERENCES public.paint_types(id) ON DELETE CASCADE,
    adjustment_percent DECIMAL(5, 4) NOT NULL DEFAULT 0.0000, -- e.g. 0.0150 for +1.5%
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(samar_class_id, paint_type_id)
);

-- Insert Default Paint Types
INSERT INTO public.paint_types (name) VALUES 
('Niemetalizowany (Bazowy)'),
('Metalizowany (Metalik)'),
('Perłowy');

-- Insert common rules mappings
INSERT INTO public.paint_parsing_rules (paint_type_id, keyword_regex) VALUES 
((SELECT id FROM public.paint_types WHERE name = 'Metalizowany (Metalik)'), '(?i)metal(ik|lic|izowany)'),
((SELECT id FROM public.paint_types WHERE name = 'Perłowy'), '(?i)perł(ow[y|a]|a)');

