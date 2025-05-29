# Video Annotation API Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [Core Endpoints](#core-endpoints)
4. [File Management Endpoints](#file-management-endpoints)
5. [Scheduling Endpoints](#scheduling-endpoints)
6. [Workflow Examples](#workflow-examples)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

## Introduction

The Video Annotation API provides comprehensive capabilities for managing annotated video files, their metadata, and scheduling automatic uploads to Amazon S3. This system is designed to handle video files with associated label annotations, providing secure access to authorized clients.

**Key Features:**
- Secure API key authentication
- Query video files with metadata
- Download individual videos or ranges
- Schedule automatic uploads to S3
- Trigger manual uploads
- Access to both local and cloud-stored videos

**Base URL:** `http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000`

## Authentication

All protected endpoints require API key authentication using one of the following methods:

### Method 1: X-API-Key Header
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" https://api-endpoint
```

### Method 2: Authorization Bearer Token
```bash
curl -H "Authorization: Bearer sk_live_abc123def456ghi789jkl012mno345pqr678" https://api-endpoint
```

### Obtaining an API Key
For testing purposes, you can generate a new API key using:

```bash
curl -X POST http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/auth/generate-key
```

**Response:**
```json
{
  "api_key": "sk_live_De7NudIdAGw-1NN8A0qcTTdb3AERARykttP0q3tqp4o",
  "note": "This is for testing only. In production, keys should be managed securely."
}
```

**Note:** In production, API keys are managed by system administrators and should be kept secure.

## Core Endpoints

### Health Check
Verify if the API is operational. This endpoint does not require authentication.

**Request:**
```bash
curl -X GET http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-05-29T06:17:04.623231",
  "version": "1.0.0"
}
```

### Query Local Files
Retrieve a list of all available video files on the server with detailed metadata.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/query/local
```

**Response:**
```json
{
  "count": 15,
  "files": [
    {
      "datetime": "2025-04-17T09:10:31",
      "exists": true,
      "filename": "channel1002_20250417T091031.avi",
      "id": "6836d799d249",
      "label_count": 43,
      "labels": [
        "channel1002_20250417T091031_1.txt",
        "channel1002_20250417T091031_10.txt",
        "channel1002_20250417T091031_11.txt",
        "..."
      ],
      "size_mb": 8.5
    },
    "..."
  ]
}
```

**Response Fields:**
- `count`: Total number of files
- `files`: Array of file objects with the following properties:
  - `id`: Unique identifier for the file (use for download operations)
  - `filename`: Original video filename
  - `datetime`: ISO-formatted datetime extracted from the filename
  - `size_mb`: File size in megabytes
  - `label_count`: Number of annotation label files associated with this video
  - `labels`: Array of label filenames (first 10 only)
  - `exists`: Boolean indicating if the file exists on disk

### Query S3 Files
Retrieve a list of all archived video files stored in Amazon S3.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/query/s3
```

**Response:**
```json
{
  "count": 15,
  "files": [
    {
      "filename": "channel1002_20250417T084930.tar.gz",
      "id": "65953b97b71c",
      "key": "annotation/2025/04/17/channel1002_20250417T084930.tar.gz",
      "last_modified": "2025-05-29T06:16:17+00:00",
      "size": 19674522,
      "size_mb": 18.76
    },
    "..."
  ]
}
```

**Response Fields:**
- `count`: Total number of files
- `files`: Array of file objects with the following properties:
  - `id`: Unique identifier for the S3 object (use for download operations)
  - `filename`: Archive filename
  - `key`: Full S3 object key
  - `last_modified`: Timestamp when the file was last modified
  - `size`: File size in bytes
  - `size_mb`: File size in megabytes

### Legacy Combined Query
Query both local and S3 files in a single request.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/query
```

**Response:**
```json
{
  "local": {
    "files": [...],
    "count": 15
  },
  "s3": {
    "files": [...],
    "count": 15
  }
}
```

## File Management Endpoints

### Download Local File
Download a specific video file with its labels as a tar.gz archive.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/download/local/6836d799d249 \
     -o video_download.tar.gz
```

**Parameters:**
- `file_id`: The ID of the file to download (obtained from `/query/local` endpoint)

**Response:**
A binary stream containing the tar.gz archive with:
- The original video file
- All associated label files in a `modified_labels` directory

**Example Archive Structure:**
```
video_download.tar.gz
├── channel1002_20250417T091031.avi
└── modified_labels/
    ├── channel1002_20250417T091031_1.txt
    ├── channel1002_20250417T091031_2.txt
    └── ...
```

### Download S3 File
Download a specific archived file from S3.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/download/s3/65953b97b71c \
     -o s3_download.tar.gz
```

**Parameters:**
- `s3_file_id`: The ID of the S3 file to download (obtained from `/query/s3` endpoint)

**Response:**
A binary stream containing the tar.gz archive from S3.

### Download Range
Download all videos and their labels within a specific time range as a single archive.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     -H "Content-Type: application/json" \
     -d '{"start_time": "2025-04-17T08:00:00", "end_time": "2025-04-17T10:00:00"}' \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/download/range \
     -o range_download.tar.gz
```

**Request Body:**
```json
{
  "start_time": "2025-04-17T08:00:00",
  "end_time": "2025-04-17T10:00:00"
}
```

**Parameters:**
- `start_time`: ISO-formatted datetime for the beginning of the range (inclusive)
- `end_time`: ISO-formatted datetime for the end of the range (inclusive)

**Response:**
A binary stream containing a tar.gz archive with:
- All videos in the specified time range (in a `videos` directory)
- All associated label files (in a `modified_labels` directory)

**Example Archive Structure:**
```
range_download.tar.gz
├── videos/
│   ├── channel1002_20250417T084930.avi
│   ├── channel1002_20250417T085102.avi
│   └── ...
└── modified_labels/
    ├── channel1002_20250417T084930_1.txt
    ├── channel1002_20250417T084930_2.txt
    └── ...
```

## Scheduling Endpoints

### Get Upload Schedule
Retrieve the current automatic upload schedule.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/schedule
```

**Response:**
```json
{
  "scheduler_running": true,
  "upload_times": [
    "10:00",
    "12:00",
    "13:00",
    "17:00",
    "20:00"
  ]
}
```

### Update Upload Schedule
Modify the automatic upload schedule.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     -H "Content-Type: application/json" \
     -d '{"upload_times": ["08:00", "16:00"]}' \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/schedule
```

**Request Body:**
```json
{
  "upload_times": ["08:00", "16:00"]
}
```

**Response:**
```json
{
  "status": "success",
  "upload_times": [
    "08:00",
    "16:00"
  ]
}
```

### Trigger Manual Upload
Manually trigger an upload of all videos to S3.

**Request:**
```bash
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     -X POST \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/upload/manual
```

**Response:**
```json
{
  "message": "Upload completed",
  "result": {
    "failed": 0,
    "uploaded": 15
  },
  "status": "success"
}
```

## Workflow Examples

### Example 1: Find and Download a Specific Video

```bash
# Step 1: Query available local videos
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/query/local > videos.json

# Step 2: Extract the ID of the desired video (using jq)
# For example, to get the first video:
VIDEO_ID=$(cat videos.json | jq -r '.files[0].id')

# Step 3: Download the video with its labels
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/download/local/$VIDEO_ID \
     -o video_download.tar.gz

# Step 4: Extract the archive
tar -xzf video_download.tar.gz
```

### Example 2: Download Videos from a Specific Date

```bash
# Download all videos from April 17, 2025 between 8 AM and 10 AM
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     -H "Content-Type: application/json" \
     -d '{"start_time": "2025-04-17T08:00:00", "end_time": "2025-04-17T10:00:00"}' \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/download/range \
     -o april17_morning.tar.gz
```

### Example 3: Scheduled Upload Automation

```bash
# Step 1: Get current schedule
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/schedule

# Step 2: Update schedule to 4 times daily (6AM, 12PM, 6PM, 12AM)
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     -H "Content-Type: application/json" \
     -d '{"upload_times": ["06:00", "12:00", "18:00", "00:00"]}' \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/schedule

# Step 3: Trigger immediate upload (optional)
curl -H "X-API-Key: sk_live_abc123def456ghi789jkl012mno345pqr678" \
     -X POST \
     http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000/upload/manual
```

### Example 4: Automated Daily Report Script

```bash
#!/bin/bash
# daily_report.sh - Example of how to generate a daily video report

API_KEY="sk_live_abc123def456ghi789jkl012mno345pqr678"
BASE_URL="http://ec2-65-0-71-245.ap-south-1.compute.amazonaws.com:5000"
TODAY=$(date +"%Y-%m-%d")
YESTERDAY=$(date -d "yesterday" +"%Y-%m-%d")

# Generate report file
echo "Video Report for $YESTERDAY to $TODAY" > report.txt
echo "===========================================" >> report.txt

# Get local files
LOCAL_DATA=$(curl -s -H "X-API-Key: $API_KEY" $BASE_URL/query/local)
LOCAL_COUNT=$(echo $LOCAL_DATA | jq '.count')
echo "Local Videos Available: $LOCAL_COUNT" >> report.txt

# Get S3 files
S3_DATA=$(curl -s -H "X-API-Key: $API_KEY" $BASE_URL/query/s3)
S3_COUNT=$(echo $S3_DATA | jq '.count')
echo "S3 Archives Available: $S3_COUNT" >> report.txt

# Download yesterday's videos
echo "Downloading videos from $YESTERDAY..." >> report.txt
START_TIME="${YESTERDAY}T00:00:00"
END_TIME="${YESTERDAY}T23:59:59"

curl -s -H "X-API-Key: $API_KEY" \
     -H "Content-Type: application/json" \
     -d "{\"start_time\": \"$START_TIME\", \"end_time\": \"$END_TIME\"}" \
     $BASE_URL/download/range \
     -o yesterday_videos.tar.gz

# Check if download was successful
if [ -f "yesterday_videos.tar.gz" ]; then
    SIZE=$(du -h yesterday_videos.tar.gz | cut -f1)
    echo "Download successful. Archive size: $SIZE" >> report.txt
    
    # List videos in archive
    echo "Videos in archive:" >> report.txt
    tar -tzf yesterday_videos.tar.gz | grep "\.avi" | sed 's/videos\//  - /' >> report.txt
else
    echo "No videos found for yesterday or download failed." >> report.txt
fi

echo "Report complete." >> report.txt
```

## Error Handling

### Common HTTP Status Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (invalid or missing API key) |
| 404 | Not Found (resource doesn't exist) |
| 500 | Internal Server Error |

### Error Response Format

All error responses follow this JSON format:

```json
{
  "status": "error",
  "message": "Descriptive error message"
}
```

### Common Error Messages

| Error Message | Description | Solution |
|---------------|-------------|----------|
| "API key required" | No API key provided | Include X-API-Key header or Authorization Bearer token |
| "Invalid API key" | Provided API key is not valid | Use a valid API key |
| "File not found" | Requested file ID doesn't exist | Verify the file ID using the query endpoints |
| "Invalid datetime format" | Incorrect datetime string | Use ISO format (YYYY-MM-DDThh:mm:ss) |
| "No videos found in time range" | The specified range contains no videos | Adjust time range or verify data exists for that period |

## Best Practices

### Working with Large Files

1. **Download in Ranges**: For large datasets, break downloads into smaller time ranges
2. **Check File Size**: Query endpoints provide file sizes - be prepared to handle large downloads
3. **Streaming Processing**: Process large tar.gz files as streams rather than loading entirely into memory

### Date and Time Handling

1. **ISO Format**: Always use ISO 8601 format for dates and times (YYYY-MM-DDThh:mm:ss)
2. **Timezone Handling**: Times are in UTC unless specified. Include timezone offset if needed
3. **Range Limitations**: Avoid excessive time ranges (>30 days) as they may timeout or create very large archives

### Authentication

1. **Header Usage**: Prefer X-API-Key header for simplicity and clarity
2. **Key Security**: Never expose API keys in client-side code or public repositories
3. **Rate Limiting**: Implement rate limiting in your integration to avoid overloading the API

### Integration Recommendations

1. **Health Checks**: Periodically check the `/health` endpoint to ensure the API is operational
2. **Error Handling**: Implement proper error handling for all API calls
3. **Scheduled Tasks**: Use the scheduling endpoints to automate routine tasks
4. **Caching**: Cache query results when appropriate to reduce API load
5. **Exponential Backoff**: Implement exponential backoff for retries on failed requests

---

For further assistance or to report issues, please contact the system administrator. This API documentation is current as of May 2025.
