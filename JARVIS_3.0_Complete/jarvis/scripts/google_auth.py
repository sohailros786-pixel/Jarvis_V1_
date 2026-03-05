"""
Run this once to get your Google OAuth2 refresh token.
Usage: python scripts/google_auth.py
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
]

# You need a client_secrets.json from Google Cloud Console
flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
creds = flow.run_local_server(port=0)

print("\n=== Add these to your .env ===")
print(f"GOOGLE_CLIENT_ID={creds.client_id}")
print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
