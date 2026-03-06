from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from agents.prompts import EMAIL_PERSONALIZER_PROMPT, build_agent_prompt

class EmailPersonalizerAgent:
    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.llm = ChatOpenAI(model=model_name)
        self.agent = Agent(
            role="EmailPersonalizer",
            goal="Draft hyper-personalized cold outreach emails that feel human and relevant.",
            backstory=build_agent_prompt(EMAIL_PERSONALIZER_PROMPT),
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )

    def get_task(self, context: dict):
        return Task(
            description=f"""
Draft an email using the PROVEN EMAIL FRAMEWORK based on this context:
Enriched Lead Profile: {context.get('enriched_lead')}
Sender's Product/Service: {context.get('product_description')}
Campaign Goal: {context.get('goal')}
Tone Preference: {context.get('tone', 'conversational')}
""",
            agent=self.agent,
            expected_output="A JSON object matching the defined OUTPUT FORMAT, including 3 subject line variations and a personalized email body."
        )

    def run(self, context: dict):
        task = self.get_task(context)
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            process=Process.sequential
        )
        return crew.kickoff()
