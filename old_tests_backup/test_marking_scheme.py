#!/usr/bin/env python3
"""
Test script for marking scheme functionality.
"""

import os
import tempfile
import requests
from pathlib import Path

def create_test_files():
    """Create test files for marking scheme and document."""
    
    # Create a test marking scheme
    marking_scheme_content = """
GRADING RUBRIC FOR ESSAYS

CRITERIA:
1. Thesis Statement (20 points)
   - Clear and specific thesis
   - Well-argued position
   - Appropriate scope

2. Content and Analysis (30 points)
   - Relevant evidence and examples
   - Logical argument development
   - Critical thinking demonstrated

3. Organization (20 points)
   - Clear structure and flow
   - Effective transitions
   - Logical paragraph organization

4. Writing Quality (20 points)
   - Clear and concise writing
   - Appropriate tone and style
   - Grammar and mechanics

5. Citations and References (10 points)
   - Proper citation format
   - Adequate source integration
   - Works cited page

GRADING SCALE:
A (90-100): Excellent work that exceeds expectations
B (80-89): Good work that meets most expectations
C (70-79): Satisfactory work with some areas for improvement
D (60-69): Below average work with significant issues
F (0-59): Unsatisfactory work that fails to meet basic requirements
"""
    
    # Create a test document
    document_content = """
The Impact of Technology on Education

Technology has fundamentally transformed the way we approach education in the 21st century. This essay explores the various ways in which digital tools and platforms have enhanced learning experiences while also examining potential challenges and concerns.

The integration of technology in education has provided unprecedented access to information and resources. Students can now access vast libraries of knowledge through the internet, participate in virtual classrooms, and collaborate with peers across geographical boundaries. Online learning platforms have made education more accessible to individuals who may not have been able to attend traditional institutions due to geographical, financial, or time constraints.

However, the rapid adoption of technology in education also presents several challenges. The digital divide remains a significant concern, as not all students have equal access to technology and reliable internet connections. Additionally, there are concerns about the quality of online education and the potential for technology to replace rather than enhance human interaction in learning environments.

Despite these challenges, the benefits of technology in education are substantial. Digital tools can provide personalized learning experiences, immediate feedback, and engaging multimedia content that can enhance understanding and retention. The key is to implement technology thoughtfully and ensure that it serves to support rather than replace effective teaching practices.

In conclusion, while technology presents both opportunities and challenges in education, its thoughtful integration can significantly enhance learning outcomes and make education more accessible and engaging for students worldwide.
"""
    
    # Create temporary files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(marking_scheme_content)
        marking_scheme_path = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(document_content)
        document_path = f.name
    
    return marking_scheme_path, document_path

