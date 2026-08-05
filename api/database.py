import os
from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient

# Load environment variables (useful for local development)
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
# REQ-SEC-3: Utilizes the service_role key to prevent public access bypasses
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_client: AsyncClient = None

async def get_supabase() -> AsyncClient:
    """
    Dependency provider that returns an initialized asynchronous Supabase client.
    Reuses a single client instance after initial async creation.
    """
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Database configuration missing. "
                "Ensure SUPABASE_URL and SUPABASE_KEY environment variables are set."
            )
        _client = await acreate_client(SUPABASE_URL, SUPABASE_KEY)
    return _client
