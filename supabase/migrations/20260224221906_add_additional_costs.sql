ALTER TABLE control_center
    ADD COLUMN IF NOT EXISTS cost_gsm_subscription_monthly numeric DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_gsm_device numeric DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_gsm_installation numeric DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_hook_installation numeric DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_grid_dismantling numeric DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_registration numeric DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cost_sales_prep numeric DEFAULT 0;

UPDATE control_center SET 
    cost_gsm_subscription_monthly = COALESCE(cost_gsm_subscription_monthly, 0),
    cost_gsm_device = COALESCE(cost_gsm_device, 0),
    cost_gsm_installation = COALESCE(cost_gsm_installation, 0),
    cost_hook_installation = COALESCE(cost_hook_installation, 0),
    cost_grid_dismantling = COALESCE(cost_grid_dismantling, 0),
    cost_registration = COALESCE(cost_registration, 0),
    cost_sales_prep = COALESCE(cost_sales_prep, 0);
