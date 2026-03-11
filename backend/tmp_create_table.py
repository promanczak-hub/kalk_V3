import asyncio


async def run():
    sql = """
    CREATE TABLE IF NOT EXISTS public.document_library (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        file_name VARCHAR(255) NOT NULL,
        document_url TEXT NOT NULL,
        document_type VARCHAR(50) NOT NULL,
        brand VARCHAR(100),
        model VARCHAR(100),
        valid_from DATE,
        description TEXT,
        digital_twin JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
    );

    ALTER TABLE public.document_library ENABLE ROW LEVEL SECURITY;

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = 'document_library' AND policyname = 'Enable read access for all users'
        ) THEN
            CREATE POLICY "Enable read access for all users" ON public.document_library FOR SELECT USING (true);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = 'document_library' AND policyname = 'Enable insert access for all users'
        ) THEN
            CREATE POLICY "Enable insert access for all users" ON public.document_library FOR INSERT WITH CHECK (true);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = 'document_library' AND policyname = 'Enable update access for all users'
        ) THEN
            CREATE POLICY "Enable update access for all users" ON public.document_library FOR UPDATE USING (true);
        END IF;

        IF NOT EXISTS (
            SELECT 1 FROM pg_policies WHERE tablename = 'document_library' AND policyname = 'Enable delete access for all users'
        ) THEN
            CREATE POLICY "Enable delete access for all users" ON public.document_library FOR DELETE USING (true);
        END IF;
    END
    $$;
    """

    # Supabase Data API doesn't support raw SQL execution directly in all versions,
    # but we can try calling a predefined RPC if we had one.
    # Since we can't execute raw DDL via REST easily, we will create an RPC in python using asyncpg/psycopg2
    # but wait, we already failed psycopg2. Let's try to find an RPC `exec_sql` or just create one.
    pass


if __name__ == "__main__":
    asyncio.run(run())
