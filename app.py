#!/usr/bin/env python3
"""
Latency Monitor - Cloud Foundry Application
Monitors network latency to specified hosts
"""

import os
import time
import subprocess
import threading
from datetime import datetime
from collections import deque
from flask import Flask, render_template, jsonify, request, send_from_directory

app = Flask(__name__)

# Configuration
DEFAULT_HOSTS = os.getenv('MONITORED_HOSTS', 'vcenter.skynetsystems.io,google.com,cloudflare.com').split(',')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '60'))  # seconds
TCP_PORT = int(os.getenv('TCP_PORT', '443'))  # TCP port for latency checks

# Calculate max history for 24 hours
MAX_HISTORY = int(86400 / CHECK_INTERVAL)

print(f"Configuration: CHECK_INTERVAL={CHECK_INTERVAL}s, MAX_HISTORY={MAX_HISTORY} data points (24 hours)", flush=True)

# Persistent host storage file
HOST_FILE = '/tmp/monitored_hosts.txt'

def load_hosts():
    """Load hosts from persistent storage or use defaults"""
    if os.path.exists(HOST_FILE):
        try:
            with open(HOST_FILE, 'r') as f:
                hosts = set(line.strip() for line in f.readlines() if line.strip())
                if hosts:
                    print(f"Loaded {len(hosts)} unique hosts from persistent storage", flush=True)
                    return hosts
        except Exception as e:
            print(f"Error loading hosts from file: {e}", flush=True)
    
    # Use defaults if file doesn't exist or is empty
    print(f"Using default hosts from environment", flush=True)
    default_hosts = set(host.strip() for host in DEFAULT_HOSTS if host.strip())
    return default_hosts

def save_hosts():
    """Save current hosts to persistent storage"""
    try:
        # Use a set to ensure uniqueness
        unique_hosts = set(monitored_hosts)
        with open(HOST_FILE, 'w') as f:
            for host in sorted(unique_hosts):  # Sort for consistency
                f.write(f"{host}\n")
        print(f"Saved {len(unique_hosts)} unique hosts to persistent storage", flush=True)
    except Exception as e:
        print(f"Error saving hosts to file: {e}", flush=True)

# In-memory storage for latency data
monitored_hosts = load_hosts()  # Load from file or use defaults
latency_data = {host: deque(maxlen=MAX_HISTORY) for host in monitored_hosts}
lock = threading.Lock()
monitor_thread_started = False


def start_monitor_thread():
    """Start the monitoring thread (called once when module loads)"""
    global monitor_thread_started
    if not monitor_thread_started:
        print(f"=== STARTING LATENCY MONITOR ===", flush=True)
        print(f"Default hosts: {', '.join(monitored_hosts)}", flush=True)
        print(f"Check interval: {CHECK_INTERVAL} seconds", flush=True)
        print(f"TCP port: {TCP_PORT}", flush=True)
        print(f"Data retention: {MAX_HISTORY} data points (24 hours)", flush=True)
        
        monitor_thread = threading.Thread(target=monitor_latency, daemon=True)
        monitor_thread.start()
        monitor_thread_started = True
        print("=== MONITOR THREAD STARTED ===", flush=True)


