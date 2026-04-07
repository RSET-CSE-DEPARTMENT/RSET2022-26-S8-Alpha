import secrets
import time

REFRESH_TOKENS = {}

REFRESH_LIFETIME = 60 * 60  # 1 hour

def issue_refresh_token(username):
    token = secrets.token_urlsafe(32)
    REFRESH_TOKENS[token] = {
        "username": username,
        "expires": time.time() + REFRESH_LIFETIME
    }
    return token

def validate_refresh_token(token):
    data = REFRESH_TOKENS.get(token)
    if not data:
        return None
    if time.time() > data["expires"]:
        del REFRESH_TOKENS[token]
        return None
    return data["username"]

def revoke_user_tokens(username):
    for t in list(REFRESH_TOKENS.keys()):
        if REFRESH_TOKENS[t]["username"] == username:
            del REFRESH_TOKENS[t]
