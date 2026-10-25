# ChronosMatch Environment Verification & Test Setup
# Author: Gauri Dwivedi
# Role: Testing & Performance Benchmarking Lead

import sys
import os
import json

def verify_environment():
    print("==================================================")
    print("   CHRONOSMATCH TEST ENVIRONMENT CHECK           ")
    print("==================================================")
    
    python_version = sys.version.split()[0]
    print(f"[INFO] Python Runtime Version: {python_version}")
    
    # Verify required configuration file exists
    config_file = "test_config.json"
    if os.path.exists(config_file):
        print(f"[PASS] Configuration file '{config_file}' found.")
        with open(config_file, "r") as f:
            config_data = json.load(f)
            print(f"[INFO] Target Latency Limit: {config_data.get('latency_threshold_ms')} ms")
    else:
        print(f"[WARN] Configuration file '{config_file}' missing. Using defaults.")
        
    print("[SUCCESS] Environment verification complete. System ready for benchmarking.")

if __name__ == "__main__":
    verify_environment()
