from dotenv import load_dotenv

load_dotenv()
from core.database import supabase
from core.embeddings import generate_embedding, build_vehicle_document

vid = "8f4b8b89-f6e1-4390-85ad-e319734062f7"
v_resp = (
    supabase.table("vehicle_synthesis")
    .select("brand, model, synthesis_data")
    .eq("id", vid)
    .execute()
)
row = v_resp.data[0]
doc = build_vehicle_document(
    row.get("brand", ""), row.get("model", ""), row.get("synthesis_data", {})
)

print(f"DEBUG text length = {len(doc)}")
vec = generate_embedding(doc)
print(f"Success from generate_embedding: length {len(vec) if vec else 'None'}")
