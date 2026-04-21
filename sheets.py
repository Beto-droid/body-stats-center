"""
Google Sheets integration for mi-scale-automation.

Setup instructions:
  1. Go to https://console.cloud.google.com/ and create a new project.
  2. Enable the "Google Sheets API" and "Google Drive API" for that project.
  3. Create a Service Account (IAM & Admin > Service Accounts > Create).
  4. Create a JSON key for that service account and download it.
  5. Save the JSON key file as "service_account.json" in this folder.
  6. Create a Google Sheet (sheets.google.com) and name it "Mi Scale Log" (or change SHEET_NAME below).
  7. Share that sheet with the service account email (e.g. myaccount@myproject.iam.gserviceaccount.com) with Editor permissions.
  8. Done! The script will automatically append a new row each time a valid measurement is received.
"""

import logging
from pathlib import Path

import gspread

from body_composition import BodyComposition

SHEET_NAME = "Mi Scale Log"
CREDENTIALS_FILE = Path(__file__).parent / "service_account.json"

HEADERS = [
    "Timestamp", "Weight (kg)", "Impedance (ohm)", "Stabilized",
    "BMI", "Body Fat (%)", "Muscle Mass (kg)", "Bone Mass (kg)",
    "Water (%)", "Visceral Fat", "BMR (kcal/day)", "Lean Mass (kg)", "Protein (%)",
]

logger = logging.getLogger(__name__)

_worksheet = None


def _get_worksheet():
    global _worksheet
    if _worksheet is not None:
        return _worksheet

    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"Google service account credentials not found at {CREDENTIALS_FILE}. "
            "See sheets.py for setup instructions."
        )

    gc = gspread.service_account(filename=str(CREDENTIALS_FILE))
    spreadsheet = gc.open(SHEET_NAME)
    worksheet = spreadsheet.sheet1

    if worksheet.row_count == 0 or worksheet.cell(1, 1).value != HEADERS[0]:
        worksheet.insert_row(HEADERS, index=1)

    _worksheet = worksheet
    return _worksheet


def append_measurement(
    timestamp: str,
    weight: float,
    impedance: int,
    stabilized: bool,
    comp: BodyComposition,
) -> None:
    """Appends a full measurement row to the Google Sheet."""
    try:
        worksheet = _get_worksheet()
        row = [
            timestamp, weight, impedance, str(stabilized),
            comp.bmi, comp.fat_percent, comp.muscle_mass_kg, comp.bone_mass_kg,
            comp.water_percent, comp.visceral_fat, comp.bmr_kcal, comp.lean_mass_kg, comp.protein_percent,
        ]
        worksheet.append_row(row)
        logger.info(f"📊 Saved to Google Sheets: {row}")
    except Exception as e:
        logger.error(f"Failed to save to Google Sheets: {e}")
