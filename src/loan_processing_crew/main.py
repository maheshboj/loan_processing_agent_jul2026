#!/usr/bin/env python
import os
import sys
import json
from pathlib import Path
from loan_processing_crew.crew import LoanProcessingCrew

os.makedirs("output", exist_ok=True)


def run():
    """Run the loan processing crew."""
    # Path to the applications file
    applications_file = Path("synthetic_data") / "loan_applications.json"
    
    try:
        with open(applications_file, "r") as f:
            applications_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Applications file not found at {applications_file}")
        sys.exit(1)

    # Compile a list of valid application IDs
    if isinstance(applications_data, list):
        all_app_ids = [app["application_id"] for app in applications_data]
    elif isinstance(applications_data, dict):
        if "application_id" in applications_data:
            all_app_ids = [applications_data["application_id"]]
        else:
            all_app_ids = list(applications_data.keys())
    else:
        print("Error: Invalid application data format")
        sys.exit(1)

    # Check for application_id passed via command line
    # Default is "all" to process all applications if no arguments are passed
    app_id = "all"
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if args:
        app_id = args[0]

    # Determine which application IDs to run
    if app_id.lower() == "all":
        target_ids = all_app_ids
    else:
        if app_id not in all_app_ids:
            print(f"Error: Application ID '{app_id}' not found in the dataset.")
            print(f"Available IDs: {', '.join(all_app_ids)}")
            sys.exit(1)
        target_ids = [app_id]

    print(f"Applications to process: {', '.join(target_ids)}")
    
    results = []
    for idx, current_id in enumerate(target_ids, 1):
        print(f"\nProcessing application {idx}/{len(target_ids)}: {current_id}")
        inputs = {
            "application_id": current_id
        }
        try:
            result = LoanProcessingCrew().crew().kickoff(inputs=inputs)
            # Read the dynamic output file written by CrewAI
            output_filepath = Path("output") / f"loan_decision_{current_id}.md"
            if output_filepath.exists():
                with open(output_filepath, "r", encoding="utf-8") as f_in:
                    decision_content = f_in.read()
            else:
                decision_content = result.raw
            results.append((current_id, decision_content))
        except Exception as e:
            error_msg = f"Failed processing {current_id}: {str(e)}"
            print(error_msg)
            results.append((current_id, f"# Decision for {current_id}\n\nERROR: {error_msg}"))

    # Consolidate results into a single output/loan_decision.md
    consolidated_content = []
    consolidated_content.append("# CONSOLIDATED LOAN DECISION REPORT\n")
    consolidated_content.append(f"Total Applications Processed: {len(target_ids)}\n")
    consolidated_content.append("---\n")

    for current_id, decision in results:
        consolidated_content.append(f"\n# START OF REPORT: {current_id}\n")
        consolidated_content.append(decision)
        consolidated_content.append("\n---\n")

    output_file = Path("output") / "loan_decision.md"
    with open(output_file, "w", encoding="utf-8") as f_out:
        f_out.write("\n".join(consolidated_content))

    print("\n\n" + "=" * 60)
    print("       LOAN PROCESSING COMPLETE")
    print("=" * 60 + "\n")
    print(f"Consolidated decisions saved to: {output_file}")


if __name__ == "__main__":
    run()
