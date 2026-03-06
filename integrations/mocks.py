# integrations/apollo.py
class ApolloIntegration:
    def enrich_contact(self, email: str):
        # Mocking Apollo API response
        return {
            "name": "John Doe",
            "title": "Director of Sales Operations",
            "company": "TechCorp Solutions",
            "industry": "Software",
            "employee_count": "500-1000",
            "tech_stack": ["Salesforce", "Marketo", "Gong"],
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "recent_news": "TechCorp raises $50M Series C",
            "verified": True
        }

# integrations/hubspot.py
class HubSpotIntegration:
    def get_deal_data(self):
        # Mocking HubSpot deals
        return [
            {"id": "1", "name": "Deal A", "value": 50000, "stage": "Closed Won", "industry": "Finance"},
            {"id": "2", "name": "Deal B", "value": 15000, "stage": "Negotiation", "industry": "Retail"},
            {"id": "3", "name": "Deal C", "value": 25000, "stage": "Closed Lost", "reason": "Price", "industry": "Healthcare"}
        ]

# integrations/gmail.py
class GmailIntegration:
    def send_email(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}...")
        return {"status": "success", "message_id": "mock_msg_123"}

# integrations/slack.py
class SlackIntegration:
    def post_message(self, channel: str, text: str):
        print(f"Posting to Slack channel {channel}...")
        return {"status": "success"}
