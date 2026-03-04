from core.database import supabase

ubezpieczenia = supabase.table("ltr_admin_ubezpieczenia").select("*").limit(1).execute()
print("ubezpieczenia:", ubezpieczenia.data)

szkodowe = (
    supabase.table("ltr_admin_wspolczynniki_szkodowe").select("*").limit(1).execute()
)
print("szkodowe:", szkodowe.data)
