"""
integrations/__init__.py
Integration factory — returns real or mock client based on USE_MOCK_INTEGRATIONS env var.
Import from here everywhere in the codebase. Never import mocks or real clients directly.

Usage:
    from integrations import get_lead_provider, get_crm_provider, get_email_provider, get_messaging_provider
"""
from config.settings import settings
from integrations.base import (
    BaseLeadEnrichmentProvider,
    BaseCRMProvider,
    BaseEmailProvider,
    BaseMessagingProvider,
)


def get_lead_provider() -> BaseLeadEnrichmentProvider:
    if settings.is_mock_mode:
        from integrations.mocks import MockApolloIntegration
        return MockApolloIntegration()
    from integrations.apollo import ApolloIntegration
    return ApolloIntegration()


def get_crm_provider() -> BaseCRMProvider:
    if settings.is_mock_mode:
        from integrations.mocks import MockHubSpotIntegration
        return MockHubSpotIntegration()
    from integrations.hubspot import HubSpotIntegration
    return HubSpotIntegration()


def get_email_provider() -> BaseEmailProvider:
    if settings.is_mock_mode:
        from integrations.mocks import MockGmailIntegration
        return MockGmailIntegration()
    # Real implementation when ready:
    # from integrations.gmail import GmailIntegration
    # return GmailIntegration()
    from integrations.mocks import MockGmailIntegration
    return MockGmailIntegration()


def get_messaging_provider() -> BaseMessagingProvider:
    if settings.is_mock_mode:
        from integrations.mocks import MockSlackIntegration
        return MockSlackIntegration()
    from integrations.slack import SlackIntegration
    return SlackIntegration()
