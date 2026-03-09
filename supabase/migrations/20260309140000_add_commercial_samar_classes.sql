-- Migration: Add missing commercial SAMAR classes + remove Kempingowe + populate example_models
-- Source: Segmentacja rynku SAMAR 202510 PDF

-- ═══════════════════════════════════════════════════════════════
-- 1. Remove Kempingowe (user request)
-- ═══════════════════════════════════════════════════════════════
DELETE FROM samar_classes WHERE name = 'Kempingowe - K KEMPINGOWE';

-- ═══════════════════════════════════════════════════════════════
-- 2. Add 6 missing commercial vehicle classes
-- ═══════════════════════════════════════════════════════════════
INSERT INTO samar_classes (name, category, size_class, excel_code, example_models, description)
VALUES
  (
    'Lekkie dostawcze - KOMBI VAN',
    'LEKKIE DOSTAWCZE',
    'KOMBI VAN',
    'Mvan',
    'VW Caddy, Renault Kangoo Van, Peugeot Partner, Ford Transit Connect, Citroen Berlingo, Toyota Proace City, Opel Combo Van, Mercedes Citan, Nissan Townstar, Fiat Doblo',
    'Samochody dostawcze lekkie w nadwoziu kombi-van'
  ),
  (
    'Lekkie dostawcze - VAN',
    'LEKKIE DOSTAWCZE',
    'VAN',
    NULL,
    'Opel Corsa Van, Peugeot 208 Van, Dacia Spring Cargo, Citroen C3 Van, Ford Transit Courier, Renault Clio Societe, Kia Niro Van',
    'Samochody dostawcze lekkie w nadwoziu van (mniejsze)'
  ),
  (
    'Pick-up - PICK-UP',
    'PICK-UP',
    'PICK-UP',
    'T PICK-UP',
    'Ford Ranger, Toyota Hilux, Volkswagen Amarok, Isuzu D-Max, Ssangyong/KGM Musso Grand, Maxus T60 Max, JAC T8 Pro, JAC T9, Foton Tunland',
    'Samochody typu pick-up'
  ),
  (
    'Średnie dostawcze - ŚREDNIE DOSTAWCZE',
    'ŚREDNIE DOSTAWCZE',
    'ŚREDNIE DOSTAWCZE',
    'P',
    'VW Transporter, Mercedes Vito, Ford Transit Custom, Opel Vivaro, Renault Trafic, Peugeot Expert, Citroen Jumpy, Toyota Proace, Fiat Scudo, Nissan Primastar, VW ID.Buzz',
    'Samochody dostawcze średniej wielkości'
  ),
  (
    'Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE',
    'CIĘŻKIE DOSTAWCZE',
    'CIĘŻKIE DOSTAWCZE',
    'Pciez',
    'VW Crafter, Mercedes Sprinter, Iveco Daily, Fiat Ducato, Ford Transit, Opel Movano, Peugeot Boxer, Renault Master, Man TGE, Citroen Jumper, Toyota Proace Max',
    'Samochody dostawcze ciężkie (do 6T)'
  ),
  (
    'Autobusy - AUTOBUSY',
    'AUTOBUSY',
    'AUTOBUSY',
    NULL,
    'Ford Transit, Iveco Daily, Mercedes Sprinter, Opel Movano, Peugeot Boxer, Renault Master, VW Crafter, Man TGE, Karsan Jest',
    'Autobusy do 6T'
  )
ON CONFLICT (name) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════
-- 3. Populate example_models for existing passenger car classes
--    (from SAMAR PDF 202510)
-- ═══════════════════════════════════════════════════════════════

-- Podstawowa - A MINI
UPDATE samar_classes SET example_models = 'Fiat 500, Toyota Aygo X, Citroen C1 / Ami, Hyundai i10, Kia Picanto, VW up!, Smart #1, Dacia Spring, Suzuki Ignis'
WHERE name = 'Podstawowa - A MINI' AND (example_models IS NULL OR example_models = '');

-- Podstawowa - B MAŁE
UPDATE samar_classes SET example_models = 'VW Polo, Toyota Yaris, Skoda Fabia, Opel Corsa, Hyundai i20, Kia Rio, Peugeot 208, Renault Clio, Ford Fiesta, Mazda 2, Seat Ibiza, Citroen C3'
WHERE name = 'Podstawowa - B MAŁE' AND (example_models IS NULL OR example_models = '');

