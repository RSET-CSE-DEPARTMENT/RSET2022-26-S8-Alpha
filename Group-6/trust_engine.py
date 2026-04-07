from logger import log_trust_change

def reduce_trust(username, reason):
    old = trust_scores[username]

    if reason == "FAILED_LOGIN":
        trust_scores[username] -= W_FAILED_LOGIN
    elif reason == "FAILED_OTP":
        trust_scores[username] -= W_FAILED_OTP
    elif reason == "RBAC_VIOLATION":
        trust_scores[username] -= W_RBAC
    elif reason == "RATE_LIMIT":
        trust_scores[username] -= W_RATE

    trust_scores[username] = max(trust_scores[username], MIN_TRUST)

    # ✅ LOG TRUST CHANGE
    log_trust_change(username, old, trust_scores[username], reason)

    return trust_scores[username]
