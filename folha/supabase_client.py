import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

supabase_url: str = os.getenv("secret_key")
supabase_key: str = os.getenv("api_key")

if not supabase_url or not supabase_key:
    raise ValueError("Credenciais do Supabase não encontradas no .env")

supabase: Client = create_client(supabase_url, supabase_key)