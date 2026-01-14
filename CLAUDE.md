# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask-based network latency monitoring application designed for Cloud Foundry deployment. Monitors ping latency to multiple hosts using HTTP/TCP/ICMP methods, with a web dashboard and REST API.

## Commands

### Local Development
```bash
pip install -r requirements.txt
python app.py                    # Runs on http://localhost:8080
```

### Cloud Foundry Deployment
```bash
cf login -a <api-endpoint> -u <username> -o <org> -s <space>
cf push                          # Deploys using manifest.yml
./deploy.sh                      # Interactive deployment script
```

### Environment Variables
- `MONITORED_HOSTS`: Comma-separated hostnames (default: `vcenter.skynetsystems.io,google.com,cloudflare.com`)
- `CHECK_INTERVAL`: Seconds between checks (default: `60`)
- `TCP_PORT`: Port for latency checks (default: `443`)
- `PORT`: HTTP server port (default: `8080`, overridden by CF)

## Architecture

**Single-file Flask app** (`app.py`) with a background monitoring thread:

1. **Monitor Thread** (`monitor_latency`): Runs continuously in background, checking latency for all hosts at `CHECK_INTERVAL`. Uses three fallback methods: HTTP HEAD request → TCP socket connection → ICMP ping.

2. **Data Storage**: In-memory `deque` per host with 24-hour retention (calculated as `86400 / CHECK_INTERVAL` data points). Host list persisted to `/tmp/monitored_hosts.txt` for worker synchronization.

3. **Thread Safety**: Global `lock` protects `monitored_hosts` set and `latency_data` dict access.

4. **Web Layer**: Flask serves Jinja template (`templates/index.html`) with Chart.js for real-time graphs. Dashboard auto-refreshes at the check interval.

## Key API Endpoints
- `GET /api/latency` - All latency data
- `GET /api/current` - Latest reading per host
- `POST /api/hosts/add` - Add host `{"host": "example.com"}`
- `POST /api/hosts/remove` - Remove host
- `GET /health` - CF health check
- `GET /debug` - Connectivity diagnostics

## Production Configuration

Uses gunicorn with single worker (`--workers 1`) to ensure the monitor thread runs exactly once. The `Procfile` and `manifest.yml` both specify this configuration.
