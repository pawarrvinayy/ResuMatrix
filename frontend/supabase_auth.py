from supabase import create_client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def register_user(email: str, password: str, username: str) -> bool:
    try:
        result = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username
                }

            }
        })
        if result and result.user:
            # Optionally store metadata like username
            # supabase.auth.update_user({"data": {"username": username}})
            return True
        return False
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise

def authenticate_user(email: str, password: str):
    try:
        result = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if result and result.user:
            return {
                "email": result.user.email,
                "username": result.user.user_metadata.get("username", "User"),
                "id": result.user.id
            }
        return None
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise