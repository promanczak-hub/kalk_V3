-- Add new SAMAR RV calculation toggles and parameters
ALTER TABLE control_center
ADD COLUMN samar_rv_apply_color_correction BOOLEAN NOT NULL DEFAULT TRUE,
ADD COLUMN samar_rv_apply_body_correction BOOLEAN NOT NULL DEFAULT TRUE,
ADD COLUMN samar_rv_apply_options_depreciation BOOLEAN NOT NULL DEFAULT TRUE,
ADD COLUMN samar_rv_base_mileage INT NOT NULL DEFAULT 140000,
ADD COLUMN samar_rv_mileage_unit_km INT NOT NULL DEFAULT 10000;
