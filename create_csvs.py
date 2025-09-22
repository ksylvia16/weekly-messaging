import gspread
import pandas as pd
import os
from oauth2client.service_account import ServiceAccountCredentials

# 1. Setup credentials
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# 2. Open the spreadsheet
spreadsheet = client.open("Curriculum Schedules All Tracks") 

# 3. Create output folder
os.makedirs("csv_data", exist_ok=True)

# 4. Loop through each worksheet
for ws in spreadsheet.worksheets():
    name = ws.title
    print(f"Exporting: {name}")

    # Pull a limited range
    values = ws.get_all_values("A1:I25")
    if not values:
        continue

    # Convert to DataFrame and save
    df = pd.DataFrame(values[1:], columns=values[0])
    csv_path = f"./csv_data/{name}.csv"
    df.to_csv(csv_path, index=False)
    print(f"✅ Saved to {csv_path}")
