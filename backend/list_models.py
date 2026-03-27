from google import genai

project_id = "express-handlorz"
location = "us-central1"

print(f"Connecting to Vertex AI (Project: {project_id}, Region: {location})...")
try:
    client = genai.Client(vertexai=True, project=project_id, location=location)
    print("Found models:")

    # Iterate over available models
    models = client.models.list()
    embed_models = []

    for m in models:
        name = m.name.lower()
        if "embed" in name:
            embed_models.append(m.name)

    if embed_models:
        for em in embed_models:
            print(f"- {em}")
    else:
        print("No embedding models found. Listing first 10 models for context:")
        for m in list(client.models.list())[:10]:
            print(f"- {m.name}")

except Exception as e:
    print(f"Error fetching models: {e}")
