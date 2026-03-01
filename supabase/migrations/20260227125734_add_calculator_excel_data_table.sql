create table public.calculator_excel_data (
    id uuid not null default gen_random_uuid (),
    sheet_name text not null,
    row_data jsonb not null default '[]'::jsonb,
    updated_at timestamp with time zone not null default now(),
    constraint calculator_excel_data_pkey primary key (id),
    constraint calculator_excel_data_sheet_name_key unique (sheet_name)
);

-- RLS policies
alter table public.calculator_excel_data enable row level security;

create policy "Allow public read access on calculator_excel_data" 
on public.calculator_excel_data 
for select 
to public 
using (true);

create policy "Allow anon insert/update on calculator_excel_data"
on public.calculator_excel_data
for all
to anon
using (true)
with check (true);
