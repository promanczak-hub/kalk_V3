-- Enable Realtime for vehicle_synthesis table
begin;
  -- remove the supabase_realtime publication if it exists
  drop publication if exists supabase_realtime;
  -- re-create the publication
  create publication supabase_realtime;
commit;

-- add table to the publication
alter publication supabase_realtime add table public.vehicle_synthesis;
