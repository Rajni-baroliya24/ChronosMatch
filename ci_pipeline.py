# ChronosMatch Automated CI/CD Testing Pipeline Execution Script
# Author: Gauri Dwivedi
# Role: Testing & Performance Benchmarking Lead

import os
import subprocess
import sys

def run_step(step_name, command):
    print(f"\n[CI PIPELINE] Running Step: {step_name}...")
    result = subprocess.run(command, shell=True)
    if result.returncode == 0:
        print(f"[PASSED] {step_name} completed successfully.")
        return True
    else:
        print(f"[FAILED] {step_name} failed with exit code {result.returncode}.")
        return False

def execute_pipeline():
    print("==================================================")
    print("      CHRONOSMATCH CI AUTOMATED TEST PIPELINE      ")
    print("==================================================")
    
    steps = [
        ("Mock Market Data Generation", "python generate_mock_data.py"),
        ("Core Test Suite Execution", "python test_engine.py"),
        ("Master End-to-End Test Runner", "python run_all.py")
    ]
    
    all_passed = True
    for step_name, cmd in steps:
        if not run_step(step_name, cmd):
            all_passed = False
            break

    print("\n==================================================")
    if all_passed:
        print(" [STATUS] ALL CI PIPELINE CHECKS PASSED SUCCESSFULLY ")
        print("==================================================")
        sys.exit(0)
    else:
        print(" [STATUS] CI PIPELINE FAILED - ATTENTION REQUIRED ")
        print("==================================================")
        sys.exit(1)

if __name__ == "__main__":
    execute_pipeline()
