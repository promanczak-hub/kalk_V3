-- A1: Drop legacy public.drivetrains (UPPERCASE codes AWD/FWD/RWD).
-- Replaced by public.drivetrain_types (lowercase codes, matches SOT _dict_drivetrains).
-- Verified: zero references in code (Python backend, frontend TS, SQL migrations).
-- CASCADE: drops the FK constraint samar_service_drive_multipliers_drive_fk;
-- the dependent table keeps its 3 hardcoded multiplier rows (drive_normalized text).
DROP TABLE IF EXISTS public.drivetrains CASCADE;
