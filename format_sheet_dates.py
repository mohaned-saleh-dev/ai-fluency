#!/usr/bin/env python3
"""
Script to format dates in a Google Sheet column to DD/MM/YYYY format.
"""

import gspread
from google.oauth2.service_account import Credentials
import os
import sys

# Google Sheets API scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_credentials():
    """Get Google Sheets API credentials."""
    # Try to get credentials from environment variable or file
    creds_path = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', 'credentials.json')
    
    if os.path.exists(creds_path):
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        return creds
    
    # Try to get from environment variable as JSON string
    creds_json = os.getenv('GOOGLE_SHEETS_CREDENTIALS_JSON')
    if creds_json:
        import json
        creds_info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        return creds
    
    raise FileNotFoundError(
        f"Google Sheets credentials not found. Please either:\n"
        f"1. Set GOOGLE_SHEETS_CREDENTIALS_PATH to point to your credentials.json file, or\n"
        f"2. Set GOOGLE_SHEETS_CREDENTIALS_JSON with the JSON content of your credentials, or\n"
        f"3. Place credentials.json in the current directory.\n\n"
        f"To get credentials:\n"
        f"1. Go to https://console.cloud.google.com/\n"
        f"2. Create a new project or select existing one\n"
        f"3. Enable Google Sheets API and Google Drive API\n"
        f"4. Create a Service Account\n"
        f"5. Download the JSON key file\n"
        f"6. Share your Google Sheet with the service account email"
    )

def format_dates_column(sheet_url: str, column_name: str = "Dates"):
    """
    Format all dates in the specified column to DD/MM/YYYY format.
    
    Args:
        sheet_url: The Google Sheets URL
        column_name: Name of the column to format (default: "Dates")
    """
    try:
        # Get credentials
        creds = get_credentials()
        client = gspread.authorize(creds)
        
        # Extract spreadsheet ID from URL
        # URL format: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit...
        if '/d/' in sheet_url:
            spreadsheet_id = sheet_url.split('/d/')[1].split('/')[0]
        else:
            raise ValueError("Invalid Google Sheets URL format")
        
        # Open the spreadsheet
        print(f"Opening spreadsheet {spreadsheet_id}...")
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get the worksheet by gid if specified in URL
        if '#gid=' in sheet_url:
            gid = sheet_url.split('#gid=')[1].split('&')[0]
            try:
                worksheet = spreadsheet.get_worksheet_by_id(int(gid))
            except Exception:
                worksheet = spreadsheet.sheet1
        else:
            worksheet = spreadsheet.sheet1
        
        print(f"Working with worksheet: {worksheet.title}")
        
        # Find the column with the specified name
        header_row = worksheet.row_values(1)
        try:
            col_index = header_row.index(column_name) + 1  # gspread uses 1-based indexing
        except ValueError:
            raise ValueError(f"Column '{column_name}' not found in the sheet. Available columns: {header_row}")
        
        print(f"Found '{column_name}' column at index {col_index}")
        
        # Get all values in the column
        col_letter = gspread.utils.rowcol_to_a1(1, col_index)[0]  # Get column letter (A, B, C, etc.)
        all_values = worksheet.col_values(col_index)
        
        # Skip header row
        data_values = all_values[1:] if len(all_values) > 1 else []
        
        if not data_values:
            print("No data found in the column (only header row exists)")
            return
        
        print(f"Found {len(data_values)} rows with data")
        
        # Format the entire column at once (from row 2 to the last row with data)
        if data_values:
            print("Updating date formats...")
            
            # Get the last row number
            last_row = len(all_values)
            
            # Format the entire column range (excluding header row)
            # Use batch_update to set number format for the entire column range
            spreadsheet.batch_update({
                'requests': [{
                    'repeatCell': {
                        'range': {
                            'sheetId': worksheet.id,
                            'startRowIndex': 1,  # Start from row 2 (0-indexed, so 1 = row 2)
                            'endRowIndex': last_row,  # End at last row with data
                            'startColumnIndex': col_index - 1,  # Column index (0-indexed)
                            'endColumnIndex': col_index
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'numberFormat': {
                                    'type': 'DATE',
                                    'pattern': 'dd/mm/yyyy'
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.numberFormat'
                    }
                }]
            })
            
            print(f"✅ Successfully formatted column '{column_name}' (rows 2-{last_row}) to DD/MM/YYYY format")
        else:
            print("No data cells found to format")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    sheet_url = "https://docs.google.com/spreadsheets/d/1cKvxrjpCXxL2hRTkRxVhlLmFieooj27NGPV1Lid4Pvg/edit?gid=437158564#gid=437158564"
    format_dates_column(sheet_url, "Dates")

