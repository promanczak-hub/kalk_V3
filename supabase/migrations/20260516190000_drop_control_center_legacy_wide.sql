-- Usuwa stara wide-row tabele control_center_legacy_wide po pomyslnym
-- przejsciu na pionowy EAV (migracja 20260516180000_eav_control_center).
-- Dane sa w `control_center` jako key/value rows; adapter w
-- core/control_center.py rekonstruuje wide-row dict dla kalkulatorow.

DROP TRIGGER IF EXISTS trigger_update_control_center_legacy_updated_at ON public.control_center_legacy_wide;
DROP TABLE IF EXISTS public.control_center_legacy_wide;