-- Podstawowa - C NIŻSZA ŚREDNIA
UPDATE samar_classes SET example_models = 'VW Golf, Toyota Corolla, Skoda Octavia, Hyundai i30, Kia Ceed, Opel Astra, Peugeot 308, Ford Focus, Mazda 3, Seat Leon, Citroen C4, Renault Megane'
WHERE name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND (example_models IS NULL OR example_models = '');

-- Podstawowa - D ŚREDNIA
UPDATE samar_classes SET example_models = 'VW Passat, Toyota Camry, Skoda Superb, BMW 3, Mercedes C, Audi A4, Peugeot 508, Opel Insignia, Ford Mondeo, Volvo S60/V60'
WHERE name = 'Podstawowa - D ŚREDNIA' AND (example_models IS NULL OR example_models = '');

-- Podstawowa - E WYŻSZA
UPDATE samar_classes SET example_models = 'BMW 5, Mercedes E, Audi A6, Volvo S90/V90, Lexus ES, BMW i5, Mercedes EQE'
WHERE name = 'Podstawowa - E WYŻSZA' AND (example_models IS NULL OR example_models = '');

-- Podstawowa - F LUKSUSOWE
UPDATE samar_classes SET example_models = 'BMW 7, Mercedes S, Audi A8, Porsche Panamera, Lexus LS, Maserati Quattroporte'
WHERE name = 'Podstawowa - F LUKSUSOWE' AND (example_models IS NULL OR example_models = '');

-- Podstawowa - G SUPER LUKSUSOWE
UPDATE samar_classes SET example_models = 'Rolls-Royce Ghost, Bentley Flying Spur, Mercedes Maybach S, BMW i7'
WHERE name = 'Podstawowa - G SUPER LUKSUSOWE' AND (example_models IS NULL OR example_models = '');

-- Vany - B MICROVANY
UPDATE samar_classes SET example_models = 'Opel Combo Life, Citroen Berlingo, Peugeot Rifter, Renault Kangoo, Toyota Proace City Verso, Ford Tourneo Courier'
WHERE name = 'Vany - B MICROVANY' AND (example_models IS NULL OR example_models = '');

-- Vany - C MINIVANY
UPDATE samar_classes SET example_models = 'VW Touran, BMW 2 Active Tourer, Citroen C4 SpaceTourer, Ford S-Max, Renault Scenic'
WHERE name = 'Vany - C MINIVANY' AND (example_models IS NULL OR example_models = '');

-- Vany - D VANY
UPDATE samar_classes SET example_models = 'VW Multivan, Mercedes V, Ford Tourneo Custom, Hyundai Staria, Toyota Proace Verso, Peugeot Traveller, Citroen SpaceTourer'
WHERE name = 'Vany - D VANY' AND (example_models IS NULL OR example_models = '');

-- Sportowo-rekreacyjne - A MINI
UPDATE samar_classes SET example_models = 'Mini Cooper, Mini Cabrio, Fiat 500e, Smart #1'
WHERE name = 'Sportowo-rekreacyjne - A MINI' AND (example_models IS NULL OR example_models = '');

-- Sportowo-rekreacyjne - B MAŁE
UPDATE samar_classes SET example_models = 'Mini Cooper, Mazda MX-5, Abarth 500/595, Toyota GR86, Subaru BRZ'
WHERE name = 'Sportowo-rekreacyjne - B MAŁE' AND (example_models IS NULL OR example_models = '');

-- Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA
UPDATE samar_classes SET example_models = 'Toyota GR Supra, BMW Z4, BMW 2 Coupe, Audi TT, Alpine A110, Cupra Born'
WHERE name = 'Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA' AND (example_models IS NULL OR example_models = '');

-- Sportowo-rekreacyjne - D ŚREDNIA
UPDATE samar_classes SET example_models = 'BMW 4, Mercedes C Coupe/Cabrio, Audi A5, Polestar 2, Tesla Model 3'
WHERE name = 'Sportowo-rekreacyjne - D ŚREDNIA' AND (example_models IS NULL OR example_models = '');

