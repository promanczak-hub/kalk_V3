-- 1. v1_admin_ubezpieczenie
CREATE TABLE public.v1_admin_ubezpieczenie (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    kolejny_rok INT NOT NULL,
    stawka_bazowa_ac NUMERIC NOT NULL,
    skladka_oc_wartosc NUMERIC NOT NULL,
    klasa_samar TEXT NOT NULL
);

-- Index for fast lookup by class and year
CREATE INDEX idx_v1_admin_ubezpieczenie_klasa_rok ON public.v1_admin_ubezpieczenie(klasa_samar, kolejny_rok);

-- 2. v1_admin_parametry
CREATE TABLE public.v1_admin_parametry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    nazwa TEXT NOT NULL UNIQUE,
    wartosc NUMERIC NOT NULL
);

-- 3. ubezpieczenie_wspolczynniki_szkodowe
CREATE TABLE public.ubezpieczenie_wspolczynniki_szkodowe (
    klasa_samar TEXT PRIMARY KEY,
    wspolczynnik_szkodowy NUMERIC NOT NULL
);
