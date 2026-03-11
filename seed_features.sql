-- Wyczyść stare dane (opcjonalnie)
DELETE FROM reverse_search.universal_features;
DELETE FROM reverse_search.universal_feature_categories;

-- Dodaj Kategorie
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('c8d1c814-0769-4ed0-83e7-09d7385a948b', 'wymiary_masy', 'Wymiary i Masy');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('325a857d-b73f-429f-9b94-b94d7e4d8a27', 'silnik_napęd', 'Silnik i Napęd');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('c6c23615-2428-4118-a4cd-aa20abddda84', 'przestrzeń_ładunkowa', 'Przestrzeń Ładunkowa');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('0e0f944f-49e9-429c-9871-7b559918a173', 'zabudowy_specjalistyczne', 'Zabudowy Specjalistyczne');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('57668cc7-e413-416f-ab2d-77501e2f10ef', 'komfort_wnętrze', 'Komfort i Wnętrze');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'bezpieczeństwo', 'Bezpieczeństwo');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('fc56af5c-266f-49f6-b698-fd31811c9450', 'wygląd_zewnętrzny', 'Wygląd Zewnętrzny');
INSERT INTO reverse_search.universal_feature_categories (id, category_key, display_name) VALUES ('4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'inne', 'Inne');

-- Dodaj Cechy
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3f0c1b02-7d36-4c79-8f88-5028a76fe10d', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'długość_pojazdu_w_mm_bez_haka', 'długość pojazdu w mm (bez haka)', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ad35db1b-04be-4bd5-936d-6255eba655b9', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'szerokość_pojazdu_rozłożone_lusterka_w_mm', 'szerokość pojazdu (rozłożone lusterka) w mm', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ae3e9b2e-54db-4e4a-966a-ca01e860b6b0', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'wysokość_pojazdu_w_mm', 'wysokość pojazdu w mm', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('31cdf161-62db-4eb8-9678-a4ed0888e4bc', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'długość_przestrzeni_ładunkowej_w_mm', 'długość przestrzeni ładunkowej w mm', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('db435a81-4a61-4ef5-b47c-943fdc600da8', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'wysokość_przestrzeni_ładunkowej_w_mm', 'wysokość przestrzeni ładunkowej w mm', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a00ef0a2-0f81-4d69-8ffe-b861de94e24c', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'szerokość_przestrzeni_ładunkowej_w_mm', 'szerokość przestrzeni ładunkowej w mm', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d17ed026-6012-4001-96d1-b28d7a1dde83', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'minimalna_szerokość_między_nadkolami_w_mm', 'minimalna szerokość między nadkolami w mm', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('db6f037d-eaee-4f85-bbb4-93b126388e58', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'długość_przestrzeni_ładunkowej_dla_złożonych_siedzeń_w_mm_iii_rząd', 'długość przestrzeni ładunkowej dla złożonych siedzeń w mm (III rząd)', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('6abbdd0f-462b-41d4-96b7-b89fb31e2749', 'c6c23615-2428-4118-a4cd-aa20abddda84', 'kubatura_przestrzeni_ładunkowej_w_m3', 'kubatura przestrzeni ładunkowej w m3', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('920de39c-ea5e-41ed-b26c-7ed236d11b0a', 'c6c23615-2428-4118-a4cd-aa20abddda84', 'pojemność_przestrzeni_ładunkowej_dla_złożonych_siedzeń_w_litrach_iii_rząd', 'pojemność przestrzeni ładunkowej dla złożonych siedzeń w litrach (III rząd)', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('0dc73a9b-3c75-4849-bc7e-82f18b450f4d', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'dopuszczalna_ładowność_w_kg', 'dopuszczalna ładowność w kg', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('5f919743-8edf-4e81-9ad7-d5878f2e8fc3', 'c6c23615-2428-4118-a4cd-aa20abddda84', 'ilość_europalet', 'ilość europalet', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('79cae73d-bfe3-4441-9ea8-9990bf4f211b', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'sposób_otwarcia_tylnych_drzwi', 'sposób otwarcia tylnych drzwi', 'enum', '{"options": ["skrzydła", "klapa"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3b3ffab9-5e02-444e-88b3-4435fa65e34d', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'kąt_otwarcia_tylnych_drzwi', 'kąt otwarcia tylnych drzwi', 'enum', '{"options": ["180°", "270°"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('462cd6b7-cb4b-4112-8443-e7ea0b613203', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'boczne_drzwi', 'boczne drzwi', 'enum', '{"options": ["z lewej strony", "z prawej strony", "z obu stron"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('b4e3d399-783c-4a33-b535-7702a52e708c', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'czy_pojazd_spełnia_wymogi_vat', 'czy pojazd spełnia wymogi VAT', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('c017ab41-a604-464f-acbd-4d1ca9e386c4', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_mocowania_ładunku', 'system mocowania ładunku', 'enum', '{"options": ["listwy na bocznych ścianach", "uchwyty w podłodze"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('0956cb86-1775-450f-a2b7-66f6ccaabf94', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'rodzaj_zawieszenia', 'rodzaj zawieszenia', 'enum', '{"options": ["mechaniczne", "pneumatyczne"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('42f3f824-1d76-43be-a0a8-0007864485ff', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'skrzynia_narzędziowa', 'Skrzynia narzędziowa', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('bba9597d-a2f1-426a-875a-7545bd060dc1', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'zbiornik_na_wodę', 'Zbiornik na wodę', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('148b9a16-fffc-46c8-ac48-c933f1817776', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'otwieranie_burty_tylnej', 'otwieranie burty tylnej', 'enum', '{"options": ["otwierana w osi górnej", "otwierana w osi dolnej"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('2828e304-5dec-4107-94cb-17339501af87', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'otwieranie_burt_bocznych', 'otwieranie burt bocznych', 'enum', '{"options": ["otwierana w osi górnej", "otwierana w osi dolnej"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('72aa5ddb-f979-4cbc-b5e6-da841fa7d3b2', 'c6c23615-2428-4118-a4cd-aa20abddda84', 'odzielenie_przestrzeni_ładunkowej', 'odzielenie przestrzeni ładunkowej', 'enum', '{"options": ["ściana grodziowa", "krata", "brak"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('fbb54d32-079d-44e9-940e-500bcbbfe4e3', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'regulacja_wysokości_plandeki_szkieletu_konstrukcji', 'regulacja wysokości plandeki (szkieletu konstrukcji)', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('9e510883-1029-4c35-8ec9-452e17286e86', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_plandeki_przesuwnej_firanka', 'system plandeki przesuwnej (firanka)', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('cdc9ddab-dccd-483e-ba2f-7c5a3a693e93', '0e0f944f-49e9-429c-9871-7b559918a173', 'kabina_sypialna', 'Kabina sypialna', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8b04b901-15d8-43b4-8b54-76ff2979c976', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'marka_kabiny_sypialnej', 'Marka kabiny sypialnej', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('20e4e118-cca1-4fa8-a8c2-3692431b0a78', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'model_kabiny_sypialnej', 'Model kabiny sypialnej', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d3f7273b-cf71-48dd-a9aa-de43f0f6e396', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'spoiler_dachowy', 'Spoiler dachowy', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a38400ee-0a0d-4ad8-8881-37bc47a57b61', '0e0f944f-49e9-429c-9871-7b559918a173', 'ogrzewanie_postojowe_webasto', 'Ogrzewanie postojowe Webasto', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('96ae6d23-176d-48e5-8c8c-787a08b9f5d1', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'hak_holowniczyzaczep', 'Hak holowniczy/zaczep', 'enum', '{"options": ["hak", "zaczep", "brak"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d8291d5f-ba01-4577-9af4-769b982444f7', 'cf35a46c-2bf1-400f-8971-2752d1236f18', 'd_uciag', 'D - uciag', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8d412f40-b62f-4224-9aad-be1571d69ebe', 'cf35a46c-2bf1-400f-8971-2752d1236f18', 's_nacisk_na_hak', 'S - nacisk na hak', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('53c00550-2511-4bbb-b790-2c0fb28d7b7b', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'dopuszczalna_masa_całkowita_zespołu_pojazdów_kg', 'dopuszczalna masa całkowita zespołu pojazdów (kg)', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('bdb297b9-2942-4daf-a35f-f0adf88c2207', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'maksymalna_masa_całkowita_przyczepy_z_hamulcem_kg', 'maksymalna masa całkowita przyczepy z hamulcem (kg)', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('949dbf25-697e-4805-817f-eba5f4e3a66d', 'c8d1c814-0769-4ed0-83e7-09d7385a948b', 'maksymalna_masa_całkowita_przyczepy_bez_hamulca_kg', 'maksymalna masa całkowita przyczepy bez hamulca (kg)', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8766cc7b-9c47-4a0a-a5e1-2a29935ecbfa', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'instalacja_lpg_taknie', 'instalacja LPG (tak/nie)', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('71e647a5-e468-41ce-9e95-1063192f37c4', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'marka_instalacji_lpg', 'marka instalacji LPG', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('99aa2dbe-5bfd-4bed-b16d-6f464b8f5f62', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'model_instalacji_lpg', 'model  instalacji LPG', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('6a524902-399f-44f6-b8c1-4a9d236ae506', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'gwarantinstalator_instalacji_lpg', 'gwarant/instalator instalacji LPG', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('758bc20f-51a4-4fc5-876e-23106e50aa8c', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'cykl_obowiązkowego_serwisu_instalacji_lpg_w_kmmiesiącach', 'cykl obowiązkowego serwisu instalacji LPG w km/miesiącach', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('b1e2c99b-c4c9-4d03-94f4-8ae74dafcea4', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'producent_zbiornika_lpg', 'Producent zbiornika LPG', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('1907a048-8e1c-4cb8-9a3e-98ea07a3aa50', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'pojemność_zbiornika_lpg_w_litrach', 'Pojemność zbiornika LPG w litrach', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3c9c2aa7-433f-42a0-b02c-17653dc33a12', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'nr_fabryczny_zbiornika_lpg', 'Nr fabryczny zbiornika LPG', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('95878a09-2e9c-4836-a97d-07a81c2fb90f', '0e0f944f-49e9-429c-9871-7b559918a173', 'rodzaj_zabudowy_chłodniczej_izotermachłodnia', 'Rodzaj zabudowy chłodniczej (izoterma/chłodnia)', 'enum', '{"options": ["izoterma", "chłodnia"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('09fc428f-a199-4f6f-8910-8dcc9b13b2ac', '0e0f944f-49e9-429c-9871-7b559918a173', 'marka_agregatu', 'Marka agregatu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('b9c307cd-1d37-4ed2-8aea-c12ccecadd5d', '0e0f944f-49e9-429c-9871-7b559918a173', 'model_agregatu', 'Model agregatu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ac61d18c-8498-472f-9c98-db9f0c2c9d19', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'klasa_chłodzenia_abc', 'Klasa chłodzenia (A/B/C)', 'enum', '{"options": ["a", "b", "c"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('deba2af2-2cc9-4266-a6c7-8c95b7f3da9c', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'zakres_temperatury_chłodzenia', 'Zakres temperatury chłodzenia', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('01f0ea83-1d93-4776-990c-94e6da4cac2a', '0e0f944f-49e9-429c-9871-7b559918a173', 'funkcja_grzania_agregatu', 'Funkcja grzania agregatu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('dc6c11b3-f681-4c31-8c23-e8152dfa3264', '0e0f944f-49e9-429c-9871-7b559918a173', 'gwarantwykonawca_agregatu', 'Gwarant/wykonawca agregatu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('90fb2ff8-4e4d-4ed7-b4c1-b88824218c4d', '0e0f944f-49e9-429c-9871-7b559918a173', 'cykl_obowiązkowego_serwisu_agregatu_w_miesiącach', 'Cykl obowiązkowego serwisu agregatu w miesiącach', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('620f1050-8529-4e76-a282-dbb1dac8d038', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'pomiar_temperatury_ładunku', 'Pomiar temperatury ładunku', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('9f8d44d8-981d-4d23-bdeb-878a5d8bf526', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'sposób_pomiaru_temperatury_ładunku', 'Sposób pomiaru temperatury ładunku', 'enum', '{"options": ["wydruk z drukarki", "wersja elektroniczna"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('30a0fbc9-a658-4f14-bb57-ab61ded127e1', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'atest_sanepid', 'Atest SANEPID', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8a9067be-5ebb-49c2-915b-8db472a6dcb4', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'certyfikacja_atp', 'Certyfikacja ATP', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('c78f5230-79bd-49f2-a3d8-4a47fceb0211', '0e0f944f-49e9-429c-9871-7b559918a173', 'winda_załadowcza', 'Winda załadowcza', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('69775327-5d40-4abb-a363-1e4e0e131f09', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'producent_windy', 'Producent windy', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d982b9cc-51f4-4ddc-ba9a-7b07820faa9c', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'model_windy', 'Model windy', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('92cced0e-74b6-46b3-9e5b-ff76c4f66d23', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'udźwig_windy_w_kg', 'Udźwig windy w kg', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('52b7c1f9-a9cf-4fe5-ad13-af63a38ea5f4', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'sterowanie_windą', 'sterowanie windą', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('672e29ee-c59d-48d4-978e-7a5b808c030a', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'gwarantwykonawca_windy', 'Gwarant/wykonawca windy', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('6141869a-1638-4e0e-ad2b-570dba52caf0', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'cykl_obowiązkowego_serwisu_windy_w_miesiącach', 'Cykl obowiązkowego serwisu windy w miesiącach', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3e68ff38-b88b-44ab-8749-8a38b38e1e39', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'numer_seryjny_windy', 'Numer seryjny windy', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f677e5bc-a054-4394-82fc-d507ce821998', '0e0f944f-49e9-429c-9871-7b559918a173', 'tachograf', 'tachograf', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('68c6addb-dddf-4818-8ffa-432cf14e8acb', '0e0f944f-49e9-429c-9871-7b559918a173', 'producent_tachografu', 'Producent tachografu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('10cc4ae0-2142-4685-bfe1-23ce73b15940', '0e0f944f-49e9-429c-9871-7b559918a173', 'model_tachografu', 'Model tachografu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('266734a6-e342-4e3f-9738-197f5b49d385', '0e0f944f-49e9-429c-9871-7b559918a173', 'cykl_obowiązkowego_serwisu_tachografu_w_miesiącach', 'Cykl obowiązkowego serwisu tachografu w miesiącach', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('46c5646a-4712-44bf-96f4-987c1a3d40cf', '0e0f944f-49e9-429c-9871-7b559918a173', 'numer_seryjny_tachografu', 'Numer seryjny tachografu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d428d6e3-c1f2-48d0-9ffb-9e3429cfee45', '0e0f944f-49e9-429c-9871-7b559918a173', 'wywrot_ładunku', 'wywrot ładunku', 'enum', '{"options": ["tylny", "trójstronny"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('c7156b2e-0c13-498f-94a8-750285d03fd0', '0e0f944f-49e9-429c-9871-7b559918a173', 'sterowanie_wywrotem', 'sterowanie wywrotem', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d27fe0d9-44c8-4e9d-8cd8-3e2850139740', '0e0f944f-49e9-429c-9871-7b559918a173', 'producent_wywrotu', 'Producent wywrotu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('b4a783f0-962c-459a-ab6b-8ebddfb10421', '0e0f944f-49e9-429c-9871-7b559918a173', 'model_wywrotu', 'Model wywrotu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('34f255ef-652b-412c-b4ae-a1818049ccef', '0e0f944f-49e9-429c-9871-7b559918a173', 'gwarantwykonawca_wywrotu', 'Gwarant/wykonawca wywrotu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('7520e882-2fde-4889-97e4-f8fcf1227d7d', '0e0f944f-49e9-429c-9871-7b559918a173', 'cykl_obowiązkowego_serwisu_wywrotu_w_miesiącach', 'Cykl obowiązkowego serwisu wywrotu w miesiącach', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('334325bd-1983-4c19-8bc2-496886459304', '0e0f944f-49e9-429c-9871-7b559918a173', 'numer_seryjny_wywrotu', 'Numer seryjny wywrotu', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('e225f2c4-993d-4a02-9db6-9a3f7927d387', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'koła_tylnej_osi', 'Koła tylnej osi', 'enum', '{"options": ["pojedyncze", "bliźniak"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('4a4a9b9f-45b5-4ae3-bc0d-88815e49dbef', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'napęd', 'Napęd', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('12569fed-5904-4cf3-8bf3-441488fcccff', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'zużycie_paliwa_wltp_dla_silników_spalinowych_w_litrach', 'zużycie paliwa WLTP dla silników spalinowych w litrach', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('87e2025e-cfd5-4710-b5a1-ae90822e2b99', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'zasięg_wltp_dla_pojazdów_elektrycznych_w_km', 'Zasięg WLTP dla pojazdów elektrycznych w km', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8efe8770-c31b-4d4a-830a-0584122f143f', '325a857d-b73f-429f-9b94-b94d7e4d8a27', 'pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh', 'Pojemność akumulatora dla pojazdu elektrycznego w kWh', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('4e7826af-3578-4c97-be29-61a9111aeaaf', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'rodzaj_kablawtyczki_dla_pojazdu_elektrycznego', 'Rodzaj kabla/wtyczki dla pojazdu elektrycznego', 'enum', '{"options": ["typ1, typ2, ccs1, ccs2, chademo, gb", "t, tesla", "supercharger"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ed3dee20-6f29-4b20-96af-ff724be707a7', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'kategoria_prawa_jazdy', 'kategoria prawa jazdy', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3d6cf4eb-ab06-4717-92c5-16dbce018b52', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'rodzaj_zabudowy', 'rodzaj zabudowy', 'enum', '{"options": ["brak", "brygadowa", "kontenerowa", "izotermiczna", "chłodnicza", "wywrotka", "międzynarodowa", "skrzyniowa", "skrzyniowa z plandeką", "hard top", "roleta", "płaska", "wieloosobowa"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('12f4dba5-0fbc-41b9-b8cc-23c95fa2bb00', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'android_auto', 'Android Auto', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('4f99e164-fd14-483d-8f9e-96c3a5a3c03b', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'apple_car_play', 'Apple Car Play', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('e362b5aa-c47f-477c-aaf2-537a9e6bea78', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'abs', 'ABS', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3e3bece3-376e-4793-a5d2-56d74450f4ce', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'asr', 'ASR', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('20861845-1bd4-456a-b13b-19c81599c0ab', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'asystent_ruszania_na_wzniesieniach', 'asystent ruszania na wzniesieniach', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a4a6f09d-e0c4-4833-9f2a-4ba5c7ff81f7', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'asystent_zmiany_pasa_ruchu', 'asystent zmiany pasa ruchu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('22a1ba28-700a-45ea-9e06-c4cd3dc42711', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'automatycznie_ściemniające_się_lusterko_wsteczne', 'Automatycznie ściemniające się lusterko wsteczne', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('c0d79300-bc04-4cb0-8f91-f6b49dbf52bb', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'automatycznie_włączanie_świateł_awaryjnych_przy_nagłym_hamowaniu', 'automatycznie włączanie świateł awaryjnych przy nagłym hamowaniu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3dd63a8b-e23c-415e-a684-50a15559e904', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'bezkluczykowy_dostęp_i_uruchamianie_pojazdu', 'bezkluczykowy dostęp i uruchamianie pojazdu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('dc5c3140-4e48-4deb-87bc-cd14c7990009', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'bluetooth', 'Bluetooth', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('44e1a0a9-c9e0-4f8e-bcc8-9e9ed56ac21a', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'centralny_zamek_sterowany_pilotem', 'Centralny zamek sterowany pilotem', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('81f601fa-b170-4a01-9721-0695f3187342', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'czujnik_deszczu', 'Czujnik deszczu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f4a6c19f-f9bd-47be-8d88-354a1026100a', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'czujnik_zmierzchu', 'Czujnik zmierzchu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ae4989a6-99a6-4bb4-b66e-282f871efb0e', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'dach_otwierany_elektrycznie', 'Dach otwierany elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('150cd922-53b0-4910-8ddc-52f33a1fbcea', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'dach_panoramiczny', 'Dach panoramiczny', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('348330e9-bf94-4b7b-9658-af0dc4d95cc9', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'ekran_dotykowy', 'Ekran dotykowy', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('93723eb0-ad3f-468d-8336-194f00bcb4fc', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'elektrycznie_sterowana_pokrywa_bagażnika', 'Elektrycznie sterowana pokrywa bagażnika', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('7f53768b-3d5f-459d-81d6-b55fc6a4d9f4', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'lusterka_boczne', 'Lusterka boczne', 'enum', '{"options": ["elektrycznie sterowane", "elektrycznie sterowane i składane", "elektrycznie sterowane, składane i podgrzewane"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f96d5ae2-2a45-4c71-aa97-ee28ea1a6c06', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'esp', 'ESP', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('765926f7-4304-4044-ad54-cbfa349047ed', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'felga_aluminiowa', 'felga aluminiowa', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('cde2ea3e-9f29-4c39-acb0-98389300595f', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotel_kierowcy_ustawiany_elektrycznie', 'Fotel kierowcy ustawiany elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a7ae5318-f29b-4d39-99b3-792000cd5fca', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotel_kierowcy_z_elektryczną_regulacją_podparcia_lędźwiowego', 'Fotel kierowcy z elektryczną regulacją podparcia lędźwiowego', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d95d2832-dc0b-4fba-ac71-712340409295', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotel_kierowcy_z_regulacją_wysokości', 'Fotel kierowcy z regulacją wysokości', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('b541fc6e-4230-4728-86de-01692ea98982', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotel_pasażera_ustawiany_elektrycznie', 'Fotel pasażera ustawiany elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('06657d3f-eb10-468b-8916-49bcf9c6da72', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotel_kierowcy_z_pamięcią_ustawienia', 'Fotel kierowcy z pamięcią ustawienia', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('dfe68a43-6203-429f-b112-628d11b02146', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotele_przednie_podgrzewane', 'Fotele przednie podgrzewane', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('67b1dc48-1493-4a18-a460-51f366b8c623', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotele_przednie_wentylowane', 'Fotele przednie wentylowane', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d3718065-acf4-4f09-bf74-aca781682bf2', '1f9892a9-51cc-4ed2-921e-36f30f2c9145', 'fotele_przednie_z_funkcją_masażu', 'Fotele przednie z funkcją masażu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a23dc063-e236-40c0-b5ab-91ea4f0e4594', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotele_tylne_podgrzewane', 'Fotele tylne podgrzewane', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('e6d7daff-6734-40f9-b9ad-9890c9aef9e9', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'fotele_tylne_wentylowane', 'Fotele tylne wentylowane', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ce17ed81-9509-4e67-a337-3646b7d854e8', '1f9892a9-51cc-4ed2-921e-36f30f2c9145', 'fotele_tylne_z_funkcją_masażu', 'Fotele tylne z funkcją masażu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f037d15d-53f4-41f8-bbd1-e5848bbcda33', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'funkcja_szybkiego_ładowania_samochodu', 'Funkcja szybkiego ładowania samochodu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('3dba33d9-a44e-41a5-be8a-9113899b74ae', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'gniazda_usb', 'gniazda USB', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('cd25c145-388e-4f70-a6b7-18af8009b485', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'gniazdo_12v', 'gniazdo 12V', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('aad64366-38f9-46c6-a05a-309800dad3a7', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'gps_nawigacja_satelitarna', 'GPS - nawigacja satelitarna', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('66b05287-0f82-443e-aa37-1d10960a33e9', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'kierownica_multifunkcyjna', 'Kierownica multifunkcyjna', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d1b285d6-6da8-4454-b71a-0032ddb7bb94', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'kierownica_ogrzewana', 'Kierownica ogrzewana', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('67312394-6c70-40a2-babf-28c6c3bb0366', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'kierownica_regulowana_elektrycznie', 'Kierownica regulowana elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f09cd5ff-9889-4efc-9f72-8aafbbb33c42', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'kierownica_skórzana', 'Kierownica skórzana', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f47f96d6-b167-46f6-8725-ac5d5b66337b', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'klimatyzacja_automatyczna', 'Klimatyzacja automatyczna', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('7e8540f4-a237-4c1e-82e4-fbd6d5ae7209', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'klimatyzacja_dla_pasażerów_z_tyłu', 'Klimatyzacja dla pasażerów z tyłu', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('547fb3b2-bcb6-43ce-a312-0b8b4b4a1587', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'klimatyzacja_manualna', 'Klimatyzacja manualna', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('772eddbc-0f60-4e41-a842-43a809ca0633', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'koło_dojazdowe_i_zestaw_narzędzi', 'koło dojazdowe i zestaw narzędzi', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('ea5554a7-5371-4e1e-8b26-a6c76180d1b9', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'kurtyny_powietrzne', 'Kurtyny powietrzne', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a5e15744-71e1-490e-a8d6-02c85cb53027', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'lampy_przeciwmgielne', 'Lampy przeciwmgielne', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('25b740bf-0165-4cc0-a675-75c4f339e9e6', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'ładowarka_indukcyjna_do_smartfonów', 'ładowarka indukcyjna do smartfonów', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('55117e2a-646c-40b1-8ad9-638238c252f7', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'ogranicznik_prędkości', 'Ogranicznik prędkości', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('91b5d312-cd4e-4521-80c0-1fda2233c08d', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'podgrzewana_przednia_szyba', 'Podgrzewana przednia szyba', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a52b0b0f-9b57-4fdc-b7a6-bf850f6ec204', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'podłokietnik_przedni', 'Podłokietnik przedni', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('32e02837-9cf2-4f0e-bbbc-eee815fd187b', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'podłokietnik_tylny', 'Podłokietnik tylny', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('fa2cfdee-71fc-49c1-aace-b6abe5b2c314', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'poduszki_powietrzne', 'Poduszki powietrzne', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('349a8b71-e743-4776-9c4c-3ec5c0281e8d', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'radio', 'radio', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a51ea9ad-6dc9-4141-acc8-f8b9fa98b2f9', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'reflektory', 'Reflektory', 'enum', '{"options": ["halogenowe", "ksenonowe", "led", "matrycowe"]}'::jsonb);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('64bde7b2-47e3-4321-87ad-d0cab40ec9e3', 'fc56af5c-266f-49f6-b698-fd31811c9450', 'relingi_dachowe', 'relingi dachowe', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d6f7442e-6e5d-4c61-8d74-689b3d548e17', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'roleta_szyby_tylnej_regulowana_elektrycznie', 'Roleta szyby tylnej regulowana elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('1fe95a11-6ef6-4505-823b-61bef84bc66b', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'rolety_przeciwsłoneczne_boczne', 'Rolety przeciwsłoneczne boczne', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('5fb829af-da56-4d36-85f6-3bebdd2e6023', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'składana_tylna_kanapa', 'składana tylna kanapa', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('967119f4-996f-413d-a584-c3713cf5fe0a', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'sygnalizacja_spadku_ciśnienia_w_oponach', 'sygnalizacja spadku ciśnienia w oponach', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('5cb67002-c279-49d8-a4ee-38599cf7d978', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'system_audio', 'system audio', 'numeric', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('f882466e-5522-4579-a544-47177a02c86a', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_auto_hold', 'System Auto hold', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8dceb142-e682-4288-b969-b9787f23d324', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_bezkluczykowy', 'System bezkluczykowy', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d7dabeec-4098-41c9-a2b2-c74b5724b742', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'system_isofix', 'system Isofix', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('d16594e6-5bd1-4021-8657-9d6c4fbf7046', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_rozpoznający_zmęczenie_kierowcy', 'system rozpoznający zmęczenie kierowcy', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('9f61a422-cb1a-4bc5-adce-116fb4ab785d', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_rozpoznawania_znaków', 'system rozpoznawania znaków', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('88ebb64c-8e49-46aa-b4cd-1a9236d8aac4', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'czujniki_parkowania_przód', 'czujniki parkowania przód', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('6a556f22-3fdb-4ee0-829d-2deec4345fe3', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'czujniki_parkowania_tył', 'czujniki parkowania tył', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('875b47b9-2b4a-49a4-8978-b05224914aad', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'kamera_parkowania_tył', 'kamera parkowania tył', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('702f22ad-997b-4dfc-ae7e-861debcdb311', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_360', 'system 360"', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('53c383b6-517d-41fe-bc3d-e78d40d59745', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'autoalarm', 'autoalarm', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('bf09081a-b59a-4b4c-b715-db28d183f8cc', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'immobiliser', 'immobiliser', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('a1c407df-0d25-4c91-bcbb-562c424d551c', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'system_startstop', 'System Start/Stop', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('8505790c-e9ca-4857-90f2-a0f8b312d2c9', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'szyby_przednie_sterowane_elektrycznie', 'Szyby przednie sterowane elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('849be808-279e-4b71-94af-da59c753e53f', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'szyby_tylne_przyciemniane', 'Szyby tylne przyciemniane', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('24765ac2-4d91-4eec-a776-cc5ad508e5e2', '57668cc7-e413-416f-ab2d-77501e2f10ef', 'szyby_tylne_sterowane_elektrycznie', 'Szyby tylne sterowane elektrycznie', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('13e858b1-79ea-408b-b2b9-5d2bba9ef8dc', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'światła_do_jazdy_dziennej', 'światła do jazdy dziennej', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('11627d75-a76e-4b56-9c48-1679d4d40ca0', 'c6196cc1-16bb-4ab8-9a2d-18acca6db4ac', 'tempomat', 'Tempomat', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('1546d650-829c-42af-86cf-d8be77a65307', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'wyświetlacz_typu_head_up', 'Wyświetlacz typu Head-Up', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('1a32ab0a-f51c-4406-a751-afe1afc1b426', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'zestaw_naprawczy', 'zestaw naprawczy', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('02ca7805-db34-4573-bca7-9afc1d2933cf', '4fb15092-4bff-47ca-aac0-c0a8d2d67727', 'zmiana_biegów_w_kierownicy', 'Zmiana biegów w kierownicy', 'boolean', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
VALUES ('dc9c2bf9-c052-44c8-ab02-d629286daf31', 'c6c23615-2428-4118-a4cd-aa20abddda84', 'm2', 'm2', 'text', NULL);
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, metadata) 
