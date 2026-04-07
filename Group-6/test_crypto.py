import sys
sys.path.insert(0, 'zero_trust_vpn')
from crypto_utils import encrypt_payload, decrypt_payload, load_public_key, load_private_key

pub  = load_public_key('zero_trust_vpn/keys/public.pem')
priv = load_private_key('zero_trust_vpn/keys/private.pem')

original = '{"jwt": "test.token.here", "path": "/dashboard"}'
wire = encrypt_payload(original, pub)
recovered = decrypt_payload(wire[4:], priv)

print('Original: ', original)
print('Recovered:', recovered)
print('Match:', original == recovered)
print(f'Wire bytes: {len(wire)} (was {len(original)} plaintext)')
