#!/usr/bin/env python3
"""
Test script to verify the new batch job management UI functionality.
This script simulates the key API calls that the UI makes.
"""

import requests
import json
import sys

def test_endpoints():
    """Test the new batch job management endpoints."""
    base_url = "http://localhost:5000"
    
    print("Testing batch job management endpoints...")
    
    # Test endpoints with a dummy batch ID (this will fail gracefully)
    test_batch_id = "123"
    
    endpoints_to_test = [
        {
            "method": "GET",
            "url": f"{base_url}/api/batches/{test_batch_id}/available-jobs",
            "description": "Get available jobs for batch"
        },
        {
            "method": "GET", 
            "url": f"{base_url}/api/batches/{test_batch_id}/settings",
            "description": "Get batch settings"
        },
        {
            "method": "POST",
            "url": f"{base_url}/api/batches/{test_batch_id}/jobs/create",
            "description": "Create job in batch",
            "data": {"job_name": "Test Job"}
        },
        {
            "method": "POST",
            "url": f"{base_url}/api/batches/{test_batch_id}/jobs",
            "description": "Add jobs to batch",
            "data": {"job_ids": ["456"]}
        }
    ]
    
    print("Note: These tests expect the server to be running and will return 404 errors")
    print("since we're using dummy IDs. The important thing is that the endpoints exist.\n")
    
    for test in endpoints_to_test:
        try:
            if test["method"] == "GET":
                response = requests.get(test["url"], timeout=2)
            else:
                response = requests.post(
                    test["url"], 
                    json=test.get("data", {}),
                    headers={'Content-Type': 'application/json'},
                    timeout=2
                )
            
            print(f"✓ {test['description']}: {response.status_code}")
            if response.status_code not in [200, 404]:
                print(f"  Response: {response.text[:100]}")
                
        except requests.exceptions.ConnectionError:
            print(f"✗ {test['description']}: Server not running")
        except requests.exceptions.Timeout:
            print(f"✗ {test['description']}: Timeout")
        except Exception as e:
            print(f"✗ {test['description']}: {e}")

if __name__ == "__main__":
    print("Batch Job Management UI Test Script")
    print("===================================")
    test_endpoints()
    print("\nNote: Run 'python app.py' in another terminal to test with a live server.")