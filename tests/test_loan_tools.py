import json
import pytest
from loan_processing_crew.tools.loan_tools import (
    LoadLoanApplicationTool,
    CreditScoringTool,
    DTICalculatorTool,
    ComplianceCheckTool,
)

def test_load_loan_application_tool():
    tool = LoadLoanApplicationTool()
    
    # Test loading a valid application
    res_happy = tool._run("LOAN-2026-HAPPY")
    assert "LOAN-2026-HAPPY" in res_happy
    assert "Alice K. Vance" in res_happy
    
    # Test loading another valid application
    res_underage = tool._run("LOAN-2026-UNDERAGE")
    assert "LOAN-2026-UNDERAGE" in res_underage
    assert "Tyler Durden" in res_underage

    # Test loading invalid application
    res_invalid = tool._run("INVALID-ID")
    assert "INVALID-ID not found" in res_invalid or "INVALID-ID" in res_invalid


def test_credit_scoring_tool():
    tool = CreditScoringTool()
    
    # Excellent
    res = json.loads(tool._run(780))
    assert res["tier"] == "Excellent"
    assert res["risk_level"] == "Low"
    
    # Good
    res = json.loads(tool._run(710))
    assert res["tier"] == "Good"
    assert res["risk_level"] == "Low-Medium"
    
    # Fair
    res = json.loads(tool._run(675))
    assert res["tier"] == "Fair"
    assert res["risk_level"] == "Medium"
    
    # Below Average
    res = json.loads(tool._run(620))
    assert res["tier"] == "Below Average"
    assert res["risk_level"] == "Medium-High"
    
    # Poor
    res = json.loads(tool._run(580))
    assert res["tier"] == "Poor"
    assert res["risk_level"] == "High"


def test_dti_calculator_tool():
    tool = DTICalculatorTool()
    
    # PASS DTI <= 36%
    res = json.loads(tool._run(10000, 3000))
    assert res["dti_ratio_percent"] == 30.0
    assert "PASS" in res["assessment"]
    
    # CAUTION 36% < DTI <= 43%
    res = json.loads(tool._run(10000, 4000))
    assert res["dti_ratio_percent"] == 40.0
    assert "CAUTION" in res["assessment"]
    
    # FAIL DTI > 43%
    res = json.loads(tool._run(10000, 5000))
    assert res["dti_ratio_percent"] == 50.0
    assert "FAIL" in res["assessment"]


def test_compliance_check_tool():
    tool = ComplianceCheckTool()
    
    # PASS scenario (age >= 18, lti <= 0.5)
    res = json.loads(tool._run(applicant_age=25, loan_amount=30000, annual_income=80000))
    assert res["overall_compliance"] == "PASS"
    age_check = next(c for c in res["checks"] if c["check"] == "Age Verification")
    assert age_check["status"] == "PASS"
    lti_check = next(c for c in res["checks"] if c["check"] == "Loan-to-Income Ratio")
    assert lti_check["status"] == "PASS"
    
    # Underage FAIL scenario
    res_underage = json.loads(tool._run(applicant_age=17, loan_amount=10000, annual_income=30000))
    assert res_underage["overall_compliance"] == "REVIEW NEEDED"
    age_check = next(c for c in res_underage["checks"] if c["check"] == "Age Verification")
    assert age_check["status"] == "FAIL"

    # Loan-to-Income WARNING scenario
    res_lti = json.loads(tool._run(applicant_age=30, loan_amount=50000, annual_income=80000))
    # 50000/80000 = 0.625 > 0.5, so warning is expected
    lti_check = next(c for c in res_lti["checks"] if c["check"] == "Loan-to-Income Ratio")
    assert lti_check["status"] == "WARNING"
