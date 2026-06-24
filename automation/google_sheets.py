import json
import logging
import os
import re

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from core import models

logger = logging.getLogger(__name__)

SPREADSHEET_URL_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")
SPREADSHEET_ID_RE = re.compile(r"^[a-zA-Z0-9-_]{20,}$")


def extract_spreadsheet_id(value: str | None) -> str | None:
    """Accept a Google Sheets URL or raw spreadsheet ID and return the ID."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    url_match = SPREADSHEET_URL_RE.search(raw)
    spreadsheet_id = url_match.group(1) if url_match else raw
    if not SPREADSHEET_ID_RE.match(spreadsheet_id):
        raise ValueError("Некорректный ID Google таблицы")
    return spreadsheet_id


def _to_float(value) -> float:
    return float(value or 0)


def _to_int(value) -> int:
    return int(value or 0)


class GoogleSheetsService:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        self.creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
        self.service = None
        self.service_account_email = None

        if os.path.exists(self.creds_path):
            creds = Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
            self.service_account_email = getattr(creds, "service_account_email", None) or self._read_client_email()
            self.service = build("sheets", "v4", credentials=creds)
        else:
            logger.warning(
                "Google Service Account file not found at %s. Sheets export will be disabled.",
                self.creds_path,
            )

    @property
    def configured(self) -> bool:
        return self.service is not None

    def _read_client_email(self) -> str | None:
        try:
            with open(self.creds_path, "r", encoding="utf-8") as fh:
                return json.load(fh).get("client_email")
        except (OSError, json.JSONDecodeError):
            return None

    def _require_service(self):
        if not self.service:
            raise RuntimeError(
                "Google Sheets не настроен на сервере: добавьте service account JSON и GOOGLE_APPLICATION_CREDENTIALS."
            )

    def check_access(self, spreadsheet_id: str) -> dict:
        self._require_service()
        spreadsheet_id = extract_spreadsheet_id(spreadsheet_id)
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="properties/title,spreadsheetUrl",
        ).execute()
        return {
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_title": spreadsheet.get("properties", {}).get("title"),
            "spreadsheet_url": spreadsheet.get("spreadsheetUrl"),
        }

    def export_all(self, spreadsheet_id: str, client_id: str, db: Session) -> dict:
        self._require_service()
        spreadsheet_id = extract_spreadsheet_id(spreadsheet_id)
        return {
            "raw_rows": self.export_raw_data(spreadsheet_id, client_id, db),
            "weekly_rows": self.export_weekly_reports(spreadsheet_id, client_id, db),
            "monthly_rows": self.export_monthly_reports(spreadsheet_id, client_id, db),
            "goals_rows": self.export_metrika_goals(spreadsheet_id, client_id, db),
        }

    def export_raw_data(self, spreadsheet_id: str, client_id: str, db: Session) -> int:
        """
        Export full Yandex and VK daily stats history to Raw Data.
        """
        self._require_service()

        yandex_data = (
            db.query(models.YandexStats)
            .filter_by(client_id=client_id)
            .order_by(models.YandexStats.date.asc(), models.YandexStats.campaign_name.asc())
            .all()
        )
        vk_data = (
            db.query(models.VKStats)
            .filter_by(client_id=client_id)
            .order_by(models.VKStats.date.asc(), models.VKStats.campaign_name.asc())
            .all()
        )
        avito_data = (
            db.query(models.AvitoStats)
            .filter_by(client_id=client_id)
            .order_by(models.AvitoStats.date.asc(), models.AvitoStats.campaign_name.asc())
            .all()
        )

        rows = [["Date", "Platform", "Campaign", "Impressions", "Clicks", "Cost", "Conversions"]]

        for item in yandex_data:
            rows.append([
                str(item.date),
                "Yandex Direct",
                item.campaign_name or "",
                _to_int(item.impressions),
                _to_int(item.clicks),
                _to_float(item.cost),
                _to_int(item.conversions),
            ])

        for item in vk_data:
            rows.append([
                str(item.date),
                "VK Ads",
                item.campaign_name or "",
                _to_int(item.impressions),
                _to_int(item.clicks),
                _to_float(item.cost),
                _to_int(item.conversions),
            ])

        for item in avito_data:
            rows.append([
                str(item.date),
                "Avito",
                item.campaign_name or "",
                _to_int(item.impressions),
                _to_int(item.clicks),
                _to_float(item.cost),
                _to_int(item.conversions),
            ])

        self._write_to_sheet(spreadsheet_id, "Raw Data", rows)
        return max(len(rows) - 1, 0)

    def export_reports(self, spreadsheet_id: str, client_id: str, db: Session) -> dict:
        """
        Backward-compatible helper used by older sync code.
        """
        return {
            "weekly_rows": self.export_weekly_reports(spreadsheet_id, client_id, db),
            "monthly_rows": self.export_monthly_reports(spreadsheet_id, client_id, db),
        }

    def export_weekly_reports(self, spreadsheet_id: str, client_id: str, db: Session) -> int:
        self._require_service()
        weekly = (
            db.query(models.WeeklyReport)
            .filter_by(client_id=client_id)
            .order_by(models.WeeklyReport.week_start.asc())
            .all()
        )
        rows = [["Week Start", "Week End", "Cost", "Clicks", "Conversions", "CPC", "CPA"]]
        for r in weekly:
            rows.append([
                str(r.week_start),
                str(r.week_end),
                _to_float(r.total_cost),
                _to_int(r.total_clicks),
                _to_int(r.total_conversions),
                _to_float(r.avg_cpc),
                _to_float(r.avg_cpa),
            ])

        self._write_to_sheet(spreadsheet_id, "Weekly Reports", rows)
        return max(len(rows) - 1, 0)

    def export_monthly_reports(self, spreadsheet_id: str, client_id: str, db: Session) -> int:
        self._require_service()
        monthly = (
            db.query(models.MonthlyReport)
            .filter_by(client_id=client_id)
            .order_by(models.MonthlyReport.year.asc(), models.MonthlyReport.month.asc())
            .all()
        )
        rows = [["Year", "Month", "Cost", "Clicks", "Conversions", "CPC", "CPA"]]
        for r in monthly:
            rows.append([
                _to_int(r.year),
                _to_int(r.month),
                _to_float(r.total_cost),
                _to_int(r.total_clicks),
                _to_int(r.total_conversions),
                _to_float(r.avg_cpc),
                _to_float(r.avg_cpa),
            ])

        self._write_to_sheet(spreadsheet_id, "Monthly Report", rows)
        return max(len(rows) - 1, 0)

    def export_metrika_goals(
        self,
        spreadsheet_id: str,
        client_id: str,
        db: Session,
        integration_id: str = None,
    ) -> int:
        """
        Export Metrika goals data. Optionally filter by integration_id.
        """
        self._require_service()

        query = db.query(models.MetrikaGoals).filter_by(client_id=client_id)
        if integration_id:
            query = query.filter_by(integration_id=integration_id)

        goals = query.order_by(models.MetrikaGoals.date.asc(), models.MetrikaGoals.goal_name.asc()).all()
        rows = [["Date", "Goal ID", "Goal Name", "Conversions", "Integration ID"]]
        for g in goals:
            rows.append([
                str(g.date),
                g.goal_id,
                g.goal_name or "",
                _to_int(g.conversion_count),
                str(g.integration_id) if g.integration_id else "",
            ])

        self._write_to_sheet(spreadsheet_id, "Goals", rows)
        return max(len(rows) - 1, 0)

    def _a1(self, sheet_name: str, cell: str = "A1") -> str:
        escaped = sheet_name.replace("'", "''")
        return f"'{escaped}'!{cell}"

    def _write_to_sheet(self, spreadsheet_id: str, sheet_name: str, values: list):
        self._ensure_sheet_exists(spreadsheet_id, sheet_name)
        self.service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=self._a1(sheet_name, "A:Z"),
            body={},
        ).execute()
        self.service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=self._a1(sheet_name),
            valueInputOption="RAW",
            body={"values": values},
        ).execute()
        self._format_sheet(spreadsheet_id, sheet_name, len(values[0]) if values else 1)

    def _ensure_sheet_exists(self, spreadsheet_id: str, sheet_name: str):
        spreadsheet = self.service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(sheetId,title))",
        ).execute()
        sheets = {
            s["properties"]["title"]: s["properties"]["sheetId"]
            for s in spreadsheet.get("sheets", [])
        }
        if sheet_name in sheets:
            return sheets[sheet_name]

        response = self.service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        ).execute()
        sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
        logger.info("Created new sheet: %s in %s", sheet_name, spreadsheet_id)
        return sheet_id

    def _format_sheet(self, spreadsheet_id: str, sheet_name: str, column_count: int):
        try:
            sheet_id = self._ensure_sheet_exists(spreadsheet_id, sheet_name)
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": 0,
                                    "endRowIndex": 1,
                                    "startColumnIndex": 0,
                                    "endColumnIndex": column_count,
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "textFormat": {"bold": True},
                                        "backgroundColor": {"red": 0.93, "green": 0.95, "blue": 0.98},
                                    }
                                },
                                "fields": "userEnteredFormat(textFormat,backgroundColor)",
                            }
                        },
                        {
                            "autoResizeDimensions": {
                                "dimensions": {
                                    "sheetId": sheet_id,
                                    "dimension": "COLUMNS",
                                    "startIndex": 0,
                                    "endIndex": column_count,
                                }
                            }
                        },
                    ]
                },
            ).execute()
        except Exception as exc:
            logger.warning("Could not format Google Sheet %s: %s", sheet_name, exc)
