# Latency Monitor - Cloud Foundry Application

A real-time network latency monitoring application designed for Cloud Foundry. Monitor ping latency to multiple hosts with a beautiful web dashboard and REST API.

## Features

- 🌐 Monitor multiple hosts simultaneously
- ➕ **Add/remove hosts dynamically** from the UI
- 📊 Real-time latency graphs with Chart.js
- 🔄 Auto-refreshing dashboard
- 💾 **24-hour data retention** - navigate away and come back, your data persists
- 📡 REST API endpoints for integration
- 🏥 Health check endpoint for Cloud Foundry
- ⚙️ Configurable via environment variables

## Quick Start

### Prerequisites

- Cloud Foundry CLI installed
- Access to a Cloud Foundry instance
- CF login credentials

### Deploy to Cloud Foundry

1. **Clone or download this application**

2. **Customize the monitored hosts** (optional)

   Edit `manifest.yml` to change the hosts you want to monitor:
   ```yaml
   env:
     MONITORED_HOSTS: your-host1.com,your-host2.com,vcenter.skynetsystems.io
   ```

3. **Login to Cloud Foundry**
   ```bash
   cf login -a <api-endpoint> -u <username> -o <org> -s <space>
   ```

4. **Push the application**
   ```bash
   cf push
   ```

5. **Access the application**
   ```bash
   cf apps
   ```
   
   The output will show your app URL. Open it in a browser!

## Configuration

Configure the application using environment variables in `manifest.yml` or via CF CLI:

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONITORED_HOSTS` | Comma-separated list of default hosts to monitor (can be changed via UI) | `vcenter.skynetsystems.io,google.com,cloudflare.com` |
| `CHECK_INTERVAL` | Interval between checks in seconds | `60` |
| `TCP_PORT` | TCP port for latency checks (443 for HTTPS, 80 for HTTP) | `443` |

**Note:** Data retention is automatically set to 24 hours based on `CHECK_INTERVAL`. For example:
- `CHECK_INTERVAL=60` → 1440 data points (24 hours)
- `CHECK_INTERVAL=30` → 2880 data points (24 hours)
- `CHECK_INTERVAL=300` → 288 data points (24 hours)

### Update environment variables after deployment

```bash
cf set-env latency-monitor MONITORED_HOSTS "host1.com,host2.com,host3.com"
cf set-env latency-monitor CHECK_INTERVAL "30"
cf restage latency-monitor
```

## API Endpoints

### GET `/`
Web dashboard with real-time latency visualization

### GET `/api/latency`
Get all latency data for all monitored hosts

**Response:**
```json
{
  "hosts": ["host1.com", "host2.com"],
  "data": {
    "host1.com": [
      {
        "timestamp": "2026-01-13T10:30:00",
        "latency": 25.3,
        "status": "ok"
      }
    ]
  },
  "check_interval": 60,
  "max_history_hours": 24
}
```

### GET `/api/latency/<host>`
Get latency data for a specific host

**Example:**
```bash
curl https://latency-monitor.cfapps.io/api/latency/google.com
```

### GET `/api/current`
Get only the most recent latency for all hosts

**Response:**
```json
{
  "host1.com": {
    "timestamp": "2026-01-13T10:30:00",
    "latency": 25.3,
    "status": "ok"
  }
}
```

### GET `/api/hosts`
Get list of currently monitored hosts

**Response:**
```json
{
  "hosts": ["google.com", "vcenter.skynetsystems.io"],
  "count": 2
}
```

### POST `/api/hosts/add`
Add a new host to monitor

**Request:**
```json
{
  "host": "example.com"
}
```

**Response:**
```json
{
  "success": true,
  "host": "example.com",
  "message": "Now monitoring example.com",
  "total_hosts": 3
}
```

**Example:**
```bash
curl -X POST https://latency-monitor.cfapps.io/api/hosts/add \
  -H "Content-Type: application/json" \
  -d '{"host":"example.com"}'
```

### POST `/api/hosts/remove`
Remove a host from monitoring (historical data preserved)

**Request:**
```json
{
  "host": "example.com"
}
```

**Response:**
```json
{
  "success": true,
  "host": "example.com",
  "message": "Stopped monitoring example.com",
  "total_hosts": 2,
  "note": "Historical data preserved"
}
```

**Example:**
```bash
curl -X POST https://latency-monitor.cfapps.io/api/hosts/remove \
  -H "Content-Type: application/json" \
  -d '{"host":"example.com"}'
```

### GET `/health`
Health check endpoint for Cloud Foundry

## Local Development

### Run locally

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables** (optional)
   ```bash
   export MONITORED_HOSTS="localhost,google.com"
   export CHECK_INTERVAL="30"
   export PORT="8080"
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the dashboard**
   Open http://localhost:8080 in your browser

## Scaling

### Scale instances
```bash
cf scale latency-monitor -i 2
```

### Scale memory
```bash
cf scale latency-monitor -m 512M
```

## Monitoring & Logs

### View logs
```bash
cf logs latency-monitor --recent
```

### Stream logs
```bash
cf logs latency-monitor
```

### Check app status
```bash
cf app latency-monitor
```

## Troubleshooting

### App won't start
1. Check logs: `cf logs latency-monitor --recent`
2. Verify manifest.yml is valid
3. Ensure Python buildpack is available in your CF

### No data showing
1. Verify hosts in MONITORED_HOSTS are reachable
2. Check that ICMP (ping) is not blocked by firewalls
3. Review logs for ping errors

### High memory usage
1. Reduce MAX_HISTORY value
2. Increase CHECK_INTERVAL to reduce frequency
3. Scale memory: `cf scale latency-monitor -m 512M`

## Architecture

```
┌─────────────────┐
│   Browser       │
│   Dashboard     │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask Web App  │
│  - REST API     │
│  - Templates    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Monitor Thread │
│  - Ping hosts   │
│  - Store data   │
└─────────────────┘
```

## File Structure

```
latency-monitor/
├── app.py                 # Main Flask application
├── templates/
│   └── index.html        # Web dashboard
├── requirements.txt      # Python dependencies
├── manifest.yml         # Cloud Foundry manifest
├── Procfile            # Process definition
└── README.md          # This file
```

## Advanced Usage

### Integration with monitoring tools

Use the API endpoints to integrate with monitoring tools like Prometheus, Grafana, or custom scripts:

```bash
# Get current latency for alerting
LATENCY=$(curl -s https://your-app.cfapps.io/api/current | jq '.["vcenter.skynetsystems.io"].latency')

if (( $(echo "$LATENCY > 100" | bc -l) )); then
  echo "High latency detected: ${LATENCY}ms"
fi
```

### Custom deployment with route

```bash
cf push latency-monitor -n custom-route-name
```

## Security Considerations

- This app uses ICMP ping which requires network connectivity
- Ensure your Cloud Foundry space has appropriate network policies
- Consider adding authentication for production use
- API endpoints are currently open - add auth middleware if needed

## License

MIT License - Feel free to use and modify

## Support

For issues or questions:
1. Check logs: `cf logs latency-monitor`
2. Review troubleshooting section
3. Verify CF environment and connectivity
