#!/bin/bash

BASE_URL="http://localhost:5000"
API_KEY="sk_live_abc123def456ghi789jkl012mno345pqr678"

echo "🚀 Video Annotation API cURL Examples"
echo "======================================="

echo ""
echo "1. Health Check (Public endpoint)"
echo "curl -X GET $BASE_URL/health"
curl -X GET $BASE_URL/health | jq
echo ""

echo "2. Test without API key (should fail)"
echo "curl -X GET $BASE_URL/query/local"
curl -X GET $BASE_URL/query/local | jq
echo ""

echo "3. Generate new API key"
echo "curl -X POST $BASE_URL/auth/generate-key"
curl -X POST $BASE_URL/auth/generate-key | jq
echo ""

echo "4. Query local files (with X-API-Key header)"
echo "curl -H 'X-API-Key: $API_KEY' $BASE_URL/query/local"
curl -H "X-API-Key: $API_KEY" $BASE_URL/query/local | jq
echo ""

echo "5. Query local files (with Authorization Bearer)"
echo "curl -H 'Authorization: Bearer $API_KEY' $BASE_URL/query/local"
curl -H "Authorization: Bearer $API_KEY" $BASE_URL/query/local | jq
echo ""

echo "6. Query S3 files"
echo "curl -H 'X-API-Key: $API_KEY' $BASE_URL/query/s3"
curl -H "X-API-Key: $API_KEY" $BASE_URL/query/s3 | jq
echo ""

echo "7. Get current schedule"
echo "curl -H 'X-API-Key: $API_KEY' $BASE_URL/schedule"
curl -H "X-API-Key: $API_KEY" $BASE_URL/schedule | jq
echo ""

echo "8. Update schedule"
echo "curl -H 'X-API-Key: $API_KEY' -H 'Content-Type: application/json' -d '{\"upload_times\": [\"08:00\", \"16:00\"]}' $BASE_URL/schedule"
curl -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"upload_times": ["08:00", "16:00"]}' \
     $BASE_URL/schedule | jq
echo ""

echo "9. Trigger manual upload"
echo "curl -H 'X-API-Key: $API_KEY' -X POST $BASE_URL/upload/manual"
curl -H "X-API-Key: $API_KEY" -X POST $BASE_URL/upload/manual | jq
echo ""

echo "10. Download range (last 24 hours)"
START_TIME=$(date -d '1 day ago' --iso-8601=seconds)
END_TIME=$(date --iso-8601=seconds)
echo "curl -H 'X-API-Key: $API_KEY' -H 'Content-Type: application/json' -d '{\"start_time\": \"$START_TIME\", \"end_time\": \"$END_TIME\"}' $BASE_URL/download/range -o range_download.tar.gz"
curl -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d "{\"start_time\": \"$START_TIME\", \"end_time\": \"$END_TIME\"}" \
     $BASE_URL/download/range \
     -o range_download.tar.gz

if [ -f "range_download.tar.gz" ]; then
    echo "✅ Downloaded range_download.tar.gz ($(ls -lh range_download.tar.gz | awk '{print $5}'))"
else
    echo "❌ Download failed"
fi
echo ""

echo "🎉 All cURL examples completed!"