-- Sportowo-rekreacyjne - F LUKSUSOWE
UPDATE samar_classes SET example_models = 'Porsche 911, BMW 8, Mercedes SL, Maserati GranTurismo, Maserati GranCabrio'
WHERE name = 'Sportowo-rekreacyjne - F LUKSUSOWE' AND (example_models IS NULL OR example_models = '');

-- Sportowo-rekreacyjne - G SUPER LUKSUSOWE
UPDATE samar_classes SET example_models = 'Ferrari 296 GTB, Lamborghini Revuelto, McLaren 750S, Aston Martin Vantage, Bentley Continental, Rolls-Royce Spectre, Porsche GT3'
WHERE name = 'Sportowo-rekreacyjne - G SUPER LUKSUSOWE' AND (example_models IS NULL OR example_models = '');

-- Terenowo-rekreacyjne (SUV) - B MAŁE
UPDATE samar_classes SET example_models = 'Toyota Yaris Cross, VW T-Cross, VW T-Roc, Hyundai Kona, Kia Stonic, Ford Puma, Skoda Kamiq, Peugeot 2008, Renault Captur, Opel Mokka, Volvo EX30'
WHERE name = 'Terenowo-rekreacyjne (SUV) - B MAŁE' AND (example_models IS NULL OR example_models = '');

-- Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA
UPDATE samar_classes SET example_models = 'VW Tiguan, BMW X3, Audi Q5, Mercedes GLC, Ford Kuga, Hyundai Tucson, Kia Sportage, Toyota RAV4, Skoda Kodiaq, Mazda CX-60, Nissan X-Trail, Porsche Macan'
WHERE name = 'Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA' AND (example_models IS NULL OR example_models = '');

-- Terenowo-rekreacyjne (SUV) - D ŚREDNIA
UPDATE samar_classes SET example_models = 'VW Tiguan, BMW X1, Audi Q3, Hyundai Tucson, Kia Sportage, Toyota Corolla Cross, Skoda Karoq, Mazda CX-5, Nissan Qashqai, Dacia Duster, Ford Explorer'
WHERE name = 'Terenowo-rekreacyjne (SUV) - D ŚREDNIA' AND (example_models IS NULL OR example_models = '');

-- Terenowo-rekreacyjne (SUV) - E WYŻSZA
UPDATE samar_classes SET example_models = 'BMW X7, Mercedes GLS, Lotus Eletre, Mercedes EQS SUV, Hongqi E-HS9'
WHERE name = 'Terenowo-rekreacyjne (SUV) - E WYŻSZA' AND (example_models IS NULL OR example_models = '');

-- Terenowo-rekreacyjne (SUV) - F LUKSUSOWE
UPDATE samar_classes SET example_models = 'Lamborghini Urus, Bentley Bentayga, Aston Martin DBX, Ferrari Purosangue, Rolls-Royce Cullinan'
WHERE name = 'Terenowo-rekreacyjne (SUV) - F LUKSUSOWE' AND (example_models IS NULL OR example_models = '');

-- Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE
UPDATE samar_classes SET example_models = 'BMW X5/X6, Audi Q7/Q8, Mercedes GLE, VW Touareg, Porsche Cayenne, Land Rover Range Rover, Volvo XC90, Toyota Land Cruiser, Tesla Model X, Lexus RX'
WHERE name = 'Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE' AND (example_models IS NULL OR example_models = '');

-- Kombivany - H KOMBI-VANY
UPDATE samar_classes SET example_models = 'VW Caddy, Citroen Berlingo, Ford Transit/Tourneo Connect, Mercedes Citan/T, Renault Kangoo, Toyota Proace City Verso, Opel Combo, Peugeot Rifter, VW ID.Buzz'
WHERE name = 'Kombivany - H KOMBI-VANY' AND (example_models IS NULL OR example_models = '');

-- Minibusy - I MINIBUSY
UPDATE samar_classes SET example_models = 'VW Transporter/Caravelle/Multivan, Mercedes Vito/V/Sprinter, Ford Transit Custom/Tourneo, Opel Vivaro/Zafira Life, Renault Trafic, Toyota Proace Verso, Hyundai Staria, Iveco Daily'
WHERE name = 'Minibusy - I MINIBUSY' AND (example_models IS NULL OR example_models = '');
