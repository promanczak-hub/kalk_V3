BEGIN;

-- 1. Usuwanie starych wiszących FK, które pozostały po zmianie nazwy kolumny
ALTER TABLE public.ltr_admin_wspolczynniki_szkodowe DROP CONSTRAINT IF EXISTS ltr_admin_wspolczynniki_szkodowe_klasa_wr_id_fkey;
ALTER TABLE public.ltr_admin_ubezpieczenia DROP CONSTRAINT IF EXISTS "ltr_admin_ubezpieczenia_KlasaId_fkey";
ALTER TABLE public.replacement_car_rates DROP CONSTRAINT IF EXISTS replacement_car_rates_samar_class_id_fkey; -- just in case
ALTER TABLE public.ltr_admin_korekta_wr_markas DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_klasa_wr_id_fkey;

-- 1b. Brak powiązań wymagających kaskady w master danych

-- 2. Twardy reset obecnych klas (Kaskadowo usunie stawki, zrobimy re-insert)
DELETE FROM public.samar_classes;

-- 3. Wrzutka nowych 28 klas SAMAR
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (100, 'Podstawowa - A MINI', 'Podstawowa', 'A', 'Fiat 500, Hyundai i10, Kia Picanto, Toyota Aygo X, Dacia Spring');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (101, 'Podstawowa - B MAŁE', 'Podstawowa', 'B', 'Volkswagen Polo, Renault Clio, Toyota Yaris, Skoda Fabia, Opel Corsa');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (102, 'Podstawowa - C NIŻSZA ŚREDNIA', 'Podstawowa', 'C', 'Volkswagen Golf, Toyota Corolla, Skoda Octavia, Kia Ceed, Ford Focus');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (103, 'Podstawowa - D ŚREDNIA', 'Podstawowa', 'D', 'BMW Serii 3, Audi A5, Tesla Model 3, Toyota Camry, Volkswagen Passat');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (104, 'Podstawowa - E WYŻSZA', 'Podstawowa', 'E', 'BMW Serii 5, Audi A6, Mercedes Klasa E, Volvo S90, Lexus ES');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (105, 'Podstawowa - F LUKSUSOWE', 'Podstawowa', 'F', 'BMW Serii 7, Audi A8, Mercedes Klasa S, Porsche Panamera, Lexus LS');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (106, 'Podstawowa - G SUPER LUKSUSOWE', 'Podstawowa', 'G', 'Bentley Flying Spur, Rolls-Royce Ghost, Rolls-Royce Phantom');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (107, 'Vany - B MICROVANY', 'Vany', 'B', 'Honda Jazz');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (108, 'Vany - C MINIVANY', 'Vany', 'C', 'BMW 2 Active Tourer, Dacia Jogger, Mercedes Klasa B, Volkswagen Touran');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (109, 'Vany - D VANY', 'Vany', 'D', 'Forthing U-Tour');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (110, 'Vany - E WYŻSZA', 'Vany', 'E', 'Forthing V-Tour, Voyah Dream');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (111, 'Vany - F LUKSUSOWE', 'Vany', 'F', 'Lexus LM');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (112, 'Sportowo-rekreacyjne - A MINI', 'Sportowo-rekreacyjne', 'A', 'Fiat 500 Cabrio, Abarth 500 Cabrio');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (113, 'Sportowo-rekreacyjne - B MAŁE', 'Sportowo-rekreacyjne', 'B', 'Mini Cabrio');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (114, 'Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA', 'Sportowo-rekreacyjne', 'C', 'BMW Serii 4, Ford Mustang, Porsche 718');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (115, 'Sportowo-rekreacyjne - D ŚREDNIA', 'Sportowo-rekreacyjne', 'D', 'Mercedes CLE');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (116, 'Sportowo-rekreacyjne - E WYŻSZA', 'Sportowo-rekreacyjne', 'E', 'Alpine A110, BMW Z4, Mazda MX-5');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (117, 'Sportowo-rekreacyjne - F LUKSUSOWE', 'Sportowo-rekreacyjne', 'F', 'BMW Serii 8, Porsche 911, Mercedes SL');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (118, 'Sportowo-rekreacyjne - G SUPER LUKSUSOWE', 'Sportowo-rekreacyjne', 'G', 'Ferrari 296, Lamborghini Revuelto, Aston Martin DB12');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (119, 'Terenowo-rekreacyjne (SUV) - B MAŁE', 'Terenowo-rekreacyjne (SUV)', 'B', 'Ford Puma, Toyota Yaris Cross, Volkswagen T-Cross, Hyundai Kona');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (120, 'Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA', 'Terenowo-rekreacyjne (SUV)', 'C', 'BMW X3, Audi Q5, Hyundai Santa Fe, Kia Sorento');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (121, 'Terenowo-rekreacyjne (SUV) - D ŚREDNIA', 'Terenowo-rekreacyjne (SUV)', 'D', 'BMW X1, Audi Q3, Hyundai Tucson, Kia Sportage');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (122, 'Terenowo-rekreacyjne (SUV) - E WYŻSZA', 'Terenowo-rekreacyjne (SUV)', 'E', 'BMW X7, Mercedes GLS, Lotus Eletre');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (123, 'Terenowo-rekreacyjne (SUV) - F LUKSUSOWE', 'Terenowo-rekreacyjne (SUV)', 'F', 'Lamborghini Urus, Bentley Bentayga, Rolls-Royce Cullinan');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (124, 'Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE', 'Terenowo-rekreacyjne (SUV)', 'G', 'BMW X5, Porsche Cayenne, Mercedes GLE');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (125, 'Kombivany - H KOMBI-VANY', 'Kombivany', 'H', 'Citroen Berlingo, Peugeot Rifter, Volkswagen Caddy');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (126, 'Minibusy - I MINIBUSY', 'Minibusy', 'I', 'Volkswagen Multivan, Mercedes V-Class, Hyundai Staria');
INSERT INTO public.samar_classes (id, name, category, size_class, example_models) VALUES (127, 'Kempingowe - K KEMPINGOWE', 'Kempingowe', 'K', 'Volkswagen California, Mercedes Marco Polo');

