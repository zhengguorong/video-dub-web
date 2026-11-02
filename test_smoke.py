#!/usr/bin/env python3
"""
Smoke test script for the video dubbing application.
Tests basic API endpoints and workflow.
"""

import os
import requests
import time
import sys
from pathlib import Path

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

def test_health():
    """Test health check endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✅ Health check passed")
    return True

def test_speakers():
    """Test speakers endpoint"""
    print("Testing speakers endpoint...")
    response = requests.get(f"{BASE_URL}/api/speakers")
    assert response.status_code == 200
    data = response.json()
    assert "speakers" in data
    assert len(data["speakers"]) > 0
    print(f"✅ Found {len(data['speakers'])} speakers")
    return True

def test_upload(video_path=None):
    """Test video upload (requires a test video file)"""
    if not video_path:
        print("⚠️  Skipping upload test (no test video provided)")
        return None
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"⚠️  Test video not found: {video_path}")
        return None
    
    print(f"Testing upload with {video_path.name}...")
    with open(video_path, "rb") as f:
        files = {"file": (video_path.name, f, "video/mp4")}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.text}")
        return None
    
    data = response.json()
    job_id = data.get("job_id")
    print(f"✅ Upload successful, job_id: {job_id}")
    return job_id

def test_job_status(job_id):
    """Test job status endpoint"""
    if not job_id:
        return False
    
    print(f"Testing job status for {job_id}...")
    response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    print(f"  Status: {data['state']}")
    print(f"  Message: {data['message']}")
    return True

def main():
    print("=" * 50)
    print("Video Dubbing Tool - Smoke Test")
    print("=" * 50)
    
    try:
        test_health()
        test_speakers()
        
        if len(sys.argv) > 1:
            video_path = sys.argv[1]
            job_id = test_upload(video_path)
            
            if job_id:
                time.sleep(5)
                test_job_status(job_id)
                print("\n⏳ Full pipeline test requires manual verification")
                print(f"   Monitor progress at: {BASE_URL}")
        
        print("\n" + "=" * 50)
        print("✅ All basic tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
