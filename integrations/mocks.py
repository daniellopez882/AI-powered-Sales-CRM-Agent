"""
integrations/mocks.py
Mock implementations of all integration classes.
Used when USE_MOCK_INTEGRATIONS=true (default in development).
These implement the same abstract interfaces as real clients.
"""
from typing import Optional
from integrations.base import (
    BaseLeadEnrichmentProvider,
    BaseCRMProvider,
    BaseEmailProvider,
    BaseMessagingProvider,
)


class MockApolloIntegration(BaseLeadEnrichmentProvider):
    """Returns realistic mock data matching the real Apollo response schema."""

    def enrich_contact(self, email: str) -> dict:
        domain = email.split("@")[-1] if "@" in email else "example.com"
        return {
            "name": "Sarah Chen",
            "title": "VP of Sales Operations",
            "seniority": "vp",
            "department": "Sales",
            "email": email,
            "linkedin_url": f"https://linkedin.com/in/sarahchen",
            "city": "San Francisco",
            "state": "California",
            "country": "US",
            "company": "TechScale Inc.",
            "industry": "Software",
            "employee_count": 350,
            "revenue_range": "$10M-$50M",
            "website": f"https://www.{domain}",
            "linkedin_company_url": "https://linkedin.com/company/techscale",
            "tech_stack": ["Salesforce", "Outreach", "Gong", "Slack", "AWS"],
            "funding_stage": "Series B",
            "verified": True,
            "source": "mock_apollo",
        }

    def enrich_company(self, domain: str) -> dict:
        return {
            "name": "TechScale Inc.",
            "domain": f"https://www.{domain}",
            "industry": "Software",
            "employee_count": 350,
            "revenue_range": "$10M-$50M",
            "funding_stage": "Series B",
            "tech_stack": ["Salesforce", "Outreach", "Gong"],
            "linkedin_url": "https://linkedin.com/company/techscale",
            "source": "mock_apollo",
        }


class MockHubSpotIntegration(BaseCRMProvider):
    """Returns realistic mock CRM data with diverse deal stages and sizes."""

    def get_deal_data(self) -> list:
        return [
            {
                "id": "deal_001", "name": "TechScale Inc. — Enterprise License",
                "value": 85000, "stage": "Negotiation", "close_date": "2026-03-31",
                "win_probability": 0.75, "last_activity": "2026-03-05",
                "industry": "Software", "loss_reason": None, "contact_count": 3,
                "source": "mock_hubspot",
            },
            {
                "id": "deal_002", "name": "HealthData Corp — Pilot Program",
                "value": 22000, "stage": "Demo", "close_date": "2026-04-15",
                "win_probability": 0.40, "last_activity": "2026-02-18",
                "industry": "Healthcare", "loss_reason": None, "contact_count": 1,
                "source": "mock_hubspot",
            },
            {
                "id": "deal_003", "name": "RetailMax — Analytics Suite",
                "value": 48000, "stage": "Closed Won", "close_date": "2026-02-28",
                "win_probability": 1.0, "last_activity": "2026-02-28",
                "industry": "Retail", "loss_reason": None, "contact_count": 4,
                "source": "mock_hubspot",
            },
            {
                "id": "deal_004", "name": "FinTrust Bank — Compliance Module",
                "value": 130000, "stage": "Proposal", "close_date": "2026-03-20",
                "win_probability": 0.60, "last_activity": "2026-02-10",
                "industry": "Finance", "loss_reason": None, "contact_count": 6,
                "source": "mock_hubspot",
            },
            {
                "id": "deal_005", "name": "LogiFlow — Basic Plan",
                "value": 9500, "stage": "Closed Lost", "close_date": "2026-02-15",
                "win_probability": 0.0, "last_activity": "2026-02-15",
                "industry": "Logistics", "loss_reason": "Price", "contact_count": 1,
                "source": "mock_hubspot",
            },
        ]

    def create_deal(self, deal_data: dict) -> dict:
        return {"id": "deal_new_001", "properties": deal_data, "source": "mock_hubspot"}

    def update_deal(self, deal_id: str, updates: dict) -> dict:
        return {"id": deal_id, "properties": updates, "source": "mock_hubspot"}

    def log_activity(self, deal_id: str, activity: dict) -> dict:
        print(f"[MOCK HUBSPOT] Logged activity on deal {deal_id}: {activity.get('body', '')[:80]}")
        return {"id": "note_mock_001", "deal_id": deal_id}


class MockGmailIntegration(BaseEmailProvider):
    """Simulates email sending without actually sending anything."""

    def send_email(self, to: str, subject: str, body: str,
                   html_body: Optional[str] = None) -> dict:
        print(f"[MOCK GMAIL] Email to: {to} | Subject: {subject[:60]}")
        return {
            "status": "success",
            "message_id": "mock_msg_<random-id>",
            "to": to,
            "subject": subject,
        }


class MockSlackIntegration(BaseMessagingProvider):
    """Simulates Slack posting by printing to console."""

    def post_message(self, channel: str, text: str,
                     blocks: Optional[list] = None) -> dict:
        print(f"[MOCK SLACK] → #{channel}: {text[:100]}")
        return {"status": "success", "channel": channel, "ts": "mock_ts_001"}
