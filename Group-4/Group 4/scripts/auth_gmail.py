import os
import shutil
from google_auth_oauthlib.flow import InstalledAppFlow

print("Starting Gmail OAuth flow...")
creds_path = "secrets/credentials.json"
if not os.path.exists(creds_path):
    print(f"{creds_path} not found, falling back to credentials.json")
    creds_path = "credentials.json"
    
if not os.path.exists(creds_path):
    print(f"Error: Neither secrets/credentials.json nor credentials.json was found.")
    exit(1)

# Scopes needed for the app
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Run the OAuth flow
flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')

# Save to secrets/token.json
os.makedirs("secrets", exist_ok=True)
with open("secrets/token.json", 'w') as token:
    token.write(creds.to_json())
    print("Saved to secrets/token.json")

# Save to root token.json as well (just in case)
with open("token.json", "w") as token:
    token.write(creds.to_json())
    print("Saved to token.json in root directory")

print("Successfully authenticated and written new token.json files.")
