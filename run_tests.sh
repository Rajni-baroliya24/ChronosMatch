# ChronosMatch Automated Integration Test Execution Script
# Author: Gauri Dwivedi
# Role: Testing & Performance Benchmarking Lead

import os
import sys

def main():
    print("==================================================")
    print("      CHRONOSMATCH INTEGRATED TEST RUNNER         ")
    print("==================================================")
    
    # Run Core Engine Tests
    print("\n[STEP 1/3] Running Core Engine & Latency Tests...")
    exit_code_1 = os.system("python test_engine.py")
    
    # Run Mock Data Generator
    print("\n[STEP 2/3] Generating Synthetic Market Data...")
    exit_code_2 = os.system("python generate_mock_data.py")
    
    # Run CI Pipeline Validation
    print("\n[STEP 3/3] Running CI Pipeline Verification...")
    exit_code_3 = os.system("python ci_pipeline.py")
    
    if exit_code_1 == 0 and exit_code_2 == 0 and exit_code_3 == 0:
        print("\n==================================================")
        print(" [SUCCESS] ALL TEST SUITES PASSED VERIFICATION ")
        print("==================================================")
    else:
        print("\n==================================================")
        print(" [ERROR] ONE OR MORE SUITES FAILED ")
        print("==================================================")

if __name__ == "__main__":
    main()