def test_marking_scheme_upload():
    """Test marking scheme upload functionality."""
    print("Testing marking scheme upload...")
    
    marking_scheme_path, document_path = create_test_files()
    
    try:
        # Test marking scheme upload
        with open(marking_scheme_path, 'rb') as f:
            files = {'marking_scheme': f}
            data = {
                'name': 'Test Grading Rubric',
                'description': 'A comprehensive rubric for essay grading'
            }
            
            response = requests.post('http://localhost:5000/upload_marking_scheme', 
                                   files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✓ Marking scheme upload successful")
                    marking_scheme_id = result['marking_scheme_id']
                    print(f"  Marking scheme ID: {marking_scheme_id}")
                    return marking_scheme_id
                else:
                    print(f"✗ Marking scheme upload failed: {result.get('error')}")
                    return None
            else:
                print(f"✗ Marking scheme upload failed with status {response.status_code}")
                return None
                
    except Exception as e:
        print(f"✗ Error testing marking scheme upload: {e}")
        return None
    finally:
        # Clean up temporary files
        os.unlink(marking_scheme_path)
        os.unlink(document_path)

def test_document_upload_with_marking_scheme():
    """Test document upload with marking scheme."""
    print("\nTesting document upload with marking scheme...")
    
    marking_scheme_path, document_path = create_test_files()
    
    try:
        # Upload document with marking scheme
        with open(document_path, 'rb') as doc_file, open(marking_scheme_path, 'rb') as scheme_file:
            files = {
                'file': doc_file,
                'marking_scheme': scheme_file
            }
            data = {
                'prompt': 'Please grade this essay using the provided marking scheme.',
                'provider': 'openrouter',
                'customModel': 'anthropic/claude-3-5-sonnet-20241022'
            }
            
            response = requests.post('http://localhost:5000/upload', files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✓ Document upload with marking scheme successful")
                    print(f"  Provider: {result.get('provider')}")
                    print(f"  Model: {result.get('model')}")
                    print(f"  Grade length: {len(result.get('grade', ''))} characters")
                    return True
                else:
                    print(f"✗ Document upload failed: {result.get('error')}")
                    return False
            else:
                print(f"✗ Document upload failed with status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"✗ Error testing document upload: {e}")
        return False
    finally:
        # Clean up temporary files
        os.unlink(marking_scheme_path)
        os.unlink(document_path)

def test_bulk_upload_with_marking_scheme():
    """Test bulk upload with marking scheme."""
    print("\nTesting bulk upload with marking scheme...")
    
    marking_scheme_path, document_path = create_test_files()
    
    try:
        # First, upload marking scheme
        with open(marking_scheme_path, 'rb') as f:
            files = {'marking_scheme': f}
            data = {
                'name': 'Bulk Test Rubric',
                'description': 'Rubric for bulk upload testing'
            }
            
            response = requests.post('http://localhost:5000/upload_marking_scheme', 
                                   files=files, data=data)
            
            if not response.status_code == 200:
                print("✗ Failed to upload marking scheme for bulk test")
                return False
            
            result = response.json()
            if not result.get('success'):
                print("✗ Failed to upload marking scheme for bulk test")
                return False
            
            marking_scheme_id = result['marking_scheme_id']
            print(f"✓ Marking scheme uploaded for bulk test (ID: {marking_scheme_id})")
            
            # Create a job with marking scheme
            job_data = {
                'job_name': 'Test Bulk Job with Marking Scheme',
                'description': 'Testing bulk upload with marking scheme',
                'provider': 'openrouter',
                'model': 'anthropic/claude-3-5-sonnet-20241022',
                'prompt': 'Please grade these documents using the provided marking scheme.',
                'priority': 5,
                'marking_scheme_id': marking_scheme_id
            }
            
            response = requests.post('http://localhost:5000/create_job', 
                                   json=job_data)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    job_id = result['job_id']
                    print(f"✓ Job created successfully (ID: {job_id})")
                    
                    # Upload document to the job
                    with open(document_path, 'rb') as f:
                        files = {'files[]': f}
                        data = {'job_id': job_id}
                        
                        response = requests.post('http://localhost:5000/upload_bulk', 
                                               files=files, data=data)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get('success'):
                                print("✓ Document uploaded to bulk job successfully")
                                return True
                            else:
                                print(f"✗ Failed to upload document to bulk job: {result.get('error')}")
                                return False
                        else:
                            print(f"✗ Failed to upload document to bulk job (status: {response.status_code})")
                            return False
                else:
                    print(f"✗ Failed to create job: {result.get('error')}")
                    return False
            else:
                print(f"✗ Failed to create job (status: {response.status_code})")
                return False
                
    except Exception as e:
        print(f"✗ Error testing bulk upload: {e}")
        return False
    finally:
        # Clean up temporary files
        os.unlink(marking_scheme_path)
        os.unlink(document_path)

def main():
    """Run all tests."""
    print("Testing Marking Scheme Functionality")
    print("=" * 40)
    
    # Test 1: Marking scheme upload
    marking_scheme_id = test_marking_scheme_upload()
    
    # Test 2: Document upload with marking scheme
    test_document_upload_with_marking_scheme()
    
    # Test 3: Bulk upload with marking scheme
    test_bulk_upload_with_marking_scheme()
    
    print("\n" + "=" * 40)
    print("Testing completed!")

if __name__ == '__main__':
    main()
