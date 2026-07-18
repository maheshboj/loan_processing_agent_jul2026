from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List

from loan_processing_crew.tools.loan_tools import (
    LoadLoanApplicationTool,
    CreditScoringTool,
    DTICalculatorTool,
    ComplianceCheckTool,
)


@CrewBase
class LoanProcessingCrew:
    """Personal Loan Processing Crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def document_processor(self) -> Agent:
        return Agent(
            config=self.agents_config["document_processor"],
            verbose=True,
            tools=[LoadLoanApplicationTool()],
        )

    @agent
    def underwriter(self) -> Agent:
        return Agent(
            config=self.agents_config["underwriter"],
            verbose=True,
            tools=[CreditScoringTool(), DTICalculatorTool()],
        )

    @agent
    def compliance_officer(self) -> Agent:
        return Agent(
            config=self.agents_config["compliance_officer"],
            verbose=True,
            tools=[ComplianceCheckTool()],
        )

    @agent
    def loan_decision_manager(self) -> Agent:
        return Agent(
            config=self.agents_config["loan_decision_manager"],
            verbose=True,
        )

    @task
    def document_intake_task(self) -> Task:
        return Task(
            config=self.tasks_config["document_intake_task"],
        )

    @task
    def underwriting_task(self) -> Task:
        return Task(
            config=self.tasks_config["underwriting_task"],
        )

    @task
    def compliance_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["compliance_review_task"],
        )

    @task
    def final_decision_task(self) -> Task:
        return Task(
            config=self.tasks_config["final_decision_task"],
            output_file="output/loan_decision_{application_id}.md",
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Loan Processing Crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )