from supabase import create_client
from pathlib import Path
from dotenv import dotenv_values
import logging

logger = logging.getLogger(__name__)

# Explicitly load from frontend/.env so the correct legacy JWT anon key is
# always used, regardless of any SUPABASE_KEY set in the process environment
# (e.g. the root .env sb_publishable_ key being sourced in the shell).
_env_path = Path(__file__).resolve().parent / ".env"
_env = dotenv_values(_env_path)

_SUPABASE_URL = _env.get("SUPABASE_URL", "")
_SUPABASE_KEY = _env.get("SUPABASE_KEY", "")

supabase = create_client(_SUPABASE_URL, _SUPABASE_KEY)

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