def ping_host(host, port=443):
    """
    Measure latency to a host using multiple methods
    1. HTTP/HTTPS request (most reliable in CF)
    2. TCP socket connection
    3. ICMP ping (fallback)
    """
    import socket
    import urllib.request
    import ssl
    
    # Method 1: HTTP/HTTPS Request (most reliable)
    latencies = []
    protocol = 'https' if port == 443 else 'http'
    
    for attempt in range(3):
        try:
            start = time.time()
            context = ssl._create_unverified_context()
            req = urllib.request.Request(f'{protocol}://{host}', method='HEAD')
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                latency_ms = (time.time() - start) * 1000
                latencies.append(latency_ms)
                print(f"HTTP latency to {host}: {latency_ms:.2f}ms", flush=True)
        except Exception as e:
            print(f"HTTP request to {host} attempt {attempt+1} failed: {e}", flush=True)
            continue
    
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"Average HTTP latency to {host}: {avg:.2f}ms", flush=True)
        return avg
    
    # Method 2: TCP Socket Connection
    print(f"HTTP failed for {host}, trying TCP socket...", flush=True)
    for attempt in range(3):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            latency_ms = (time.time() - start) * 1000
            sock.close()
            latencies.append(latency_ms)
            print(f"TCP latency to {host}:{port}: {latency_ms:.2f}ms", flush=True)
        except Exception as e:
            print(f"TCP connection to {host}:{port} attempt {attempt+1} failed: {e}", flush=True)
            continue
    
    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"Average TCP latency to {host}: {avg:.2f}ms", flush=True)
        return avg
    
    # Method 3: ICMP Ping (fallback)
    print(f"TCP failed for {host}, trying ICMP ping...", flush=True)
    try:
        result = subprocess.run(
            ['ping', '-c', '3', '-W', '2', host],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            output = result.stdout
            
            for line in output.split('\n'):
                if 'avg' in line or 'Average' in line:
                    parts = line.split('=')[-1].strip().split('/')
                    if len(parts) >= 2:
                        latency = float(parts[1])
                        print(f"ICMP ping latency to {host}: {latency:.2f}ms", flush=True)
                        return latency
            
            latencies = []
            for line in output.split('\n'):
                if 'time=' in line:
                    time_str = line.split('time=')[1].split()[0]
                    latencies.append(float(time_str))
            
            if latencies:
                avg = sum(latencies) / len(latencies)
                print(f"Average ICMP latency to {host}: {avg:.2f}ms", flush=True)
                return avg
    except Exception as e:
        print(f"ICMP ping to {host} failed: {e}", flush=True)
    
    print(f"All latency check methods failed for {host}", flush=True)
    return None


def monitor_latency():
    """Background thread to continuously monitor latency"""
    print("Monitor thread running...", flush=True)
    
    while True:
        timestamp = datetime.now().isoformat()
        
        # Get current list of hosts (thread-safe)
        with lock:
            hosts_to_check = list(monitored_hosts)
        
        for host in hosts_to_check:
            print(f"Checking latency for {host}...", flush=True)
            latency = ping_host(host, TCP_PORT)
            
            with lock:
                # Initialize deque for new hosts
                if host not in latency_data:
                    latency_data[host] = deque(maxlen=MAX_HISTORY)
                
                latency_data[host].append({
                    'timestamp': timestamp,
                    'latency': latency,
                    'status': 'ok' if latency else 'down'
                })
        
        print(f"Check complete. Sleeping for {CHECK_INTERVAL} seconds...", flush=True)
        time.sleep(CHECK_INTERVAL)


# Start monitoring thread when module loads (works with gunicorn)
start_monitor_thread()


@app.route('/')
def index():
    """Main dashboard"""
    with lock:
        hosts = list(monitored_hosts)
    return render_template('index.html', hosts=hosts, interval=CHECK_INTERVAL)


@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)


@app.route('/api/latency')
def get_latency():
    """API endpoint to get current latency data"""
    global monitored_hosts
    with lock:
        # Reload from persistent storage to ensure workers are in sync
        if os.path.exists(HOST_FILE):
            try:
                with open(HOST_FILE, 'r') as f:
                    file_hosts = set(line.strip() for line in f.readlines() if line.strip())
                    if file_hosts:
                        monitored_hosts = file_hosts
            except Exception as e:
                print(f"Error reloading hosts: {e}", flush=True)
        
        hosts = list(monitored_hosts)
        # Ensure all hosts have a data array (even if empty)
        data_dict = {}
        for host in hosts:
            data_dict[host] = list(latency_data.get(host, []))
        
        return jsonify({
            'hosts': hosts,
            'data': data_dict,
            'check_interval': CHECK_INTERVAL,
            'max_history_hours': 24
        })


@app.route('/api/latency/<host>')
def get_host_latency(host):
    """API endpoint to get latency data for a specific host"""
    if host not in latency_data:
        return jsonify({'error': 'Host not found'}), 404
    
    with lock:
        return jsonify({
            'host': host,
            'data': list(latency_data[host]),
            'check_interval': CHECK_INTERVAL
        })


@app.route('/api/current')
def get_current():
    """Get only the most recent latency for all hosts"""
    with lock:
        current = {}
        for host in monitored_hosts:
            if host in latency_data and latency_data[host]:
                current[host] = latency_data[host][-1]
            else:
                current[host] = {'timestamp': None, 'latency': None, 'status': 'unknown'}
        
        return jsonify(current)


