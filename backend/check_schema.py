from core.database import supabase

def main():
    try:
        data = supabase.table('ltr_admin_parametry').select('*').limit(1).execute().data
        print(data)
    except Exception as e:
        print(e)
        
    try:
        data = supabase.table('LTRAdminParametry_czak').select('*').limit(1).execute().data
        print("czak", data)
    except Exception:
        pass

if __name__ == '__main__':
    main()
