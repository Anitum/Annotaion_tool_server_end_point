import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:5000"
API_KEY = "sk_live_abc123def456ghi789jkl012mno345pqr678"  # Use from config.py

class VideoAnnotationAPITester:
    def __init__(self, base_url=BASE_URL, api_key=API_KEY):
        self.base_url = base_url
        self.headers = {'X-API-Key': api_key}
    
    def test_health(self):
        """Test health endpoint (no auth required)"""
        print("🔍 Testing health endpoint...")
        response = requests.get(f"{self.base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    def test_auth_required(self):
        """Test endpoint without API key"""
        print("🔍 Testing auth requirement...")
        response = requests.get(f"{self.base_url}/query/local")
        print(f"Status (no auth): {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    def test_generate_key(self):
        """Test API key generation"""
        print("🔍 Testing API key generation...")
        response = requests.post(f"{self.base_url}/auth/generate-key")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    def test_query_local(self):
        """Test querying local files"""
        print("🔍 Testing local file query...")
        response = requests.get(f"{self.base_url}/query/local", headers=self.headers)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Found {data.get('count', 0)} local files")
        if data.get('files'):
            print("First file:", json.dumps(data['files'][0], indent=2))
        print()
    
    def test_query_s3(self):
        """Test querying S3 files"""
        print("🔍 Testing S3 file query...")
        response = requests.get(f"{self.base_url}/query/s3", headers=self.headers)
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Found {data.get('count', 0)} S3 files")
        if data.get('files'):
            print("First file:", json.dumps(data['files'][0], indent=2))
        print()
    
    def test_schedule_get(self):
        """Test getting current schedule"""
        print("🔍 Testing get schedule...")
        response = requests.get(f"{self.base_url}/schedule", headers=self.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    def test_schedule_update(self):
        """Test updating schedule"""
        print("🔍 Testing schedule update...")
        new_schedule = {
            "upload_times": ["09:00", "15:00", "21:00"]
        }
        response = requests.post(
            f"{self.base_url}/schedule", 
            headers=self.headers,
            json=new_schedule
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    def test_manual_upload(self):
        """Test manual upload trigger"""
        print("🔍 Testing manual upload...")
        response = requests.post(f"{self.base_url}/upload/manual", headers=self.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    
    def test_download_range(self):
        """Test downloading files in time range"""
        print("🔍 Testing range download...")
        
        # Download files from yesterday to now
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        
        range_data = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        
        response = requests.post(
            f"{self.base_url}/download/range",
            headers=self.headers,
            json=range_data
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Downloaded file size: {len(response.content)} bytes")
            # Save to file
            with open("range_download_test.tar.gz", "wb") as f:
                f.write(response.content)
            print("Saved as: range_download_test.tar.gz")
        else:
            print(f"Response: {response.json()}")
        print()

def run_all_tests():
    """Run all API tests"""
    tester = VideoAnnotationAPITester()
    
    print("🚀 Starting Video Annotation API Tests\n")
    
    # Test endpoints
    tester.test_health()
    tester.test_auth_required()
    tester.test_generate_key()
    tester.test_query_local()
    tester.test_query_s3()
    tester.test_schedule_get()
    tester.test_schedule_update()
    tester.test_manual_upload()
    tester.test_download_range()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    run_all_tests()
