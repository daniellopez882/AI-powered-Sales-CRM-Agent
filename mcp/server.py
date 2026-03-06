from mcp.server.fastmcp import FastMCP
from integrations.mocks import ApolloIntegration, HubSpotIntegration, GmailIntegration, SlackIntegration

# Initialize FastMCP server
mcp = FastMCP("SalesIQ-CRM-Server")

apollo = ApolloIntegration()
hubspot = HubSpotIntegration()
gmail = GmailIntegration()
slack = SlackIntegration()

@mcp.tool()
def enrich_lead(email: str) -> dict:
    """
    Enriches a raw lead with full B2B intelligence.
    Use when: User provides a name, email, company, or LinkedIn URL
    and wants complete prospect profile.
    Returns: ICP score, company intel, contact data, priority level.
    """
    return apollo.enrich_contact(email)

@mcp.tool()
def draft_outreach(lead_email: str, product_desc: str) -> dict:
    """
    Generates personalized cold outreach email for a prospect.
    Requires: Enriched lead profile data.
    """
    # In a real tool, this would call the EmailPersonalizerAgent
    return {
        "subject": f"Question about sales ops at TechCorp?",
        "body": f"Hi, noticed you're using Salesforce and Marketo. We help with {product_desc}..."
    }

@mcp.tool()
def analyze_pipeline() -> dict:
    """
    Analyzes current deals for risks, opportunities, patterns.
    Returns: Deal scores, risk flags, recommended actions.
    """
    deals = hubspot.get_deal_data()
    return {"deals_analyzed": len(deals), "deals": deals}

@mcp.tool()
def send_report(report_content: str, channel: str = "sales-alerts") -> dict:
    """
    Sends the generated pipeline report to Slack.
    """
    return slack.post_message(channel, report_content)

if __name__ == "__main__":
    mcp.run()
