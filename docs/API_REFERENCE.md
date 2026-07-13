# Bridge 2026 API Reference

## Dashboard Endpoints

### Polling & Feedback

#### GET `/api/polls`
Get all polls with vote counts
```
Response: [
  {
    "question": "What's your favorite feature?",
    "options": [
      {"name": "Analytics", "votes": 28},
      {"name": "Feedback", "votes": 17}
    ],
    "timestamp": "2024-01-15T10:30:00"
  }
]
```

#### GET `/api/votes`
Get all votes from Excel
```
Response: [
  {
    "timestamp": "2024-01-15T10:35:00",
    "username": "john_doe",
    "question": "What's your favorite feature?",
    "choice": "Analytics"
  }
]
```

#### POST `/submit`
Create a new poll from dashboard
```
Body: {
  "question": "What's your favorite feature?",
  "option1": "Analytics",
  "option2": "Feedback"
}
Response: {"message": "Poll created successfully", "status": "ok"}
```

#### GET `/api/votes/export`
Export all votes as CSV file
```
Response: CSV file download
Headers: Timestamp, Username, Question, Choice
```

---

## Poll Data Endpoints

#### GET `/api/data/status`
Get current statistics from Excel data
```
Response: {
  "total_votes": 234,
  "unique_voters": 156,
  "polls_count": 12,
  "data_status": "Synced",
  "last_updated": "2024-01-15T10:35:00"
}
```

#### GET `/api/summary`
Get vote summary grouped by question
```
Response: [
  {
    "question": "Favorite feature?",
    "total_votes": 45,
    "choices": {"Analytics": 28, "Feedback": 17}
  }
]
```

#### GET `/api/polls/<poll_id>`
Get detailed statistics for a specific poll
```
Example: /api/polls/1234567890
Response: {
  "total_votes": 42,
  "question": "What's your favorite feature?",
  "choices": {"Analytics": 25, "Feedback": 17},
  "voters": ["user1", "user2", "user3", ...]
}
```

#### GET `/api/export/csv`
Export all Excel data as CSV
```
Response: CSV file download
Format: Timestamp, Username, User_ID, Question, Choice, Poll_ID, Vote_Count
```

---

## Bot Status Endpoints

#### GET `/api/bot-status`
Get current bot statistics
```
Response: {
  "online": true,
  "uptime": "2d 14h 32m",
  "last_command": "/poll",
  "votes_today": 23,
  "votes_total": 234
}
```

---

## Schedule Endpoints

#### GET `/api/schedule`
Get workshop schedule (if enabled)
```
Response: [
  {
    "id": 1,
    "name": "Opening Keynote",
    "pillar": "Professional Development",
    "speaker": "Dr. Jane Smith",
    "time": "9:00 AM - 10:00 AM",
    "location": "Main Hall",
    "description": "Welcome to Bridge 2026!"
  }
]
```

---

## Error Responses

All endpoints return errors in this format:
```json
{
  "error": "Description of what went wrong"
}
```

### Common Status Codes
- `200`: Success
- `204`: No Content (empty response)
- `400`: Bad Request (missing or invalid data)
- `404`: Not Found
- `500`: Server Error (check logs)

---

## Usage Examples

### JavaScript/Fetch
```javascript
// Get all votes
const votes = await fetch('/api/votes').then(r => r.json());
console.log(votes);

// Create a poll
const response = await fetch('/submit', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    question: "What's your feedback?",
    option1: "Excellent",
    option2: "Needs Improvement"
  })
});

// Download CSV
document.getElementById('export-btn').onclick = () => {
  window.location.href = '/api/export/csv';
};
```

### Python/Requests
```python
import requests

# Get stats
stats = requests.get('http://localhost:5000/api/data/status').json()
print(f"Total votes: {stats['total_votes']}")

# Get poll details
poll = requests.get('http://localhost:5000/api/polls/1234567890').json()
print(f"Poll: {poll['question']}")
print(f"Results: {poll['choices']}")
```

### cURL
```bash
# Get statistics
curl http://localhost:5000/api/data/status

# Get summary
curl http://localhost:5000/api/summary

# Export CSV
curl http://localhost:5000/api/export/csv > feedback.csv
```

---

## Rate Limiting (Future)
Currently no rate limiting. Will be added in Phase 2 update.

## Authentication (Future)
Optional API key authentication will be added for Colab integration.

---

## Server Requirements

**Minimum**: 
- Python 3.8+
- 512MB RAM
- 100MB disk space

**Recommended**:
- Python 3.10+
- 2GB RAM
- 1GB disk space (for data growth)

---

## Performance Tips

1. **Caching**: Dashboard caches API responses for 30 seconds
2. **Batch Exports**: Use CSV export for large datasets
3. **Filtering**: Server-side filtering on votes endpoint
4. **Connection Pooling**: Handled automatically by Flask

---

**Last Updated**: 2024
**Version**: 2.0 (Excel Manager)

