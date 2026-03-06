"""
integrations/apollo.py
Real Apollo.io API client for lead enrichment.
Docs: https://apolloio.github.io/apollo-api-docs/
"""
import httpx
from typing import Optional
from integrations.base import BaseLeadEnrichmentProvider
from config.settings import settings


APOLLO_BASE_URL = "https://api.apollo.io/v1"


class ApolloIntegration(BaseLeadEnrichmentProvider):
    def __init__(self):
        self.api_key = settings.apollo_api_key
        self.headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "X-Api-Key": self.api_key or "",
        }

    def enrich_contact(self, email: str) -> dict:
        """
        Match and enrich a person by email using Apollo's People Match API.
        Rate limit: 50/hour on free, higher on paid plans.
        """
        if not self.api_key:
            raise ValueError("APOLLO_API_KEY not set. Use mock mode or provide a real key.")

        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{APOLLO_BASE_URL}/people/match",
                headers=self.headers,
                json={
                    "email": email,
                    "reveal_personal_emails": False,
                    "reveal_phone_number": False,
                }
            )
            response.raise_for_status()
            data = response.json()

        person = data.get("person", {})
        org = person.get("organization", {})

        return {
            "name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
            "title": person.get("title", ""),
            "seniority": person.get("seniority", ""),
            "department": person.get("departments", [""])[0] if person.get("departments") else "",
            "email": person.get("email", email),
            "linkedin_url": person.get("linkedin_url", ""),
            "city": person.get("city", ""),
            "state": person.get("state", ""),
            "country": person.get("country", ""),
            "company": org.get("name", ""),
            "industry": org.get("industry", ""),
            "employee_count": org.get("estimated_num_employees", 0),
            "revenue_range": org.get("annual_revenue_printed", ""),
            "website": org.get("website_url", ""),
            "linkedin_company_url": org.get("linkedin_url", ""),
            "tech_stack": [t.get("name") for t in org.get("current_technologies", [])],
            "funding_stage": org.get("latest_funding_stage", ""),
            "verified": True,
            "source": "apollo",
        }

    def enrich_company(self, domain: str) -> dict:
        """
        Enrich a company by domain using Apollo's Organization Enrich API.
        """
        if not self.api_key:
            raise ValueError("APOLLO_API_KEY not set.")

        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"{APOLLO_BASE_URL}/organizations/enrich",
                headers=self.headers,
                params={"domain": domain}
            )
            response.raise_for_status()
            data = response.json()

        org = data.get("organization", {})
        return {
            "name": org.get("name", ""),
            "domain": org.get("website_url", domain),
            "industry": org.get("industry", ""),
            "employee_count": org.get("estimated_num_employees", 0),
            "revenue_range": org.get("annual_revenue_printed", ""),
            "funding_stage": org.get("latest_funding_stage", ""),
            "tech_stack": [t.get("name") for t in org.get("current_technologies", [])],
            "linkedin_url": org.get("linkedin_url", ""),
            "source": "apollo",
        }
