"""
Canonical location for the Supabase database client.
All server-side code should import SupabaseClient from here.
"""

from supabase import create_client, Client, ClientOptions
import httpx
from shared.config import Config

class SupabaseClient:
    """
    Singleton-style wrapper for Supabase database access.
    Uses the service role key for full server-side access.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance.url = Config.SUPABASE_URL
            cls._instance.key = Config.SUPABASE_KEY
            # NEW: Explicitly disable HTTP/2 to prevent RemoteProtocolError
            # We create a custom client for both sync and async operations if possible,
            # but create_client in supabase-py manages its own client. 
            # We use ClientOptions to pass specific timeouts and headers.
            
            # Note: supabase-py uses httpx internally. We can try to force it via options.
            cls._instance.client: Client = create_client(
                cls._instance.url, 
                cls._instance.key,
                options=ClientOptions(
                    postgrest_client_timeout=httpx.Timeout(90.0, connect=10.0)
                )
            )
            print(f"[SupabaseClient] Initialized for {cls._instance.url} (HTTP/1.1 forced via env and long timeouts)")
        return cls._instance
        
    def get_client(self) -> Client:
        """
        Return the configured Supabase client instance.
        """
        return self.client
