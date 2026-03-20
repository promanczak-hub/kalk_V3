-- Migration: calculation_jobs tracking table
-- Purpose: Track Celery task status per vehicle without silent failures

CREATE TABLE IF NOT EXISTS public.calculation_jobs (
    vehicle_id      UUID        NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    status          TEXT        NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
    error_code      TEXT,       -- 'NO_SAMAR_CLASS', 'NO_BASE_PRICE', 'TIMEOUT', 'CALC_ERROR'
    error_detail    TEXT,       -- human-readable detail for UI
    queued_at       TIMESTAMPTZ DEFAULT now(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    celery_task_id  TEXT,
    monthly_price_net NUMERIC,  -- stored on success for quick stats
    PRIMARY KEY (vehicle_id)
);

-- Index for filtering by status (dashboard queries)
CREATE INDEX IF NOT EXISTS idx_calculation_jobs_status ON public.calculation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_calculation_jobs_queued_at ON public.calculation_jobs(queued_at DESC);

-- RLS: any authenticated user can read, only service_role can write
ALTER TABLE public.calculation_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "calculation_jobs_read" ON public.calculation_jobs
    FOR SELECT TO authenticated USING (true);

-- Function: upsert job status (called from Python backend)
CREATE OR REPLACE FUNCTION public.upsert_calculation_job(
    p_vehicle_id     UUID,
    p_status         TEXT,
    p_error_code     TEXT DEFAULT NULL,
    p_error_detail   TEXT DEFAULT NULL,
    p_celery_task_id TEXT DEFAULT NULL,
    p_monthly_price  NUMERIC DEFAULT NULL
) RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    INSERT INTO public.calculation_jobs (
        vehicle_id, status, error_code, error_detail,
        celery_task_id, monthly_price_net,
        queued_at, started_at, finished_at
    ) VALUES (
        p_vehicle_id,
        p_status,
        p_error_code,
        p_error_detail,
        p_celery_task_id,
        p_monthly_price,
        CASE WHEN p_status = 'queued' THEN now() ELSE NULL END,
        CASE WHEN p_status = 'running' THEN now() ELSE NULL END,
        CASE WHEN p_status IN ('done', 'failed') THEN now() ELSE NULL END
    )
    ON CONFLICT (vehicle_id) DO UPDATE SET
        status          = EXCLUDED.status,
        error_code      = EXCLUDED.error_code,
        error_detail    = EXCLUDED.error_detail,
        celery_task_id  = COALESCE(EXCLUDED.celery_task_id, calculation_jobs.celery_task_id),
        monthly_price_net = COALESCE(EXCLUDED.monthly_price_net, calculation_jobs.monthly_price_net),
        queued_at       = CASE WHEN EXCLUDED.status = 'queued' THEN now() ELSE calculation_jobs.queued_at END,
        started_at      = CASE WHEN EXCLUDED.status = 'running' THEN now() ELSE calculation_jobs.started_at END,
        finished_at     = CASE WHEN EXCLUDED.status IN ('done', 'failed') THEN now() ELSE calculation_jobs.finished_at END;
END;
$$;
