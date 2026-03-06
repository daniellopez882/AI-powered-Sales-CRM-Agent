"""
integrations/base.py
Abstract base classes for all external integrations.
Enforces a consistent contract between mock and real implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional


class BaseLeadEnrichmentProvider(ABC):
    @abstractmethod
    def enrich_contact(self, email: str) -> dict:
        """Enrich a contact by email. Returns standardized profile dict."""
        ...

    @abstractmethod
    def enrich_company(self, domain: str) -> dict:
        """Enrich a company by domain. Returns standardized company dict."""
        ...


class BaseCRMProvider(ABC):
    @abstractmethod
    def get_deal_data(self) -> list:
        """Fetch all active + closed deals. Returns list of deal dicts."""
        ...

    @abstractmethod
    def create_deal(self, deal_data: dict) -> dict:
        """Create a new deal. Returns the created deal with CRM ID."""
        ...

    @abstractmethod
    def update_deal(self, deal_id: str, updates: dict) -> dict:
        """Update an existing deal. Returns the updated deal."""
        ...

    @abstractmethod
    def log_activity(self, deal_id: str, activity: dict) -> dict:
        """Log a sales activity (email sent, call made) against a deal."""
        ...


class BaseEmailProvider(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str,
                   html_body: Optional[str] = None) -> dict:
        """Send a single email. Returns send result with message_id."""
        ...


class BaseMessagingProvider(ABC):
    @abstractmethod
    def post_message(self, channel: str, text: str,
                     blocks: Optional[list] = None) -> dict:
        """Post a message to a channel. Returns Slack API response."""
        ...
