import os, json
os.environ["COUNTRY"] = "SA"
from config import get_settings
from countries import get_country_config
import gspread
from google.oauth2.service_account import Credentials

settings = get_settings()
creds_json = os.getenv("GOOGLE_CREDENTIALS")
if creds_json:
    creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=settings.scopes)
else:
    creds = Credentials.from_service_account_file(settings.google_credentials_path, scopes=settings.scopes)

client = gspread.authorize(creds)
ws = client.open("Taager").worksheet("Products_SA")
vals = ws.get_all_values()
print(f"Total rows (including header): {len(vals)}")
if len(vals) > 0:
    print(f"Headers: {vals[0]}")
    if len(vals) > 1:
        print(f"Row 2 (first product): {vals[1]}")
    else:
        print("EMPTY - only headers")
