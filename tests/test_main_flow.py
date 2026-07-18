import os
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from loan_processing_crew.main import run

# Define a mock result class that mimics CrewOutput
class MockCrewOutput:
    def __init__(self, raw):
        self.raw = raw

@patch("loan_processing_crew.main.LoanProcessingCrew")
def test_main_run_single(mock_crew_class, tmp_path, monkeypatch):
    # Setup mocks
    mock_crew_instance = MagicMock()
    mock_crew_class.return_value = mock_crew_instance
    
    mock_crew = MagicMock()
    mock_crew_instance.crew.return_value = mock_crew
    mock_crew.kickoff.return_value = MockCrewOutput("MOCK DECISION FOR LOAN-2026-HAPPY")

    # Set up sys.argv to run a single test case
    monkeypatch.setattr(sys, "argv", ["main.py", "LOAN-2026-HAPPY"])
    
    temp_output_dir = tmp_path / "output"
    temp_output_dir.mkdir()
    
    # Patch Path to isolate test file writes inside the tmp directory
    with patch("loan_processing_crew.main.Path") as mock_path:
        def side_effect(*args):
            if args and args[0] == "output":
                return temp_output_dir
            if args and args[0] == "synthetic_data":
                return Path("synthetic_data")
            return Path(*args)
            
        mock_path.side_effect = side_effect
        
        # Execute run
        run()

    # Assert kickoff was called with LOAN-2026-HAPPY
    mock_crew.kickoff.assert_called_once_with(inputs={"application_id": "LOAN-2026-HAPPY"})
    
    # Assert consolidated report was written
    consolidated_file = temp_output_dir / "loan_decision.md"
    assert consolidated_file.exists()
    content = consolidated_file.read_text(encoding="utf-8")
    assert "LOAN-2026-HAPPY" in content
    assert "MOCK DECISION FOR LOAN-2026-HAPPY" in content


@patch("loan_processing_crew.main.LoanProcessingCrew")
def test_main_run_all(mock_crew_class, tmp_path, monkeypatch):
    # Setup mocks
    mock_crew_instance = MagicMock()
    mock_crew_class.return_value = mock_crew_instance
    
    mock_crew = MagicMock()
    mock_crew_instance.crew.return_value = mock_crew
    
    # Mock kickoff to return custom response based on inputs
    def kickoff_side_effect(inputs):
        app_id = inputs.get("application_id")
        return MockCrewOutput(f"MOCK DECISION FOR {app_id}")
        
    mock_crew.kickoff.side_effect = kickoff_side_effect

    # Set up sys.argv to run all
    monkeypatch.setattr(sys, "argv", ["main.py", "all"])
    
    temp_output_dir = tmp_path / "output"
    temp_output_dir.mkdir()
    
    with patch("loan_processing_crew.main.Path") as mock_path:
        def side_effect(*args):
            if args and args[0] == "output":
                return temp_output_dir
            if args and args[0] == "synthetic_data":
                return Path("synthetic_data")
            return Path(*args)
        mock_path.side_effect = side_effect
        
        run()

    # Assert kickoff was called for all applications
    assert mock_crew.kickoff.call_count >= 9
    
    consolidated_file = temp_output_dir / "loan_decision.md"
    assert consolidated_file.exists()
    content = consolidated_file.read_text(encoding="utf-8")
    assert "LOAN-2026-HAPPY" in content
    assert "LOAN-2026-UNDERAGE" in content
    assert "MOCK DECISION FOR LOAN-2026-HAPPY" in content
    assert "MOCK DECISION FOR LOAN-2026-UNDERAGE" in content
