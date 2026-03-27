-- Migration: Remap SAMAR classes to new consolidated ID sequence from Excel

BEGIN;

-- 1. Drop existing FK constraints safely
ALTER TABLE IF EXISTS replacement_car_rates DROP CONSTRAINT IF EXISTS replacement_car_rates_samar_class_id_fkey;
ALTER TABLE IF EXISTS body_type_wr_corrections DROP CONSTRAINT IF EXISTS body_type_wr_corrections_samar_class_id_fkey;
ALTER TABLE IF EXISTS ltr_admin_ubezpieczenia DROP CONSTRAINT IF EXISTS ltr_admin_ubezpieczenia_samar_class_id_fkey;
ALTER TABLE IF EXISTS ltr_admin_wspolczynniki_szkodowe DROP CONSTRAINT IF EXISTS ltr_admin_wspolczynniki_szkodowe_samar_class_id_fkey;
ALTER TABLE IF EXISTS samar_service_costs DROP CONSTRAINT IF EXISTS samar_service_costs_samar_class_id_fkey;
ALTER TABLE IF EXISTS ltr_admin_korekta_wr_markas DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_samar_class_fk;
ALTER TABLE IF EXISTS ltr_admin_korekta_wr_markas DROP CONSTRAINT IF EXISTS fk_brand_corr_samar_class;
ALTER TABLE IF EXISTS samar_class_depreciation_rates DROP CONSTRAINT IF EXISTS samar_class_depreciation_rates_samar_class_id_fkey;
ALTER TABLE IF EXISTS samar_class_mileage_corrections DROP CONSTRAINT IF EXISTS samar_class_mileage_corrections_samar_class_id_fkey;
ALTER TABLE IF EXISTS samar_class_base_rv DROP CONSTRAINT IF EXISTS samar_class_base_rv_samar_class_id_fkey;
ALTER TABLE IF EXISTS samar_class_options_rv DROP CONSTRAINT IF EXISTS samar_class_options_rv_samar_class_id_fkey;

-- 2. Create map and apply negative shift to avoid unique constraint violations
CREATE TEMP TABLE id_map (old_id INT, new_id INT, new_name TEXT);
INSERT INTO id_map (old_id, new_id, new_name) VALUES
(6, 1, 'Autobusy - AUTOBUSY'),
(5, 2, 'Ciężkie dostawcze - CIĘŻKIE DOSTAWCZE'),
(125, 3, 'Kombivany - H KOMBI-VANY'),
(1, 4, 'Lekkie dostawcze - KOMBI VAN'),
(2, 5, 'Lekkie dostawcze - VAN'),
(126, 6, 'Minibusy - I MINIBUSY'),
(3, 7, 'Pick-up - PICK-UP'),
(100, 8, 'Podstawowa - A MINI'),
(101, 9, 'Podstawowa - B MAŁE'),
(102, 10, 'Podstawowa - C NIŻSZA ŚREDNIA'),
(103, 11, 'Podstawowa - D ŚREDNIA'),
(104, 12, 'Podstawowa - E WYŻSZA'),
(105, 13, 'Podstawowa - F LUKSUSOWE'),
(106, 14, 'Podstawowa - G SUPER LUKSUSOWE'),
(112, 15, 'Sportowo-rekreacyjne - A MINI'),
(113, 16, 'Sportowo-rekreacyjne - B MAŁE'),
(114, 17, 'Sportowo-rekreacyjne - C NIŻSZA ŚREDNIA'),
(115, 18, 'Sportowo-rekreacyjne - D ŚREDNIA'),
(116, 19, 'Sportowo-rekreacyjne - E WYŻSZA'),
(117, 20, 'Sportowo-rekreacyjne - F LUKSUSOWE'),
(118, 21, 'Sportowo-rekreacyjne - G SUPER LUKSUSOWE'),
(4, 22, 'Średnie dostawcze - ŚREDNIE DOSTAWCZE'),
(119, 23, 'Terenowo-rekreacyjne (SUV) - B MAŁE'),
(120, 24, 'Terenowo-rekreacyjne (SUV) - C NIŻSZA ŚREDNIA'),
(121, 25, 'Terenowo-rekreacyjne (SUV) - D ŚREDNIA'),
(122, 26, 'Terenowo-rekreacyjne (SUV) - E WYŻSZA'),
(123, 27, 'Terenowo-rekreacyjne (SUV) - F LUKSUSOWE'),
(124, 28, 'Terenowo-rekreacyjne (SUV) - G SUPER LUKSUSOWE'),
(107, 29, 'Vany - B MICROVANY'),
(108, 30, 'Vany - C MINIVANY'),
(109, 31, 'Vany - D VANY'),
(110, 32, 'Vany - E WYŻSZA'),
(111, 33, 'Vany - F LUKSUSOWE');

-- Shift samar_classes IDs
UPDATE samar_classes sc SET id = -m.old_id FROM id_map m WHERE sc.id = m.old_id;

-- Shift child tables
UPDATE replacement_car_rates SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE body_type_wr_corrections SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE ltr_admin_ubezpieczenia SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE ltr_admin_wspolczynniki_szkodowe SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE samar_service_costs SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE ltr_admin_korekta_wr_markas SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE samar_class_depreciation_rates SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE samar_class_mileage_corrections SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE samar_class_base_rv SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);
UPDATE samar_class_options_rv SET samar_class_id = -samar_class_id WHERE samar_class_id IN (SELECT old_id FROM id_map);

-- Apply final IDs and names
UPDATE samar_classes sc SET id = m.new_id, name = m.new_name FROM id_map m WHERE sc.id = -m.old_id;

UPDATE replacement_car_rates t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE body_type_wr_corrections t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE ltr_admin_ubezpieczenia t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE ltr_admin_wspolczynniki_szkodowe t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE samar_service_costs t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE ltr_admin_korekta_wr_markas t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE samar_class_depreciation_rates t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE samar_class_mileage_corrections t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE samar_class_base_rv t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;
UPDATE samar_class_options_rv t SET samar_class_id = m.new_id FROM id_map m WHERE t.samar_class_id = -m.old_id;

-- 3. Restore Constraints
ALTER TABLE replacement_car_rates ADD CONSTRAINT replacement_car_rates_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE body_type_wr_corrections ADD CONSTRAINT body_type_wr_corrections_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE ltr_admin_ubezpieczenia ADD CONSTRAINT ltr_admin_ubezpieczenia_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE ltr_admin_wspolczynniki_szkodowe ADD CONSTRAINT ltr_admin_wspolczynniki_szkodowe_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE samar_service_costs ADD CONSTRAINT samar_service_costs_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE ltr_admin_korekta_wr_markas ADD CONSTRAINT ltr_admin_korekta_wr_markas_samar_class_fk FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE samar_class_depreciation_rates ADD CONSTRAINT samar_class_depreciation_rates_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE samar_class_mileage_corrections ADD CONSTRAINT samar_class_mileage_corrections_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE samar_class_base_rv ADD CONSTRAINT samar_class_base_rv_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;
ALTER TABLE samar_class_options_rv ADD CONSTRAINT samar_class_options_rv_samar_class_id_fkey FOREIGN KEY (samar_class_id) REFERENCES samar_classes(id) ON DELETE CASCADE;

-- Reset sequence to safety
SELECT setval(pg_get_serial_sequence('samar_classes', 'id'), coalesce(max(id), 1) + 1, false) FROM public.samar_classes;

COMMIT;