-- 4. Odtworzenie i zmapowanie stawek ubezpieczeń

-- 5. Odtworzenie starych współczynników szkodowych
INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (samar_class_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (100, 0.91, 1.0);
INSERT INTO public.ltr_admin_wspolczynniki_szkodowe (samar_class_id, wsp_sredni_przebieg, wsp_wartosc_szkody) VALUES (104, 1.0, 1.0);

-- 6. Odtworzenie stawek wynajmu aut zastępczych
INSERT INTO public.replacement_car_rates (samar_class_id, samar_class_name, average_days_per_year, daily_rate_net) VALUES (100, 'Podstawowa - A MINI', 6.5, 50.0);
INSERT INTO public.replacement_car_rates (samar_class_id, samar_class_name, average_days_per_year, daily_rate_net) VALUES (104, 'Podstawowa - E WYŻSZA', 6.5, 185.0);

-- 7. Odtworzenie korekt marek bazujących na klasach
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 1, 'AUDI', NULL, 0.07, NULL);
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 5, 'AUDI', NULL, -0.03, NULL);
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 2, 'AUDI', NULL, 0.03, NULL);
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 1, 'BMW', NULL, 0.0, NULL);
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 5, 'BMW', NULL, 0.0, NULL);
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 1, 'VOLVO', NULL, -0.05, NULL);
INSERT INTO public.ltr_admin_korekta_wr_markas (samar_class_id, rodzaj_paliwa, brand_name, model_name, korekta_procent, notes) VALUES (104, 5, 'VOLVO', NULL, 0.01, NULL);

-- 8. Brak pojazdy_master pomijam

COMMIT;

