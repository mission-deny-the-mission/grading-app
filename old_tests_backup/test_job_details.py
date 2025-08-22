#!/usr/bin/env python3
"""
Test script for job details page functionality
"""

import requests
import json

def test_job_details():
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Job Details Page Functionality...")
    
    # Test 1: Get all jobs
    print("\n1. Getting all jobs...")
    response = requests.get(f"{base_url}/jobs")
    
    if response.status_code == 200:
        print("✅ Jobs page accessible")
    else:
        print(f"❌ Jobs page failed: {response.status_code}")
        return False
    
    # Test 2: Get jobs API
    print("\n2. Testing jobs API...")
    response = requests.get(f"{base_url}/api/jobs")
    
    if response.status_code == 200:
        jobs = response.json()
        if jobs:
            job_id = jobs[0]['id']
            print(f"✅ Found job: {jobs[0]['job_name']} (ID: {job_id})")
        else:
            print("⚠️  No jobs found")
            return False
    else:
        print(f"❌ Jobs API failed: {response.status_code}")
        return False
    
    # Test 3: Get job details page
    print(f"\n3. Testing job details page for job {job_id}...")
    response = requests.get(f"{base_url}/jobs/{job_id}")
    
    if response.status_code == 200:
        print("✅ Job details page accessible")
    else:
        print(f"❌ Job details page failed: {response.status_code}")
        return False
    
    # Test 4: Get job API details
    print(f"\n4. Testing job API details...")
    response = requests.get(f"{base_url}/api/jobs/{job_id}")
    
    if response.status_code == 200:
        job_data = response.json()
        print(f"✅ Job API working - Status: {job_data['status']}, Progress: {job_data['progress']}%")
    else:
        print(f"❌ Job API failed: {response.status_code}")
        return False
    
    # Test 5: Get job submissions
    print(f"\n5. Testing job submissions API...")
    response = requests.get(f"{base_url}/api/jobs/{job_id}/submissions")
    
    if response.status_code == 200:
        submissions = response.json()
        print(f"✅ Submissions API working - Found {len(submissions)} submissions")
        
        if submissions:
            submission_id = submissions[0]['id']
            print(f"   First submission: {submissions[0]['original_filename']} (ID: {submission_id})")
            
            # Test 6: Get submission details
            print(f"\n6. Testing submission details API...")
            response = requests.get(f"{base_url}/api/submissions/{submission_id}")
            
            if response.status_code == 200:
                submission_data = response.json()
                print(f"✅ Submission API working - Status: {submission_data['status']}")
            else:
                print(f"❌ Submission API failed: {response.status_code}")
                return False
    else:
        print(f"❌ Submissions API failed: {response.status_code}")
        return False
    
    print("\n🎉 All job details tests completed successfully!")
    return True

if __name__ == "__main__":
    test_job_details()
