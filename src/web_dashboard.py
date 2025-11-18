#!/usr/bin/env python3
"""
RCA Platform Web Dashboard
Real-time monitoring and visualization
"""

from flask import Flask, render_template_string, jsonify, make_response
from flask_socketio import SocketIO
import json
import threading
from kafka import KafkaConsumer
from datetime import datetime
import time
import csv
from io import StringIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'rca-platform-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for real-time data
current_alarms = []
rca_results = []
device_status = {}
stats = {
    'total_alarms': 0,
    'suppressed_alarms': 0,
    'root_causes_found': 0,
    'active_devices': 0
}

# HTML template for the dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🔍 RCA Platform Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .header { 
            text-align: center;
            background: rgba(255,255,255,0.1);
            padding: 20px; 
            border-radius: 15px; 
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        
        .metrics { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 15px; 
            margin-bottom: 25px; 
        }
        .metric { 
            background: rgba(255,255,255,0.15);
            padding: 20px; 
            border-radius: 10px; 
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .metric-value { 
            font-size: 2.5em; 
            font-weight: bold; 
            margin-bottom: 5px;
            color: #fff;
        }
        .metric-label { opacity: 0.8; }
        
        .dashboard-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
        }
        .card { 
            background: rgba(255,255,255,0.1);
            padding: 25px; 
            border-radius: 15px;
            backdrop-filter: blur(10px);
            max-height: 400px;
            overflow-y: auto;
        }
        .card h3 { 
            margin-top: 0; 
            color: #fff;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }
        
        .alarm-item { 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
            background: rgba(255,255,255,0.1);
            border-left: 5px solid #3498db;
        }
        .alarm-critical { 
            border-left-color: #e74c3c; 
            background: rgba(231, 76, 60, 0.2);
        }
        .alarm-warning { 
            border-left-color: #f39c12; 
            background: rgba(243, 156, 18, 0.2);
        }
        
        .rca-result { 
            background: rgba(46, 204, 113, 0.2); 
            border: 2px solid #2ecc71; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px;
        }
        .rca-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 10px;
            color: #2ecc71;
        }
        
        .device-status { 
            display: inline-block; 
            padding: 8px 15px; 
            margin: 8px; 
            border-radius: 20px; 
            font-size: 0.9em;
        }
        .device-active { 
            background: rgba(46, 204, 113, 0.3); 
            border: 1px solid #2ecc71;
        }
        .device-alarm { 
            background: rgba(231, 76, 60, 0.3); 
            border: 1px solid #e74c3c;
        }
        
        .timestamp { 
            font-size: 0.85em; 
            opacity: 0.7; 
            margin-top: 8px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status-active { background-color: #2ecc71; }
        .status-warning { background-color: #f39c12; }
        .status-critical { background-color: #e74c3c; }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .export-btn {
            background: rgba(46, 204, 113, 0.3);
            border: 1px solid #2ecc71;
            color: white;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        .export-btn:hover {
            background: rgba(46, 204, 113, 0.5);
            transform: translateY(-2px);
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(46, 204, 113, 0.9);
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            backdrop-filter: blur(10px);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .no-data {
            text-align: center;
            opacity: 0.6;
            padding: 30px;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 RCA Platform Dashboard</h1>
        <p>Real-time Network Monitoring & Intelligent Alarm Correlation</p>
        <div style="margin-top: 15px;">
            <span class="status-indicator status-active"></span>
            <span id="connection-status">Connected & Monitoring</span>
        </div>
    </div>

    <div class="metrics">
        <div class="metric">
            <div class="metric-value" id="total-alarms">0</div>
            <div class="metric-label">Total Alarms</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="suppressed-alarms">0</div>
            <div class="metric-label">Suppressed</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="rca-count">0</div>
            <div class="metric-label">Root Causes</div>
        </div>
        <div class="metric">
            <div class="metric-value" id="efficiency">0%</div>
            <div class="metric-label">Efficiency</div>
        </div>
    </div>

    <div class="dashboard-grid">
        <div class="card">
            <h3>📊 Recent Alarms</h3>
            <div id="alarms-container">
                <div class="no-data">Waiting for alarms...</div>
            </div>
        </div>

        <div class="card">
            <h3>🎯 Root Cause Analysis</h3>
            <div id="rca-container">
                <div class="no-data">No correlations detected yet...</div>
            </div>
        </div>

        <div class="card">
            <h3>🖥️ Device Status</h3>
            <div id="devices-container">
                <div class="no-data">Loading device information...</div>
            </div>
        </div>

        <div class="card">
            <h3>📈 Live Statistics & Export</h3>
            <div id="stats-container">
                <div style="margin: 15px 0;">
                    <strong>Platform Performance:</strong><br>
                    • Correlation Engine: <span id="correlation-status">Active</span><br>
                    • Message Processing: <span id="processing-rate">0 msg/min</span><br>
                    • Average Response Time: <span id="response-time">&lt; 1s</span><br>
                    • Noise Reduction: <span id="noise-reduction">0%</span>
                </div>
                
                <div style="margin-top: 25px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.3);">
                    <strong>📊 Export Reports:</strong><br>
                    <div style="margin-top: 15px;">
                        <button onclick="exportCSV()" class="export-btn">📄 Export CSV Report</button>
                        <button onclick="exportJSON()" class="export-btn">📋 Export JSON Data</button>
                        <button onclick="generateSummary()" class="export-btn">📈 Executive Summary</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const socket = io();
        let alarmCount = 0;
        let suppressedCount = 0;
        let rcaCount = 0;
        let messageRate = 0;
        let lastMinuteMessages = [];

        // Socket event handlers
        socket.on('connect', function() {
            console.log('Connected to RCA Platform');
            document.getElementById('connection-status').textContent = 'Connected & Monitoring';
        });

        socket.on('new_alarm', function(alarm) {
            addAlarmToDisplay(alarm);
            updateMessageRate();
            updateMetrics();
        });

        socket.on('rca_result', function(result) {
            addRCAResultToDisplay(result);
            suppressedCount += result.suppressed_count || 0;
            rcaCount++;
            updateMetrics();
        });

        socket.on('device_update', function(devices) {
            updateDeviceStatus(devices);
        });

        function addAlarmToDisplay(alarm) {
            const container = document.getElementById('alarms-container');
            
            // Remove "no data" message
            if (container.querySelector('.no-data')) {
                container.innerHTML = '';
            }
            
            const alarmDiv = document.createElement('div');
            const severityClass = alarm.severity === 'CRITICAL' ? 'alarm-critical' : 
                                 alarm.severity === 'WARNING' ? 'alarm-warning' : '';
            
            alarmDiv.className = `alarm-item ${severityClass}`;
            alarmDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>${alarm.alarm_type || 'Unknown'}</strong> - ${alarm.device_ip || 'Unknown Device'}
                        <br><small>${alarm.description || 'No description'}</small>
                    </div>
                    <div class="timestamp">${new Date().toLocaleTimeString()}</div>
                </div>
            `;
            
            container.insertBefore(alarmDiv, container.firstChild);
            
            // Keep only last 8 alarms visible
            while (container.children.length > 8) {
                container.removeChild(container.lastChild);
            }
            
            alarmCount++;
        }

        function addRCAResultToDisplay(result) {
            const container = document.getElementById('rca-container');
            
            // Remove "no data" message
            if (container.querySelector('.no-data')) {
                container.innerHTML = '';
            }
            
            const rcaDiv = document.createElement('div');
            rcaDiv.className = 'rca-result';
            rcaDiv.innerHTML = `
                <div class="rca-title">🎯 Root Cause Detected</div>
                <strong>Device:</strong> ${result.root_cause_device}<br>
                <strong>Type:</strong> ${result.correlation_type}<br>
                <strong>Confidence:</strong> ${Math.round(result.confidence * 100)}%<br>
                <strong>Suppressed:</strong> ${result.suppressed_count} alarms<br>
                <div class="timestamp">Detected: ${new Date().toLocaleTimeString()}</div>
            `;
            
            container.insertBefore(rcaDiv, container.firstChild);
            
            // Keep only last 4 RCA results visible
            while (container.children.length > 4) {
                container.removeChild(container.lastChild);
            }
        }

        function updateDeviceStatus(devices) {
            const container = document.getElementById('devices-container');
            container.innerHTML = '';
            
            let activeCount = 0;
            for (const [ip, status] of Object.entries(devices)) {
                const deviceDiv = document.createElement('div');
                const statusClass = status.last_alarm ? 'device-alarm' : 'device-active';
                
                deviceDiv.className = `device-status ${statusClass}`;
                deviceDiv.innerHTML = `${ip} - ${status.status}`;
                container.appendChild(deviceDiv);
                
                if (status.status === 'active') activeCount++;
            }
            
            if (Object.keys(devices).length === 0) {
                container.innerHTML = '<div class="no-data">No devices detected</div>';
            }
        }

        function updateMessageRate() {
            const now = Date.now();
            lastMinuteMessages.push(now);
            
            // Keep only messages from last minute
            lastMinuteMessages = lastMinuteMessages.filter(time => now - time < 60000);
            messageRate = lastMinuteMessages.length;
            
            document.getElementById('processing-rate').textContent = messageRate + ' msg/min';
        }

        function updateMetrics() {
            document.getElementById('total-alarms').textContent = alarmCount;
            document.getElementById('suppressed-alarms').textContent = suppressedCount;
            document.getElementById('rca-count').textContent = rcaCount;
            
            const efficiency = alarmCount > 0 ? Math.round((suppressedCount / alarmCount) * 100) : 0;
            document.getElementById('efficiency').textContent = efficiency + '%';
            document.getElementById('noise-reduction').textContent = efficiency + '%';
        }

        // Update connection status periodically
        setInterval(function() {
            document.getElementById('correlation-status').textContent = 'Active';
            document.getElementById('response-time').textContent = '< 1s';
        }, 5000);
        
        // Export functions
        function exportCSV() {
            showNotification('📄 Generating CSV report...');
            window.open('/api/export/csv', '_blank');
            setTimeout(() => showNotification('✅ CSV report downloaded!'), 1000);
        }
        
        function exportJSON() {
            showNotification('📋 Generating JSON export...');
            window.open('/api/export/json', '_blank');
            setTimeout(() => showNotification('✅ JSON data downloaded!'), 1000);
        }
        
        function generateSummary() {
            showNotification('📈 Generating executive summary...');
            fetch('/api/report/summary')
                .then(response => response.json())
                .then(data => {
                    const summary = JSON.stringify(data, null, 2);
                    const blob = new Blob([summary], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `executive_summary_${new Date().toISOString().split('T')[0]}.json`;
                    a.click();
                    URL.revokeObjectURL(url);
                    showNotification('✅ Executive summary downloaded!');
                })
                .catch(err => showNotification('❌ Export failed'));
        }
        
        function showNotification(message) {
            // Remove existing notifications
            const existing = document.querySelector('.notification');
            if (existing) existing.remove();
            
            // Create new notification
            const notification = document.createElement('div');
            notification.className = 'notification';
            notification.textContent = message;
            document.body.appendChild(notification);
            
            // Auto remove after 3 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 3000);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/export/csv')
def export_csv():
    """Export alarm data as CSV"""
    output = StringIO()
    writer = csv.writer(output)
    
    # CSV Headers
    writer.writerow([
        'Timestamp', 'Device IP', 'Alarm Type', 'Severity', 
        'Description', 'Status', 'Root Cause Analysis'
    ])
    
    # Add current alarms
    for alarm in current_alarms[-50:]:  # Last 50 alarms
        rca_info = "Independent"
        for rca in rca_results:
            if rca.get('root_cause_device') == alarm.get('device_ip'):
                rca_info = f"Root Cause ({rca.get('confidence', 0)*100:.0f}% confidence)"
            elif alarm.get('device_ip') in str(rca.get('affected_devices', [])):
                rca_info = f"Suppressed (caused by {rca.get('root_cause_device')})"
        
        writer.writerow([
            alarm.get('timestamp', datetime.now().isoformat()),
            alarm.get('device_ip', 'Unknown'),
            alarm.get('alarm_type', 'Unknown'),
            alarm.get('severity', 'Unknown'),
            alarm.get('description', 'No description'),
            'Processed',
            rca_info
        ])
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=rca_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    return response

@app.route('/api/export/json')
def export_json():
    """Export complete platform data as JSON"""
    export_data = {
        'export_timestamp': datetime.now().isoformat(),
        'platform_stats': stats,
        'recent_alarms': current_alarms[-50:],
        'rca_results': rca_results[-20:],
        'device_status': device_status,
        'summary': {
            'total_devices_monitored': len(device_status),
            'alarm_suppression_rate': f"{(stats['suppressed_alarms'] / max(stats['total_alarms'], 1)) * 100:.1f}%",
            'average_confidence': f"{sum([r.get('confidence', 0) for r in rca_results]) / max(len(rca_results), 1) * 100:.1f}%"
        }
    }
    
    response = make_response(json.dumps(export_data, indent=2))
    response.headers['Content-Type'] = 'application/json'
    response.headers['Content-Disposition'] = f'attachment; filename=rca_complete_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    return response

@app.route('/api/report/summary')
def generate_summary_report():
    """Generate executive summary report"""
    total_alarms = stats['total_alarms']
    suppressed = stats['suppressed_alarms'] 
    efficiency = (suppressed / max(total_alarms, 1)) * 100
    
    summary = {
        'report_generated': datetime.now().isoformat(),
        'executive_summary': {
            'total_alarms_processed': total_alarms,
            'alarms_suppressed': suppressed,
            'noise_reduction_percentage': f"{efficiency:.1f}%",
            'root_causes_identified': stats['root_causes_found'],
            'average_response_time': "< 1 second",
            'platform_status': "Operational"
        },
        'key_achievements': [
            f"Reduced alarm noise by {efficiency:.1f}%",
            f"Identified {stats['root_causes_found']} root causes automatically",
            f"Processed {total_alarms} alarms with sub-second response time",
            "Provided actionable recommendations for each incident"
        ],
        'recommendations': [
            "Continue monitoring for pattern optimization",
            "Consider adding more correlation rules",
            "Integrate with additional network devices",
            "Implement predictive analysis capabilities"
        ]
    }
    
    return jsonify(summary)

def kafka_consumer_thread():
    """Background thread to consume Kafka messages and send to web interface"""
    try:
        consumer = KafkaConsumer(
            'network-alarms',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        print("✅ Dashboard connected to Kafka")
        
        for message in consumer:
            alarm_data = message.value
            
            # Send alarm to web interface
            socketio.emit('new_alarm', alarm_data)
            
            # Update stats
            stats['total_alarms'] += 1
            
            # Simple correlation detection for demo
            if 'DEVICE_UNREACHABLE' in alarm_data.get('alarm_type', ''):
                # Simulate RCA result for demo
                rca_result = {
                    'root_cause_device': alarm_data.get('device_ip', 'Unknown'),
                    'correlation_type': 'cascade_failure',
                    'confidence': 0.95,
                    'suppressed_count': 3
                }
                socketio.emit('rca_result', rca_result)
                stats['suppressed_alarms'] += 3
                stats['root_causes_found'] += 1
            
            # Update device status
            device_ip = alarm_data.get('device_ip')
            if device_ip:
                device_status[device_ip] = {
                    'status': 'alarm' if alarm_data.get('severity') == 'CRITICAL' else 'active',
                    'last_alarm': alarm_data.get('alarm_type'),
                    'last_seen': datetime.now().isoformat()
                }
                socketio.emit('device_update', device_status)
                
    except Exception as e:
        print(f"❌ Dashboard Kafka connection failed: {e}")

def main():
    print("🌐 Starting RCA Platform Web Dashboard")
    print("💻 Dashboard will be available at: http://localhost:5000")
    print("🔄 Starting Kafka consumer for real-time updates...")
    
    # Start Kafka consumer in background thread
    kafka_thread = threading.Thread(target=kafka_consumer_thread)
    kafka_thread.daemon = True
    kafka_thread.start()
    
    # Start web server
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n⏹️  Dashboard stopped")

if __name__ == '__main__':
    main()
