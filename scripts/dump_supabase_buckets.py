import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("backend/.env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing Supabase credentials")
    exit(1)

supabase = create_client(url, key)


def get_all_buckets():
    try:
        response = supabase.storage.list_buckets()
        return [b.name for b in response]
    except Exception as e:
        print(f"Failed to list buckets: {e}")
        # fallback to known
        return ["vehicles", "offers_excel"]


def download_folder(bucket_name, prefix="", local_base_dir="dump_buckets"):
    try:
        items = supabase.storage.from_(bucket_name).list(path=prefix)
        for item in items:
            name = item.get("name")
            if not name or name == ".emptyFolderPlaceholder":
                continue

            item_path = f"{prefix}/{name}" if prefix else name
            # Check if it's a folder (size implicitly 0 or lack of metadata usually)
            meta = item.get("metadata")
            if meta is None or item.get("id") is None:
                # it's a folder
                print(f"Folder found: {item_path}")
                download_folder(bucket_name, item_path, local_base_dir)
            else:
                download_file(bucket_name, item_path, local_base_dir)
    except Exception as e:
        print(f"Error listing {prefix} in {bucket_name}: {e}")


def download_file(bucket, file_path, local_base_dir):
    try:
        local_path = os.path.join(local_base_dir, bucket, file_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        print(f"Downloading {bucket}/{file_path} -> {local_path}")
        with open(local_path, "wb") as f:
            res = supabase.storage.from_(bucket).download(file_path)
            f.write(res)
    except Exception as e:
        print(f"Failed to download {file_path}: {e}")


def main():
    buckets = get_all_buckets()
    print(f"Found buckets: {buckets}")
    base_dir = "supabase_buckets_dump"
    os.makedirs(base_dir, exist_ok=True)

    for b in buckets:
        print(f"--- Processing bucket: {b} ---")
        download_folder(b, "", base_dir)


if __name__ == "__main__":
    main()
