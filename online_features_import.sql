-- Skrypt do zasilenia bazy produkcyjnej nowymi cechami uzytkowymi z pliku Excel



INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4b74b89a-f28b-446b-83f2-b70d420c15c5', id, 'długość_pojazdu_w_mm_bez_haka', 'długość pojazdu w mm (bez haka)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'a2154d4f-2b1c-4c99-b43a-5dbab2150ac5', id, 'szerokość_pojazdu_rozłożone_lusterka_w_mm', 'szerokość pojazdu (rozłożone lusterka) w mm', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'b50e947b-2672-4c08-9d4d-85be5bae1666', id, 'wysokość_pojazdu_w_mm', 'wysokość pojazdu w mm', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '8a4c3715-8974-4002-849f-911086af563b', id, 'długość_przestrzeni_ładunkowej_w_mm', 'długość przestrzeni ładunkowej w mm', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f2abd0f3-c716-494e-bdb2-c3fbc524c093', id, 'wysokość_przestrzeni_ładunkowej_w_mm', 'wysokość przestrzeni ładunkowej w mm', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '49bd4936-9cf5-4681-9039-55c4c50208ea', id, 'szerokość_przestrzeni_ładunkowej_w_mm', 'szerokość przestrzeni ładunkowej w mm', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0d7e54cc-80d8-4387-aebd-34fc4b1ea470', id, 'minimalna_szerokość_między_nadkolami_w_mm', 'minimalna szerokość między nadkolami w mm', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '5959cc87-2b5f-448e-a9f2-df64acba8d0b', id, 'długość_przestrzeni_ładunkowej_dla_złożonych_siedzeń_w_mm_iii_rząd', 'długość przestrzeni ładunkowej dla złożonych siedzeń w mm (III rząd)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e620953f-3d08-47c1-9df5-9c15b8527847', id, 'kubatura_przestrzeni_ładunkowej_w_m3', 'kubatura przestrzeni ładunkowej w m3', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '381b8ccf-9c97-42cd-a129-9fa8a9cb7b92', id, 'pojemność_przestrzeni_ładunkowej_dla_złożonych_siedzeń_w_litrach_iii_rząd', 'pojemność przestrzeni ładunkowej dla złożonych siedzeń w litrach (III rząd)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '6edb4579-8c15-4ecf-8d71-dfd432168656', id, 'dopuszczalna_ładowność_w_kg', 'dopuszczalna ładowność w kg', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '9c9450cd-4e7d-463d-ae84-301c8fcf2da2', id, 'ilość_europalet', 'ilość europalet', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '2ac9536e-9ff4-4fb2-8ef2-a1cf928652a2', id, 'sposób_otwarcia_tylnych_drzwi
skrzydła_klapa', 'sposób otwarcia tylnych drzwi
(skrzydła/klapa)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4c6bd7a4-aec0-45cd-9914-f6e7ae3aa241', id, 'kąt_otwarcia_tylnych_drzwi
180st_270st', 'kąt otwarcia tylnych drzwi
(180°/270°)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'be589469-3d92-45d2-a6a0-a6abfadb7331', id, 'boczne_drzwi
z_lewej_strony_z_prawej_strony_z_obu_stron', 'boczne drzwi
(z lewej strony/z prawej strony/z obu stron)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4bedfac1-a79f-477b-ab6d-fd27221be2ba', id, 'czy_pojazd_spełnia_wymogi_vat
vat_1_vat_2_nie_spełnia_wymogów_vat
', 'czy pojazd spełnia wymogi VAT
(VAT-1, VAT-2, nie spełnia wymogów VAT)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e1c9bc58-9455-4ca7-8142-3c8caf3f1532', id, 'system_mocowania_ładunku
listwy_na_bocznych_ścianach_uchwyty_w_podłodze', 'system mocowania ładunku
(listwy na bocznych ścianach/uchwyty w podłodze)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e086555e-59b4-420f-9264-e42ab4fd75fb', id, 'rodzaj_zawieszenia
mechaniczne_pneumatyczne', 'rodzaj zawieszenia
(mechaniczne/pneumatyczne)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '627a3c39-f8b3-434f-a424-0bdb44446d18', id, 'skrzynia_narzędziowa
tak_nie', 'Skrzynia narzędziowa
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '33cc7932-ed61-4ce3-8eef-0e9cfaa40305', id, 'zbiornik_na_wodę
tak_nie', 'Zbiornik na wodę
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '119616e8-d239-4aea-9b17-910038e9fb68', id, 'otwieranie_burty_tylnej
otwierana_w_osi_górnej_otwierana_w_osi_dolnej', 'otwieranie burty tylnej
(otwierana w osi górnej/otwierana w osi dolnej)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1f011643-ebad-48d3-a45e-a5a434ad98a6', id, 'otwieranie_burt_bocznych
otwierana_w_osi_górnej_otwierana_w_osi_dolnej', 'otwieranie burt bocznych
(otwierana w osi górnej/otwierana w osi dolnej)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '59014acd-a7ec-4922-8826-ca6e769b538e', id, 'odzielenie_przestrzeni_ładunkowej
ściana_grodziowa_krata_brak', 'odzielenie przestrzeni ładunkowej
(ściana grodziowa/krata/brak)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '5a74476e-0463-4174-b321-ae6e8a00a10c', id, 'regulacja_wysokości_plandeki_szkieletu_konstrukcji
tak_nie', 'regulacja wysokości plandeki (szkieletu konstrukcji)
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'a7c3391a-4c26-481c-8b5a-cbad4348300c', id, 'system_plandeki_przesuwnej_firanka
tak_nie', 'system plandeki przesuwnej (firanka)
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0357e5a4-864e-43e4-85c4-0b735e210132', id, 'kabina_sypialna
tak_nie', 'Kabina sypialna
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cabin'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '2620f0fe-77e9-4afc-b73e-a12792bf27a1', id, 'marka_kabiny_sypialnej', 'Marka kabiny sypialnej', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd70a58d1-7047-42ea-92b5-3153c8bcdea5', id, 'model_kabiny_sypialnej', 'Model kabiny sypialnej', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3bd79447-d98f-4ae7-a679-66a02d5134f0', id, 'spoiler_dachowy
tak_nie', 'Spoiler dachowy
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cabin'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'afc8c3e0-ccf7-4662-9bd7-c81e3d984414', id, 'ogrzewanie_postojowe_webasto
tak_nie', 'Ogrzewanie postojowe Webasto
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e2bf884d-7b83-49da-9b2d-719c4ec51d50', id, 'hak_holowniczy_zaczep
hak_zaczep_brak', 'Hak holowniczy/zaczep
(hak/zaczep/brak)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'towing'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3c068344-fd5d-48b5-97cd-7acc9c038770', id, 'd_uciag
kn', 'D - uciag
(kN)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'towing'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '78c3687a-0d3a-45dc-85f5-fde56fb66143', id, 's_nacisk_na_hak
kg', 'S - nacisk na hak
(kg)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'towing'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '9685d42d-fa98-4331-91ab-a2776bf3e390', id, 'dopuszczalna_masa_całkowita_zespołu_pojazdów_kg
f.3._z_dow_rej', 'dopuszczalna masa całkowita zespołu pojazdów (kg)
F.3. (z dow rej)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'towing'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'c8011c88-f809-4a07-9192-cb59ed53a1b4', id, 'maksymalna_masa_całkowita_przyczepy_z_hamulcem_kg
o.1_z_dow_rej', 'maksymalna masa całkowita przyczepy z hamulcem (kg)
O.1 (z dow rej)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'towing'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '117376f6-7736-4d9f-9c37-a988271e386e', id, 'maksymalna_masa_całkowita_przyczepy_bez_hamulca_kg
o.2_z_dow_rej', 'maksymalna masa całkowita przyczepy bez hamulca (kg)
O.2 (z dow rej)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'towing'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '00799d15-c02b-4d30-8671-2c5994391d23', id, 'instalacja_lpg_tak_nie', 'instalacja LPG (tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '11e24825-c94a-4cbb-a20d-a5e2026db613', id, 'marka_instalacji_lpg', 'marka instalacji LPG', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '7899d099-55d8-4f16-b2b7-4321d6e44d06', id, 'model_instalacji_lpg', 'model  instalacji LPG', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '470ed13f-af01-4ba5-b71e-a73f87f9413e', id, 'gwarant_instalator_instalacji_lpg', 'gwarant/instalator instalacji LPG', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '93b27cbc-ac32-47ed-9161-a7a79c9599e8', id, 'cykl_obowiązkowego_serwisu_instalacji_lpg_w_km_miesiącach', 'cykl obowiązkowego serwisu instalacji LPG w km/miesiącach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'eaba1cd2-4199-44de-b1f7-64955c6c02ef', id, 'producent_zbiornika_lpg', 'Producent zbiornika LPG', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '549d7cae-8674-42f4-ab50-4a1bea4f4f01', id, 'pojemność_zbiornika_lpg_w_litrach', 'Pojemność zbiornika LPG w litrach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'c00be16e-83b9-4670-9f33-cf3f42f1962d', id, 'nr_fabryczny_zbiornika_lpg', 'Nr fabryczny zbiornika LPG', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lpg'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3144480b-f2a2-426e-a5f7-669e7fc5ed8c', id, 'rodzaj_zabudowy_chłodniczej_izoterma_chłodnia', 'Rodzaj zabudowy chłodniczej (izoterma/chłodnia)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'c2ab6b96-bf2c-4f30-96d7-0b1a2d0bf27b', id, 'marka_agregatu', 'Marka agregatu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3825a34a-1b5b-4f85-9992-001cc205a25e', id, 'model_agregatu', 'Model agregatu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3891a60f-9dcb-4989-b34e-6cce0e9a899a', id, 'klasa_chłodzenia_a_b_c', 'Klasa chłodzenia (A/B/C)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '49c1a44b-fa8e-4764-bf22-1fee4c64606a', id, 'zakres_temperatury_chłodzenia_
od_…c_do_+_…c', 'Zakres temperatury chłodzenia 
(od -…C do + …C)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '12b52d87-095d-4b60-9e5f-48b32c135aa5', id, 'funkcja_grzania_agregatu_
tak_nie', 'Funkcja grzania agregatu 
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '58f814ca-4325-4239-b99c-7c6b4dca8a64', id, 'gwarant_wykonawca_agregatu', 'Gwarant/wykonawca agregatu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd92f056a-3cf7-4d7c-b584-2162d909c1bb', id, 'cykl_obowiązkowego_serwisu_agregatu_w_miesiącach', 'Cykl obowiązkowego serwisu agregatu w miesiącach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd62cb68a-224a-4bca-a7ef-0800542a11e7', id, 'pomiar_temperatury_ładunku
tak_nie', 'Pomiar temperatury ładunku
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e0c2e1b6-d27d-42d5-a6aa-2ed46436679d', id, 'sposób_pomiaru_temperatury_ładunku
wydruk_z_drukarki_wersja_elektroniczna', 'Sposób pomiaru temperatury ładunku
(wydruk z drukarki/wersja elektroniczna)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '55766fef-735b-4e25-8e00-2b40b0a04dae', id, 'atest_sanepid
tak_nie', 'Atest SANEPID
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3aaf1364-edec-42d6-8e81-eb31b9cd7cea', id, 'certyfikacja_atp
tak_nie', 'Certyfikacja ATP
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '85fdfdd1-6601-4d3e-88f8-b4542f616f2a', id, 'winda_załadowcza
tak_nie', 'Winda załadowcza
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '83b7267c-b4c2-47f3-a368-35103bc469a4', id, 'producent_windy', 'Producent windy', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'b5411058-0052-44e8-a7c7-da63a89257f5', id, 'model_windy', 'Model windy', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '889139eb-4e74-4ad3-9bc3-b009f5e3f83d', id, 'udźwig_windy_w_kg', 'Udźwig windy w kg', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'dbc2873e-c338-48a0-913a-ea7d5960a405', id, 'długość_platformy_windy
w_mm', 'Długość platformy windy
w mm', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'fbe4f49e-53df-4016-838e-8268da2c991d', id, 'szerokość_platformy_windy
w_mm', 'Szerokość platformy windy
w mm', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'dimensions'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'b4906635-99fd-4307-afad-7d061723e667', id, 'sterowanie_windą
bezprzewodowe_pilot_przewodowe_stacjonarna_konsola_sterująca', 'sterowanie windą
(bezprzewodowe (pilot)/ przewodowe/ stacjonarna konsola sterująca)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f4fbd175-809e-4047-b35f-9e2f516fa4ad', id, 'gwarant_wykonawca_windy', 'Gwarant/wykonawca windy', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4cac8a52-6a13-4422-9d03-cc1dd71f37a3', id, 'cykl_obowiązkowego_serwisu_windy_w_miesiącach', 'Cykl obowiązkowego serwisu windy w miesiącach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f4d584bd-d1bb-4307-a8c0-01dcfda00544', id, 'numer_seryjny_windy', 'Numer seryjny windy', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '607d1cf3-08f0-4269-a401-690b0972a74c', id, 'tachograf
tak_nie', 'tachograf
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1cc7913d-5f7f-4359-9ea5-f213545b62e3', id, 'producent_tachografu', 'Producent tachografu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '2d3e115d-a5a8-45c5-82ee-ff9b98723a2f', id, 'model_tachografu', 'Model tachografu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1b1d34b8-3805-46a8-be71-b8988b0e4aff', id, 'cykl_obowiązkowego_serwisu_tachografu_w_miesiącach', 'Cykl obowiązkowego serwisu tachografu w miesiącach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'debab23f-210f-4315-8f8f-164042d53a93', id, 'numer_seryjny_tachografu', 'Numer seryjny tachografu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lift_tachograph'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd7a426dd-b8b0-4ebe-843f-e4ffb35ac99f', id, 'wywrot_ładunku
tylny_trójstronny', 'wywrot ładunku
(tylny/trójstronny)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'a213a47a-2124-4a31-b1c7-b349b7df605f', id, 'sterowanie_wywrotem
bezprzewodowe_pilot_przewodowe_stacjonarna_konsola_sterująca', 'sterowanie wywrotem
(bezprzewodowe (pilot)/ przewodowe/ stacjonarna konsola sterująca)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3dee0437-b72c-4ecb-98d5-1fa3be9c782f', id, 'producent_wywrotu', 'Producent wywrotu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '677b1ee5-67b1-4945-b622-75e560d5f57d', id, 'model_wywrotu', 'Model wywrotu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '91d81923-4d8d-4f46-ad16-c30b8af499bd', id, 'gwarant_wykonawca_wywrotu', 'Gwarant/wykonawca wywrotu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '9aed395e-9757-4109-9c7b-961c5585c2fc', id, 'cykl_obowiązkowego_serwisu_wywrotu_w_miesiącach', 'Cykl obowiązkowego serwisu wywrotu w miesiącach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'b0e1a7bc-5c75-4f50-a446-099a7dc566c4', id, 'numer_seryjny_wywrotu', 'Numer seryjny wywrotu', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '09e360cf-d3e9-4ef1-aaff-5b1cd7a75959', id, 'koła_tylnej_osi
pojedyncze_bliźniak
', 'Koła tylnej osi
(pojedyncze/bliźniak)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '55c70b25-7ecc-42d1-9292-dcc321cad7f9', id, 'napęd
przedni_2x4_tylny_2x4_4x4', 'Napęd
(przedni 2x4, tylny 2x4, 4x4)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3f5183e3-51fc-41ec-be7a-cba96a9f043d', id, 'zużycie_paliwa_wltp_dla_silników_spalinowych_w_litrach', 'zużycie paliwa WLTP dla silników spalinowych w litrach', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'ecf907a1-7e56-4f27-ba00-4752b2be4cca', id, 'zasięg_wltp_dla_pojazdów_elektrycznych_w_km', 'Zasięg WLTP dla pojazdów elektrycznych w km', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd9e43847-2cc8-4492-b9fe-fab7478a63a9', id, 'pojemność_akumulatora_dla_pojazdu_elektrycznego_w_kwh', 'Pojemność akumulatora dla pojazdu elektrycznego w kWh', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'a995730a-6ebd-46af-98ae-4a161e2f85af', id, 'rodzaj_kabla_wtyczki_dla_pojazdu_elektrycznego
typ1_typ2_ccs1_ccs2_chademo_gb_t_tesla_supercharger', 'Rodzaj kabla/wtyczki dla pojazdu elektrycznego
(typ1, typ2, CCS1, CCS2, CHAdeMO, GB/T, Tesla/Supercharger)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'drivetrain'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '10d1eb84-2eb0-415b-a2e5-6c34776c5dbf', id, 'kategoria_prawa_jazdy', 'kategoria prawa jazdy', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f5deefdc-f3d7-45b6-9f76-bd2cd45cd967', id, 'rodzaj_zabudowy
brak_brygadowa_kontenerowa_izotermiczna_chłodnicza_wywrotka_międzynarodowa_skrzyniowa_skrzyniowa_z_plandeką_hard_top_roleta_płaska_wieloosobowa', 'rodzaj zabudowy
(brak/brygadowa/kontenerowa/izotermiczna/chłodnicza/wywrotka/międzynarodowa/skrzyniowa/ skrzyniowa z plandeką/hard top/roleta/płaska/wieloosobowa)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '68f733f7-30a8-44d6-9613-f24415f00610', id, 'android_auto
tak_nie', 'Android Auto
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'df04ec9a-47ef-4685-8ffe-508c4e1e57cf', id, 'apple_car_play
tak_nie', 'Apple Car Play
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1a485c69-a4de-497d-b187-e6db9c1cf529', id, 'abs
tak_nie', 'ABS
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'cf36d955-0c4c-43b3-99ee-84967c4817a1', id, 'asr
tak_nie', 'ASR
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3be7c7e5-c1be-4bb6-9efd-371a2a51ea65', id, 'asystent_ruszania_na_wzniesieniach
tak_nie', 'asystent ruszania na wzniesieniach
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '660d02ed-c09f-4fe4-b1c8-6878f24003e4', id, 'asystent_zmiany_pasa_ruchu
tak_nie', 'asystent zmiany pasa ruchu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '9f44eb2a-4675-4927-af15-84851255f8ae', id, 'automatycznie_ściemniające_się_lusterko_wsteczne
tak_nie', 'Automatycznie ściemniające się lusterko wsteczne
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f30362c9-4402-48c0-81de-fd4671893d28', id, 'automatycznie_włączanie_świateł_awaryjnych_przy_nagłym_hamowaniu
tak_nie', 'automatycznie włączanie świateł awaryjnych przy nagłym hamowaniu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'fd60a465-4397-4b99-bf46-197fa0f09fad', id, 'bezkluczykowy_dostęp_i_uruchamianie_pojazdu
tak_nie', 'bezkluczykowy dostęp i uruchamianie pojazdu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0613513b-f882-4f6e-b44e-ca9570741963', id, 'bluetooth
tak_nie', 'Bluetooth
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4ef9713f-661f-415b-b89b-b2b3ec3cf5a9', id, 'centralny_zamek_sterowany_pilotem
tak_nie', 'Centralny zamek sterowany pilotem
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd61f6238-ee0d-4331-81c9-5cc91ea23c44', id, 'czujnik_deszczu
tak_nie', 'Czujnik deszczu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'ad975133-23bd-4e52-a91d-c355d271774b', id, 'czujnik_zmierzchu
tak_nie', 'Czujnik zmierzchu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '352e6f95-4b8a-4179-8eda-e9030a9d2973', id, 'dach_otwierany_elektrycznie
tak_nie', 'Dach otwierany elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cabin'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '5d79ced0-d343-4eae-bb8b-3d741c7a68fd', id, 'dach_panoramiczny
tak_nie', 'Dach panoramiczny
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cabin'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1052b2b7-e5b8-4d0c-be9f-3ba50da940d9', id, 'ekran_dotykowy
tak_nie', 'Ekran dotykowy
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '47e2e747-96f3-4daa-a88e-c43d26ecfab6', id, 'elektrycznie_sterowana_pokrywa_bagażnika
tak_nie', 'Elektrycznie sterowana pokrywa bagażnika
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4632c0b8-6cf3-4910-ac15-4f075ab03190', id, 'lusterka_boczne
elektrycznie_sterowane_elektrycznie_sterowane_i_składane_elektrycznie_sterowane_składane_i_podgrzewane', 'Lusterka boczne
(Elektrycznie sterowane/Elektrycznie sterowane i składane/Elektrycznie sterowane, składane i podgrzewane)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'a520ca41-c056-430b-a1e4-d57defc7473a', id, 'esp
tak_nie', 'ESP
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '812a428c-004d-4a1a-973f-6b2a835422f2', id, 'felga_aluminiowa
tak_nie', 'felga aluminiowa
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '454fe477-d007-4bbf-a186-fb3c7c5bfa9e', id, 'fotel_kierowcy_ustawiany_elektrycznie
tak_nie', 'Fotel kierowcy ustawiany elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'ccd495de-e4ad-4352-a691-fcf7b90b2f41', id, 'fotel_kierowcy_z_elektryczną_regulacją_podparcia_lędźwiowego
tak_nie', 'Fotel kierowcy z elektryczną regulacją podparcia lędźwiowego
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '37349405-d9a1-4fd0-ab4d-dea4e61e7686', id, 'fotel_kierowcy_z_regulacją_wysokości
tak_nie', 'Fotel kierowcy z regulacją wysokości
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e62338c8-676c-483d-9cef-ff96775f8067', id, 'fotel_pasażera_ustawiany_elektrycznie
tak_nie', 'Fotel pasażera ustawiany elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '8441fda4-ded7-47eb-acbb-4b5593098b0d', id, 'fotel_kierowcy_z_pamięcią_ustawienia
tak_nie', 'Fotel kierowcy z pamięcią ustawienia
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4e5f38d7-8cfd-4289-ba42-8c985f6d0078', id, 'fotele_przednie_podgrzewane
tak_nie', 'Fotele przednie podgrzewane
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'fd4c65d6-da7e-42c6-86f3-1f00d5f072ec', id, 'fotele_przednie_wentylowane
tak_nie', 'Fotele przednie wentylowane
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1f29cb01-a7f1-4746-992d-0eb7b8ca1549', id, 'fotele_przednie_z_funkcją_masażu
tak_nie', 'Fotele przednie z funkcją masażu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '59a15a9f-2cb2-4b32-b924-14913698ce35', id, 'fotele_tylne_podgrzewane
tak_nie', 'Fotele tylne podgrzewane
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f3ba8295-9542-43d3-844e-53a90cf9bed3', id, 'fotele_tylne_wentylowane
tak_nie', 'Fotele tylne wentylowane
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '7ed0ccf4-41d3-4fd8-b94b-ffe0fabd6362', id, 'fotele_tylne_z_funkcją_masażu
tak_nie', 'Fotele tylne z funkcją masażu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '257156f7-94ee-4a74-aa38-0065854c2a54', id, 'funkcja_szybkiego_ładowania_samochodu
tak_nie', 'Funkcja szybkiego ładowania samochodu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0bb2fd66-d17f-4204-92ef-e7ad29a94f7a', id, 'gniazda_usb
tak_nie', 'gniazda USB
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '029e09d3-4739-4f07-9e6d-72ac802da317', id, 'gniazdo_12v
tak_nie', 'gniazdo 12V
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'b4d01efd-0e69-4f0b-834f-c214a8453c3a', id, 'gps_nawigacja_satelitarna
tak_nie', 'GPS - nawigacja satelitarna
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'c5ae1986-d098-4296-b68d-62eb8239a8bf', id, 'kierownica_multifunkcyjna
tak_nie', 'Kierownica multifunkcyjna
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '8828f124-9ec3-41a3-b563-d0ae7eaf9a4b', id, 'kierownica_ogrzewana
tak_nie', 'Kierownica ogrzewana
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '44b5b3b1-f7c8-49b6-a882-99259db2ad51', id, 'kierownica_regulowana_elektrycznie
tak_nie', 'Kierownica regulowana elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1bc295a6-501f-4100-befe-6e0a1cb95d33', id, 'kierownica_skórzana
tak_nie', 'Kierownica skórzana
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '6d54606f-3e27-4072-b3ce-179fd4fd0be8', id, 'klimatyzacja_automatyczna
tak_nie', 'Klimatyzacja automatyczna
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'aad55d50-4c3b-4a98-96b6-438a3f17f387', id, 'klimatyzacja_dla_pasażerów_z_tyłu
tak_nie', 'Klimatyzacja dla pasażerów z tyłu
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd4d69d65-3d98-4b65-84de-31da547186ac', id, 'klimatyzacja_manualna
tak_nie', 'Klimatyzacja manualna
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '49eef314-ff57-4d95-8dec-dd50c92cb3b3', id, 'koło_dojazdowe_i_zestaw_narzędzi
tak_nie', 'koło dojazdowe i zestaw narzędzi
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'cb3cabc4-f9a7-4768-b525-7229a2a7cadb', id, 'kurtyny_powietrzne
tak_nie', 'Kurtyny powietrzne
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '3cca5bb4-a46b-49da-ad99-ddbda9114d2d', id, 'lampy_przeciwmgielne
tak_nie', 'Lampy przeciwmgielne
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lighting'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '9e99698c-4658-4934-aae6-7a201267dba9', id, 'ładowarka_indukcyjna_do_smartfonów
tak_nie', 'ładowarka indukcyjna do smartfonów
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '687795ab-1e47-481f-910c-6b5e97cc0ad1', id, 'ogranicznik_prędkości
tak_nie', 'Ogranicznik prędkości
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '21f6737f-2f10-4a6f-88d9-c206f12f2e72', id, 'podgrzewana_przednia_szyba
tak_nie', 'Podgrzewana przednia szyba
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '2275bc59-9802-4e32-9e63-8105eff0c700', id, 'podłokietnik_przedni
tak_nie', 'Podłokietnik przedni
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '9d49d066-1cd6-4cb3-8b78-66350b77b3d4', id, 'podłokietnik_tylny
tak_nie', 'Podłokietnik tylny
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '6bd56045-e940-4e1a-b8ac-7bca0668b0d6', id, 'poduszki_powietrzne
liczba_poduszek', 'Poduszki powietrzne
(liczba poduszek)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '46ef51a0-2daf-4df9-ba6b-ed7479a9aa1c', id, 'radio
tak_nie', 'radio
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '16d10b0e-dd8a-493a-abb1-31668e2fa94f', id, 'reflektory
halogenowe_ksenonowe_led_matrycowe', 'Reflektory
(halogenowe/ksenonowe/LED/matrycowe)', 'text', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lighting'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'c5e6bb08-fec6-42ca-b4b5-38ca0b30c6d1', id, 'relingi_dachowe
tak_nie', 'relingi dachowe
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cabin'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd3c3ba05-5a0f-4dc3-8afb-0bcfd8e96cbe', id, 'roleta_szyby_tylnej_regulowana_elektrycznie
tak_nie', 'Roleta szyby tylnej regulowana elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '4823aa0a-2c3b-40f2-a986-c706ed47d755', id, 'rolety_przeciwsłoneczne_boczne
tak_nie', 'Rolety przeciwsłoneczne boczne
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '5605a706-c703-4b93-bc44-e1d0391318d0', id, 'składana_tylna_kanapa
tak_nie', 'składana tylna kanapa
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '1c5659dc-392e-4432-805d-193d3814d696', id, 'sygnalizacja_spadku_ciśnienia_w_oponach
tak_nie', 'sygnalizacja spadku ciśnienia w oponach
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'e6607956-c15d-4751-9413-f85f6f18c073', id, 'system_audio
liczba_głośnikow', 'system audio
(liczba głośnikow)', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd6de989a-ed17-490f-8f4c-5fbf21a7dca1', id, 'system_auto_hold
tak_nie', 'System Auto hold
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '525c4568-3c79-41ae-bc95-3c057a04d995', id, 'system_bezkluczykowy
tak_nie', 'System bezkluczykowy
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'df60ba74-eb51-40a1-a64e-f1021cf48099', id, 'system_isofix
tak_nie', 'system Isofix
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '7d8f9301-f226-4790-869d-ef7398406343', id, 'system_rozpoznający_zmęczenie_kierowcy
tak_nie', 'system rozpoznający zmęczenie kierowcy
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '245c18b8-91de-4af9-b2c6-12142e849700', id, 'system_rozpoznawania_znaków
tak_nie', 'system rozpoznawania znaków
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0d314947-29d5-4424-9b64-eab3e7d673b6', id, 'czujniki_parkowania_przód
tak_nie', 'czujniki parkowania przód
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '5e50e2fc-301d-4743-9c79-90eed02062ba', id, 'czujniki_parkowania_tył
tak_nie', 'czujniki parkowania tył
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0bdb3557-9cdb-4d5a-9c4b-a27af2f529ad', id, 'kamera_parkowania_tył
tak_nie', 'kamera parkowania tył
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'd18e9864-6073-45c1-a70d-fb9525dc63be', id, 'system_360"
tak_nie', 'system 360"
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '530e632a-a209-49fb-b95e-d0584c67274d', id, 'autoalarm
tak_nie', 'autoalarm
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '8b8c149f-fedf-4780-96ed-d00d87d2ad26', id, 'immobiliser
tak_nie', 'immobiliser
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'safety'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '56d65341-82d4-4aa5-80b0-d9a597c600a4', id, 'system_start_stop
tak_nie', 'System Start/Stop
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0df184e1-9552-4bcc-813b-ef2639a4543b', id, 'szyby_przednie_sterowane_elektrycznie
tak_nie', 'Szyby przednie sterowane elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '18f259c0-0e75-412c-a5bd-eee2796a90a6', id, 'szyby_tylne_przyciemniane
tak_nie', 'Szyby tylne przyciemniane
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'f945d73d-4448-470b-aed1-6142445f47a8', id, 'szyby_tylne_sterowane_elektrycznie
tak_nie', 'Szyby tylne sterowane elektrycznie
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'fdb93526-ab82-47e6-99bc-36143c0b8fdd', id, 'światła_do_jazdy_dziennej
tak_nie
', 'światła do jazdy dziennej
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'lighting'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'ca810aa6-bbbd-4ad0-8296-7af5d7aace43', id, 'tempomat
tak_nie', 'Tempomat
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'comfort'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '0aed2b40-db9d-4f17-a62f-1df5b283471f', id, 'wyświetlacz_typu_head_up
tak_nie', 'Wyświetlacz typu Head-Up
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '7577f983-8a68-42f5-b9a6-275752544fba', id, 'zestaw_naprawczy
tak_nie', 'zestaw naprawczy
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'bba976d6-9263-4e66-a99c-30d7bfec3e89', id, 'zmiana_biegów_w_kierownicy
tak_nie', 'Zmiana biegów w kierownicy
(tak/nie)', 'boolean', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT '5ed174b5-77f9-40bd-9502-2b174f71a832', id, 'm2', 'm2', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'bodywork'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'fc801354-ec85-4dd0-84ab-cc0ff2c58b58', id, 'ilość_europalet.1', 'ilość europalet.1', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;

INSERT INTO reverse_search.universal_features (id, category_id, feature_key, display_name, feature_type, vehicle_scope, is_filterable, source_standard)
SELECT 'a69709db-9157-4441-b0b3-7a7bc22a4ef1', id, 'ilość_europalet.2', 'ilość europalet.2', 'numeric', 'both', true, 'fleet_excel'
FROM reverse_search.universal_feature_categories WHERE category_key = 'cargo'
ON CONFLICT (feature_key) DO UPDATE SET 
    display_name = EXCLUDED.display_name,
    feature_type = EXCLUDED.feature_type;