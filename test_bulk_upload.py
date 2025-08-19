#!/usr/bin/env python3
"""
Test script for bulk upload functionality
"""

import requests
import json
import os

def test_bulk_upload():
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Bulk Upload Functionality...")
    
    # Test 1: Create a job
    print("\n1. Creating a test job...")
    job_data = {
        "job_name": "Test Job",
        "description": "Test job for bulk upload",
        "provider": "lm_studio",
        "prompt": "Please grade this document.",
        "priority": 5
    }
    
    response = requests.post(
        f"{base_url}/create_job",
        json=job_data,
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        job_result = response.json()
        job_id = job_result['job_id']
        print(f"✅ Job created successfully! Job ID: {job_id}")
    else:
        print(f"❌ Failed to create job: {response.text}")
        return False
    
    # Test 2: Create a test file
    print("\n2. Creating test file...")
    test_content = "This is a test document for grading."
    with open("test_document.txt", "w") as f:
        f.write(test_content)
    
    # Test 3: Upload file (simulate form data)
    print("\n3. Testing file upload...")
    files = {'files[]': ('test_document.txt', open('test_document.txt', 'rb'), 'text/plain')}
    data = {'job_id': job_id}
    
    response = requests.post(
        f"{base_url}/upload_bulk",
        files=files,
        data=data
    )
    
    if response.status_code == 200:
        upload_result = response.json()
        print(f"✅ File upload successful! {upload_result['message']}")
    else:
        print(f"❌ File upload failed: {response.text}")
        return False
    
    # Test 4: Check job status
    print("\n4. Checking job status...")
    response = requests.get(f"{base_url}/api/jobs/{job_id}")
    
    if response.status_code == 200:
        job_status = response.json()
        print(f"✅ Job status: {job_status['status']}")
        print(f"   Progress: {job_status['progress']}%")
        print(f"   Total submissions: {job_status['total_submissions']}")
    else:
        print(f"❌ Failed to get job status: {response.text}")
    
    # Cleanup
    print("\n5. Cleaning up...")
    if os.path.exists("test_document.txt"):
        os.remove("test_document.txt")
    
    print("\n🎉 All tests completed!")
    return True

if __name__ == "__main__":
    test_bulk_upload()
