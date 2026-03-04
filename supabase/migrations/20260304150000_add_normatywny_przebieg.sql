-- Add normative fleet mileage (floor for service cost calculation)
ALTER TABLE control_center
ADD COLUMN IF NOT EXISTS normatywny_przebieg_mc integer DEFAULT 2916;

-- 2916 km/mc = 35 000 km/rok (fleet average)
COMMENT ON COLUMN control_center.normatywny_przebieg_mc
IS 'Normatywny przebieg floty km/mc (= 35 000 km/rok). Floor do kalkulacji kosztów serwisowych.';
