from supabase import create_client

url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NTU2MDEsImV4cCI6MjA4NzMzMTYwMX0.lBqpkkMGob1eODejdjaNksqlRkW5DSjh2A2yCQwcydQ"
client = create_client(url, key)

res = (
    client.table("vehicle_synthesis")
    .select("id, brand, model, verification_status, semantic_embedding, synthesis_data")
    .execute()
)

targets = []
for r in res.data:
    sd = r.get("synthesis_data") or {}
    samar_cat = sd.get("mapped_ai_data", {}).get("samar_category", "") or ""
    if "ŚREDNIA" in samar_cat or "SREDNIA" in samar_cat or "SUV" in samar_cat:
        if "Terenowo-rekreacyjne" in samar_cat and "D" in samar_cat:
            has_emb = r.get("semantic_embedding") is not None
            targets.append(
                (r["brand"], r["model"], samar_cat, has_emb, r["verification_status"])
            )

print(f"Pojazdy w tej klasie: {len(targets)}")
has_embs = sum(1 for t in targets if t[3])
completed = sum(1 for t in targets if t[4] == "completed")
print(f"Z embeddingami: {has_embs}, ze statusem completed: {completed}")
for t in targets:
    print(f"- {t[0]} {t[1]} (Emb: {t[3]}, Status: {t[4]})")