@app.route('/api/hosts', methods=['GET'])
def get_hosts():
    """Get list of currently monitored hosts"""
    # Reload from file to ensure workers are in sync
    global monitored_hosts
    with lock:
        # Reload from persistent storage
        if os.path.exists(HOST_FILE):
            try:
                with open(HOST_FILE, 'r') as f:
                    file_hosts = set(line.strip() for line in f.readlines() if line.strip())
                    if file_hosts:
                        monitored_hosts = file_hosts
                        print(f"Reloaded {len(monitored_hosts)} hosts from file", flush=True)
            except Exception as e:
                print(f"Error reloading hosts: {e}", flush=True)
        
        return jsonify({
            'hosts': list(monitored_hosts),
            'count': len(monitored_hosts)
        })


@app.route('/api/hosts/add', methods=['POST'])
def add_host():
    """Add a new host to monitor"""
    data = request.get_json()
    
    if not data or 'host' not in data:
        return jsonify({'error': 'Missing host parameter'}), 400
    
    host = data['host'].strip()
    
    if not host:
        return jsonify({'error': 'Host cannot be empty'}), 400
    
    # Basic validation
    if len(host) > 253:  # Max domain length
        return jsonify({'error': 'Host name too long'}), 400
    
    with lock:
        if host in monitored_hosts:
            return jsonify({'error': 'Host already being monitored', 'host': host}), 409
        
        monitored_hosts.add(host)
        # Initialize empty deque for new host
        latency_data[host] = deque(maxlen=MAX_HISTORY)
        current_hosts = list(monitored_hosts)
        
        # Persist the change
        save_hosts()
    
    print(f"Added new host: {host}. Total hosts: {len(current_hosts)}", flush=True)
    
    return jsonify({
        'success': True,
        'host': host,
        'message': f'Now monitoring {host}',
        'total_hosts': len(current_hosts)
    })


@app.route('/api/hosts/remove', methods=['POST'])
def remove_host():
    """Remove a host from monitoring"""
    data = request.get_json()
    
    if not data or 'host' not in data:
        return jsonify({'error': 'Missing host parameter'}), 400
    
    host = data['host'].strip()
    
    with lock:
        if host not in monitored_hosts:
            return jsonify({'error': 'Host not found', 'host': host}), 404
        
        monitored_hosts.remove(host)
        # Keep the historical data but stop monitoring
        # Data will still be accessible via API
        current_hosts = list(monitored_hosts)
        
        # Persist the change
        save_hosts()
    
    print(f"Removed host: {host}. Remaining hosts: {len(current_hosts)}", flush=True)
    
    return jsonify({
        'success': True,
        'host': host,
        'message': f'Stopped monitoring {host}',
        'total_hosts': len(current_hosts),
        'note': 'Historical data preserved'
    })


@app.route('/health')
def health():
    """Health check endpoint for Cloud Foundry"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


@app.route('/debug')
def debug():
    """Debug endpoint to test connectivity and show errors"""
    import socket
    import urllib.request
    import ssl
    
    with lock:
        hosts = list(monitored_hosts)
    
    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'monitored_hosts': hosts,
        'tcp_port': TCP_PORT,
        'check_interval': CHECK_INTERVAL,
        'max_history': MAX_HISTORY,
        'connectivity_tests': {}
    }
    
    for host in hosts:
        test_results = {
            'http_test': None,
            'tcp_test': None,
            'dns_test': None
        }
        
        # DNS Test
        try:
            ip = socket.gethostbyname(host)
            test_results['dns_test'] = f'OK - Resolved to {ip}'
        except Exception as e:
            test_results['dns_test'] = f'FAILED - {str(e)}'
        
        # HTTP Test
        try:
            protocol = 'https' if TCP_PORT == 443 else 'http'
            context = ssl._create_unverified_context()
            req = urllib.request.Request(f'{protocol}://{host}', method='HEAD')
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                test_results['http_test'] = f'OK - Status {response.status}'
        except Exception as e:
            test_results['http_test'] = f'FAILED - {str(e)}'
        
        # TCP Test
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, TCP_PORT))
            sock.close()
            test_results['tcp_test'] = f'OK - Connected to port {TCP_PORT}'
        except Exception as e:
            test_results['tcp_test'] = f'FAILED - {str(e)}'
        
        debug_info['connectivity_tests'][host] = test_results
    
    # Show current data status
    with lock:
        debug_info['data_status'] = {
            host: {
                'data_points': len(data),
                'latest': data[-1] if data else None
            }
            for host, data in latency_data.items()
        }
    
    return jsonify(debug_info)


if __name__ == '__main__':
    # Get port from environment (Cloud Foundry sets this)
    port = int(os.getenv('PORT', '8080'))
    
    app.run(host='0.0.0.0', port=port, debug=False)
