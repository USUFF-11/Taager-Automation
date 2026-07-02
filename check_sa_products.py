import os
os.environ["COUNTRY"] = "SA"

from config import get_settings
import gspread, json
from google.oauth2.service_account import Credentials

s = get_settings()
creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json:
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=s.scopes)
else:
    creds = Credentials.from_service_account_file(s.google_credentials_path, scopes=s.scopes)

ws = gspread.authorize(creds).open("Taager").worksheet("Products_SA")
vals = ws.get_all_values()
for row in vals[1:6]:
    if row[0]:
        print(f"ID: {row[0]} - {row[3]}")
