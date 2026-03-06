"""
integrations/hubspot.py
Real HubSpot CRM API client.
Docs: https://developers.hubspot.com/docs/api/crm/deals
"""
import httpx
from typing import Optional
from integrations.base import BaseCRMProvider
from config.settings import settings


HUBSPOT_BASE_URL = "https://api.hubapi.com"


class HubSpotIntegration(BaseCRMProvider):
    def __init__(self):
        self.token = settings.hubspot_access_token
        self.headers = {
            "Authorization": f"Bearer {self.token or ''}",
            "Content-Type": "application/json",
        }

    def _check_token(self):
        if not self.token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN not set. Use mock mode or provide a real token.")

    def get_deal_data(self) -> list:
        """
        Fetch all deals from HubSpot CRM with key properties.
        Returns normalized list of deal dicts.
        """
        self._check_token()

        properties = [
            "dealname", "amount", "dealstage", "closedate",
            "hs_deal_stage_probability", "pipeline", "industry",
            "notes_last_updated", "hs_lastmodifieddate",
            "num_associated_contacts", "closed_lost_reason"
        ]

        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/deals",
                headers=self.headers,
                params={
                    "limit": 100,
                    "properties": ",".join(properties),
                    "archived": False,
                }
            )
            response.raise_for_status()
            data = response.json()

        deals = []
        for item in data.get("results", []):
            props = item.get("properties", {})
            deals.append({
                "id": item.get("id"),
                "name": props.get("dealname", ""),
                "value": float(props.get("amount") or 0),
                "stage": props.get("dealstage", ""),
                "close_date": props.get("closedate", ""),
                "win_probability": float(props.get("hs_deal_stage_probability") or 0),
                "last_activity": props.get("hs_lastmodifieddate", ""),
                "industry": props.get("industry", ""),
                "loss_reason": props.get("closed_lost_reason", ""),
                "contact_count": int(props.get("num_associated_contacts") or 0),
                "source": "hubspot",
            })

        return deals

    def create_deal(self, deal_data: dict) -> dict:
        """Create a new deal in HubSpot."""
        self._check_token()

        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/deals",
                headers=self.headers,
                json={"properties": deal_data}
            )
            response.raise_for_status()
            return response.json()

    def update_deal(self, deal_id: str, updates: dict) -> dict:
        """Update an existing deal by ID."""
        self._check_token()

        with httpx.Client(timeout=15.0) as client:
            response = client.patch(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/deals/{deal_id}",
                headers=self.headers,
                json={"properties": updates}
            )
            response.raise_for_status()
            return response.json()

    def log_activity(self, deal_id: str, activity: dict) -> dict:
        """Log a note/activity against a deal."""
        self._check_token()

        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{HUBSPOT_BASE_URL}/crm/v3/objects/notes",
                headers=self.headers,
                json={
                    "properties": {
                        "hs_note_body": activity.get("body", ""),
                        "hs_timestamp": activity.get("timestamp", ""),
                    },
                    "associations": [{
                        "to": {"id": deal_id},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}]
                    }]
                }
            )
            response.raise_for_status()
            return response.json()
