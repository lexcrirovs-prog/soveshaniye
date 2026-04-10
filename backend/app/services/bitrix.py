import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


def _parse_datetime(value: str) -> datetime:
    """Parse datetime string from Bitrix24 API."""
    if not value:
        return datetime.now()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.now()


class BitrixClient:
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = (webhook_url or settings.bitrix_webhook_url).rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def _call(self, method: str, params: Optional[dict] = None) -> dict:
        url = f"{self.webhook_url}/{method}"
        response = self.client.post(url, json=params or {})
        response.raise_for_status()
        return response.json()

    def _call_all(self, method: str, params: Optional[dict] = None) -> list[dict]:
        """Fetch all pages from Bitrix24 API (pagination by 50)."""
        params = dict(params or {})
        results = []
        start = 0

        while True:
            params["start"] = start
            data = self._call(method, params)
            items = data.get("result", [])
            if isinstance(items, dict):
                items = list(items.values()) if items else []
            results.extend(items)

            total = data.get("total", 0)
            next_val = data.get("next")
            if next_val is None or len(results) >= total:
                break
            start = next_val

        return results

    def get_employees(self, department_id: Optional[int] = None) -> list[dict]:
        params: dict[str, Any] = {
            "FILTER": {"ACTIVE": True},
            "SELECT": ["ID", "NAME", "LAST_NAME", "WORK_POSITION", "UF_DEPARTMENT"],
        }
        if department_id:
            params["FILTER"]["UF_DEPARTMENT"] = department_id

        items = self._call_all("user.get", params)
        employees = []
        for item in items:
            name_parts = [item.get("NAME", ""), item.get("LAST_NAME", "")]
            employees.append({
                "bitrix_id": int(item["ID"]),
                "name": " ".join(p for p in name_parts if p),
                "position": item.get("WORK_POSITION", ""),
                "department": str(item.get("UF_DEPARTMENT", [""])[0]) if item.get("UF_DEPARTMENT") else "",
            })
        return employees

    def get_deals(self, date_from: datetime, date_to: datetime) -> list[dict]:
        params = {
            "FILTER": {
                ">=DATE_CREATE": date_from.strftime("%Y-%m-%d"),
                "<=DATE_CREATE": date_to.strftime("%Y-%m-%d"),
            },
            "SELECT": ["ID", "TITLE", "ASSIGNED_BY_ID", "STAGE_ID", "OPPORTUNITY", "COMMENTS"],
        }
        items = self._call_all("crm.deal.list", params)
        return [
            {
                "id": int(item["ID"]),
                "title": item.get("TITLE", ""),
                "assigned_by_id": int(item.get("ASSIGNED_BY_ID", 0)),
                "stage_id": item.get("STAGE_ID", ""),
                "opportunity": float(item.get("OPPORTUNITY", 0) or 0),
                "comments": item.get("COMMENTS", ""),
            }
            for item in items
        ]

    def get_calls(self, date_from: datetime, date_to: datetime) -> list[dict]:
        params = {
            "FILTER": {
                ">=CALL_START_DATE": date_from.strftime("%Y-%m-%dT%H:%M:%S"),
                "<=CALL_START_DATE": date_to.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        }
        items = self._call_all("voximplant.statistic.get", params)
        calls = []
        for item in items:
            call_type = int(item.get("CALL_TYPE", 0))
            direction = "incoming" if call_type == 2 else "outgoing"
            calls.append({
                "bitrix_call_id": str(item.get("ID", "")),
                "direction": direction,
                "portal_user_id": int(item.get("PORTAL_USER_ID", 0)),
                "phone_number": item.get("PHONE_NUMBER", ""),
                "duration_sec": int(item.get("CALL_DURATION", 0)),
                "call_date": _parse_datetime(item.get("CALL_START_DATE", "")),
                "record_file_id": item.get("RECORD_FILE_ID"),
                "record_url": item.get("RECORD_URL", ""),
            })
        return calls

    def find_deals_by_phone(self, phone: str) -> list[dict]:
        """Find deals linked to a phone number via contacts or direct phone field."""
        deals = []

        # Try direct deal search by phone
        try:
            params = {
                "FILTER": {"PHONE": phone},
                "SELECT": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY"],
            }
            items = self._call_all("crm.deal.list", params)
            for item in items:
                deals.append({
                    "id": int(item["ID"]),
                    "title": item.get("TITLE", ""),
                    "stage_id": item.get("STAGE_ID", ""),
                    "opportunity": float(item.get("OPPORTUNITY", 0) or 0),
                })
        except Exception:
            logger.debug("No deals found by direct phone search for %s", phone)

        # Try via contacts
        try:
            contact_params = {"FILTER": {"PHONE": phone}, "SELECT": ["ID"]}
            contacts = self._call_all("crm.contact.list", contact_params)
            for contact in contacts:
                contact_id = int(contact["ID"])
                deal_params = {
                    "FILTER": {"CONTACT_ID": contact_id},
                    "SELECT": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY"],
                }
                contact_deals = self._call_all("crm.deal.list", deal_params)
                for item in contact_deals:
                    deal = {
                        "id": int(item["ID"]),
                        "title": item.get("TITLE", ""),
                        "stage_id": item.get("STAGE_ID", ""),
                        "opportunity": float(item.get("OPPORTUNITY", 0) or 0),
                    }
                    if deal["id"] not in {d["id"] for d in deals}:
                        deals.append(deal)
        except Exception:
            logger.debug("No contacts found for phone %s", phone)

        return deals

    def download_audio(self, record_url: str) -> Optional[bytes]:
        """Download audio file from Bitrix24 record URL."""
        if not record_url:
            return None
        try:
            response = self.client.get(record_url, follow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error("Failed to download audio from %s: %s", record_url, e)
            return None

    def close(self):
        self.client.close()


def get_period_dates(period: str) -> tuple[datetime, datetime]:
    """Convert period string to (date_from, date_to) tuple."""
    now = datetime.now()
    date_to = now

    period_map = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "14d": timedelta(days=14),
        "30d": timedelta(days=30),
        "quarter": timedelta(days=90),
        "year": timedelta(days=365),
    }

    delta = period_map.get(period, timedelta(days=7))
    date_from = now - delta
    return date_from, date_to
