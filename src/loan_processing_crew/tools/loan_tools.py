import json
import os
from pathlib import Path
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class LoanApplicationInput(BaseModel):
    """Input schema for loading a loan application."""
    application_id: str = Field(
        ..., description="The loan application ID to retrieve."
    )


class LoadLoanApplicationTool(BaseTool):
    name: str = "Load Loan Application"
    description: str = (
        "Loads a loan application from the synthetic data store. "
        "Returns the full application JSON including applicant info, "
        "financial profile, employment details, and loan request."
    )
    args_schema: Type[BaseModel] = LoanApplicationInput

    def _run(self, application_id: str) -> str:
        # Resolve from the current working directory (project root)
        file_path = Path(os.getcwd()) / "synthetic_data" / "loan_applications.json"

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            # Handle list of applications
            if isinstance(data, list):
                for app in data:
                    if app.get("application_id") == application_id:
                        return json.dumps(app, indent=2)
                return f"Application {application_id} not found in the dataset list."
            
            # Handle dictionary mapping
            elif isinstance(data, dict):
                # Backwards compatibility: check if the root dict is the application itself
                if data.get("application_id") == application_id:
                    return json.dumps(data, indent=2)
                # Dictionary mapping: application_id -> application dict
                if application_id in data:
                    return json.dumps(data[application_id], indent=2)
                return f"Application {application_id} not found in the dataset map."
                
            return f"Invalid data format in {file_path}. Expected list or dict."
        except FileNotFoundError:
            return f"Data file not found at {file_path}"


class CreditScoreInput(BaseModel):
    """Input for credit score lookup."""
    credit_score: int = Field(..., description="The applicant's credit score.")


class CreditScoringTool(BaseTool):
    name: str = "Credit Score Evaluator"
    description: str = (
        "Evaluates a credit score and returns a risk tier classification "
        "with corresponding interest rate range."
    )
    args_schema: Type[BaseModel] = CreditScoreInput

    def _run(self, credit_score: int) -> str:
        if credit_score >= 750:
            tier = "Excellent"
            rate_range = "6.5% - 8.0%"
            risk = "Low"
        elif credit_score >= 700:
            tier = "Good"
            rate_range = "8.0% - 11.0%"
            risk = "Low-Medium"
        elif credit_score >= 650:
            tier = "Fair"
            rate_range = "11.0% - 15.0%"
            risk = "Medium"
        elif credit_score >= 600:
            tier = "Below Average"
            rate_range = "15.0% - 20.0%"
            risk = "Medium-High"
        else:
            tier = "Poor"
            rate_range = "20.0%+ or Decline"
            risk = "High"

        return json.dumps({
            "credit_score": credit_score,
            "tier": tier,
            "suggested_rate_range": rate_range,
            "risk_level": risk
        }, indent=2)


class DTICalculatorInput(BaseModel):
    """Input for DTI calculation."""
    monthly_gross_income: float = Field(
        ..., description="Monthly gross income."
    )
    total_monthly_debt: float = Field(
        ..., description="Total monthly debt payments including the new loan."
    )


class DTICalculatorTool(BaseTool):
    name: str = "DTI Ratio Calculator"
    description: str = (
        "Calculates the Debt-to-Income (DTI) ratio and provides "
        "an assessment of whether it meets lending guidelines."
    )
    args_schema: Type[BaseModel] = DTICalculatorInput

    def _run(self, monthly_gross_income: float, total_monthly_debt: float) -> str:
        dti = (total_monthly_debt / monthly_gross_income) * 100
        dti_rounded = round(dti, 2)

        if dti <= 36:
            assessment = "PASS - DTI is within acceptable limits."
            recommendation = "Approve from DTI perspective."
        elif dti <= 43:
            assessment = "CAUTION - DTI is elevated but may be acceptable with compensating factors."
            recommendation = "Conditional approval; review compensating factors."
        else:
            assessment = "FAIL - DTI exceeds maximum threshold."
            recommendation = "Decline or require co-signer/reduced loan amount."

        return json.dumps({
            "dti_ratio_percent": dti_rounded,
            "assessment": assessment,
            "recommendation": recommendation,
            "monthly_gross_income": monthly_gross_income,
            "total_monthly_debt": total_monthly_debt
        }, indent=2)


class ComplianceCheckInput(BaseModel):
    """Input for compliance check."""
    applicant_age: int = Field(..., description="Applicant's age in years.")
    loan_amount: float = Field(..., description="Requested loan amount.")
    annual_income: float = Field(..., description="Applicant's annual income.")


class ComplianceCheckTool(BaseTool):
    name: str = "Regulatory Compliance Checker"
    description: str = (
        "Performs regulatory compliance checks including age verification, "
        "loan-to-income ratio, and TILA/ECOA compliance flags."
    )
    args_schema: Type[BaseModel] = ComplianceCheckInput

    def _run(self, applicant_age: int, loan_amount: float, annual_income: float) -> str:
        checks = []

        # Age check
        if applicant_age >= 18:
            checks.append({"check": "Age Verification", "status": "PASS",
                           "detail": f"Applicant is {applicant_age} years old."})
        else:
            checks.append({"check": "Age Verification", "status": "FAIL",
                           "detail": "Applicant must be at least 18."})

        # Loan-to-income ratio
        lti = loan_amount / annual_income
        lti_status = "PASS" if lti <= 0.5 else "WARNING"
        checks.append({
            "check": "Loan-to-Income Ratio",
            "status": lti_status,
            "detail": f"LTI ratio is {round(lti, 2)} (threshold: 0.50)"
        })

        # TILA disclosure
        checks.append({
            "check": "TILA Disclosure Required",
            "status": "REQUIRED",
            "detail": "Truth in Lending Act disclosures must be provided."
        })

        # ECOA
        checks.append({
            "check": "ECOA Compliance",
            "status": "PASS",
            "detail": "No prohibited factors used in decision-making."
        })

        overall = "PASS" if all(
            c["status"] in ["PASS", "REQUIRED"] for c in checks
        ) else "REVIEW NEEDED"

        return json.dumps({
            "overall_compliance": overall,
            "checks": checks
        }, indent=2)