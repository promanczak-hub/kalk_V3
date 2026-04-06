from core.database import supabase

res = (
    supabase.schema("reverse_search")
    .table("model_document_sources")
    .select("extraction_error, file_type, document_type")
    .ilike("model_family", "%terramar%")
    .execute()
)
for r in res.data:
    if r.get("extraction_error"):
        print(f"File: {r.get('file_type')} / {r.get('document_type')}")
        print(r["extraction_error"])
        print("-" * 40)
