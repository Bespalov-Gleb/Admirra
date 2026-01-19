import os
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from core import models

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
        self.service = None
        
        if os.path.exists(self.creds_path):
            creds = Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
            self.service = build('sheets', 'v4', credentials=creds)
        else:
            logger.warning(f"Google Service Account file not found at {self.creds_path}. Sheets export will be disabled.")

    def export_raw_data(self, spreadsheet_id: str, client_id: str, db: Session):
        """
        Exports Yandex and VK raw data to the specified spreadsheet.
        """
        if not self.service: return

        # Fetch data
        yandex_data = db.query(models.YandexStats).filter_by(client_id=client_id).all()
        vk_data = db.query(models.VKStats).filter_by(client_id=client_id).all()

        rows = [["Date", "Platform", "Campaign", "Impressions", "Clicks", "Cost", "Conversions"]]
        
        for item in yandex_data:
            rows.append([str(item.date), "Yandex", item.campaign_name, item.impressions, item.clicks, float(item.cost), item.conversions])
            
        for item in vk_data:
            rows.append([str(item.date), "VK", item.campaign_name, item.impressions, item.clicks, float(item.cost), item.conversions])

        self._write_to_sheet(spreadsheet_id, "Raw Data!A1", rows)

    def export_reports(self, spreadsheet_id: str, client_id: str, db: Session):
        """
        Exports weekly and monthly reports.
        """
        if not self.service: return

        weekly = db.query(models.WeeklyReport).filter_by(client_id=client_id).all()
        rows = [["Week Start", "Week End", "Cost", "Clicks", "Conversions", "CPC", "CPA"]]
        for r in weekly:
            rows.append([str(r.week_start), str(r.week_end), float(r.total_cost), r.total_clicks, r.total_conversions, float(r.avg_cpc), float(r.avg_cpa)])
        
        self._write_to_sheet(spreadsheet_id, "Weekly Reports!A1", rows)

    def export_metrika_goals(self, spreadsheet_id: str, client_id: str, db: Session, integration_id: str = None):
        """
        Exports Metrika goals data.
        Optionally filter by integration_id to export goals for a specific integration/profile.
        """
        if not self.service: return

        query = db.query(models.MetrikaGoals).filter_by(client_id=client_id)
        
        # Filter by integration_id if provided
        if integration_id:
            query = query.filter_by(integration_id=integration_id)
        
        goals = query.all()
        rows = [["Date", "Goal ID", "Goal Name", "Conversions", "Integration ID"]]
        for g in goals:
            rows.append([str(g.date), g.goal_id, g.goal_name, g.conversion_count, str(g.integration_id) if g.integration_id else "N/A"])
        
        self._write_to_sheet(spreadsheet_id, "Goals!A1", rows)

    def _write_to_sheet(self, spreadsheet_id: str, range_name: str, values: list):
        try:
            # First ensure the sheet exists
            sheet_name = range_name.split('!')[0]
            self._ensure_sheet_exists(spreadsheet_id, sheet_name)

            body = {'values': values}
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, 
                range=range_name,
                valueInputOption='RAW', 
                body=body
            ).execute()
        except Exception as e:
            logger.error(f"Error writing to Google Sheets {range_name}: {e}")

    def _ensure_sheet_exists(self, spreadsheet_id: str, sheet_name: str):
        try:
            spreadsheet = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = [s['properties']['title'] for s in spreadsheet.get('sheets', [])]
            if sheet_name not in sheets:
                body = {
                    'requests': [
                        {
                            'addSheet': {
                                'properties': {
                                    'title': sheet_name
                                }
                            }
                        }
                    ]
                }
                self.service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
                logger.info(f"Created new sheet: {sheet_name} in {spreadsheet_id}")
        except Exception as e:
            logger.error(f"Error ensuring sheet exists {sheet_name}: {e}")
