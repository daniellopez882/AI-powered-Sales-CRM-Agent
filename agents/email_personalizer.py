from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI

class EmailPersonalizerAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="EmailPersonalizer",
            goal="Draft hyper-personalized cold outreach emails that feel human and relevant.",
            backstory="""You are an elite B2B copywriter who has written 
cold emails that generated millions in pipeline. You write emails that 
feel human, relevant, and irresistible to open and reply to.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, context: dict):
        return Task(
            description=f"""
Given the following context:
Enriched Lead Profile: {context.get('enriched_lead')}
Sender's Product/Service: {context.get('product_description')}
Campaign Goal: {context.get('goal')}
Tone Preference: {context.get('tone', 'conversational')}

## EMAIL FRAMEWORK — PROVEN STRUCTURE
Line 1 (Hook): A specific, researched observation about THEM.
Line 2-3 (Bridge): Connect their situation to a relevant problem.
Line 4-5 (Value): One specific, quantified outcome you deliver.
Line 6 (CTA): ONE clear, low-friction ask.

## QUALITY RULES
- Email body: 75-125 words MAX
- Reading level: Grade 6 (simple, clear)
- One idea per email — never pitch multiple things
- No attachments in first email
- No "I hope this email finds you well"
- No "We help companies like yours"
- Must pass spam filter check — no ALL CAPS, excessive punctuation
""",
            agent=self.agent,
            expected_output="A JSON object with subject line variations, recommended subject, email body, personalization elements, and estimated reply rate."
        )

    def run(self, context: dict):
        task = self.get_task(context)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
