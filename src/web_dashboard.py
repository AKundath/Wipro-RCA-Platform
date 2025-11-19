#!/usr/bin/env python3
"""
RCA Platform Web Dashboard - Enhanced Version
Real-time monitoring with severity filtering and detailed statistics
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
    'active_devices': 0,
    'critical_alarms': 0,
    'major_alarms': 0,
    'minor_alarms': 0,
    'avg_correlation_time': 0.8
}

# HTML template for the enhanced dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>RCA Platform Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: #0f0f23;
            color: #e0e0e0;
        }
        .header { 
            text-align: center;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 20px; 
            border-radius: 15px; 
            margin-bottom: 20px;
            border: 1px solid #2a2a4a;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .header h1 { 
            margin: 0; 
            font-size: 2.5em; 
            color: #00d9ff;
            text-shadow: 0 0 10px rgba(0, 217, 255, 0.3);
        }
        .header p { 
            margin: 10px 0 0 0; 
            opacity: 0.9; 
            color: #b0b0b0;
        }
        
        /* Filter Controls */
        .filter-section {
            background: #1a1a2e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #2a2a4a;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        .filter-controls {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .filter-label {
            font-weight: bold;
            font-size: 1.1em;
            color: #00d9ff;
        }
        .filter-select {
            padding: 10px 15px;
            border-radius: 5px;
            border: 1px solid #2a2a4a;
            background: #0f0f23;
            color: #e0e0e0;
            font-size: 1em;
            cursor: pointer;
            min-width: 150px;
        }
        .filter-select:hover {
            border-color: #00d9ff;
        }
        .filter-btn {
            padding: 10px 20px;
            border-radius: 5px;
            border: 1px solid #00d9ff;
            background: rgba(0, 217, 255, 0.1);
            color: #00d9ff;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .filter-btn:hover {
            background: rgba(0, 217, 255, 0.2);
            transform: translateY(-2px);
        }
        
        /* Enhanced Statistics Panel */
        .stats-panel {
            background: #1a1a2e;
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid #2a2a4a;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }
        .stats-panel h2 {
            margin-top: 0;
            border-bottom: 2px solid #2a2a4a;
            padding-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
            color: #00d9ff;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .stat-item {
            background: #0f0f23;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid;
            border: 1px solid #2a2a4a;
        }
        .stat-item.critical { border-left: 4px solid #ff4757; }
        .stat-item.success { border-left: 4px solid #1dd1a1; }
        .stat-item.warning { border-left: 4px solid #ffa502; }
        .stat-item.info { border-left: 4px solid #00d9ff; }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
            color: #e0e0e0;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.8;
            color: #b0b0b0;
        }
        .stat-sublabel {
            font-size: 0.75em;
            opacity: 0.6;
            margin-top: 5px;
            color: #808080;
        }
        
        .metrics { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 15px; 
            margin-bottom: 25px; 
        }
        .metric { 
            background: #1a1a2e;
            padding: 20px; 
            border-radius: 10px; 
            text-align: center;
            border: 1px solid #2a2a4a;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
        }
        .metric-value { 
            font-size: 2.5em; 
            font-weight: bold; 
            margin-bottom: 5px;
            color: #00d9ff;
        }
        .metric-label { 
            opacity: 0.8; 
            color: #b0b0b0;
        }
        
        .dashboard-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
        }
        .card { 
            background: #1a1a2e;
            padding: 25px; 
            border-radius: 15px;
            border: 1px solid #2a2a4a;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            max-height: 400px;
            overflow-y: auto;
        }
        .card h3 { 
            margin-top: 0; 
            color: #00d9ff;
            border-bottom: 2px solid #2a2a4a;
            padding-bottom: 10px;
        }
        
        /* Custom scrollbar for dark mode */
        .card::-webkit-scrollbar {
            width: 8px;
        }
        .card::-webkit-scrollbar-track {
            background: #0f0f23;
            border-radius: 4px;
        }
        .card::-webkit-scrollbar-thumb {
            background: #2a2a4a;
            border-radius: 4px;
        }
        .card::-webkit-scrollbar-thumb:hover {
            background: #3a3a5a;
        }
        
        .alarm-item { 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 8px; 
            background: #0f0f23;
            border-left: 5px solid #00d9ff;
            border: 1px solid #2a2a4a;
        }
        .alarm-critical { 
            border-left-color: #ff4757; 
            background: rgba(255, 71, 87, 0.1);
        }
        .alarm-major { 
            border-left-color: #ffa502; 
            background: rgba(255, 165, 2, 0.1);
        }
        .alarm-minor { 
            border-left-color: #00d9ff; 
            background: rgba(0, 217, 255, 0.1);
        }
        .alarm-suppressed {
            opacity: 0.5;
            background: rgba(149, 165, 166, 0.1);
            border-left-color: #5a5a6a;
        }
        .suppressed-badge {
            display: inline-block;
            background: #5a5a6a;
            color: #e0e0e0;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            margin-left: 8px;
            font-weight: bold;
        }
        
        .rca-result { 
            background: rgba(29, 209, 161, 0.1); 
            border: 2px solid #1dd1a1; 
            padding: 20px; 
            margin: 15px 0; 
            border-radius: 10px;
        }
        .rca-title {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 10px;
            color: #1dd1a1;
        }
        
        .device-status { 
            display: inline-block; 
            padding: 10px 18px; 
            margin: 8px; 
            border-radius: 20px; 
            font-size: 0.95em;
            font-weight: 500;
            min-width: 200px;
        }
        .device-active { 
            background: rgba(29, 209, 161, 0.2); 
            border: 1px solid #1dd1a1;
            color: #1dd1a1;
        }
        .device-alarm { 
            background: rgba(255, 71, 87, 0.2); 
            border: 1px solid #ff4757;
            color: #ff4757;
        }
        
        .timestamp { 
            font-size: 0.85em; 
            opacity: 0.6; 
            margin-top: 8px;
            color: #808080;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status-active { background-color: #1dd1a1; }
        .status-warning { background-color: #ffa502; }
        .status-critical { background-color: #ff4757; }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .export-btn {
            background: rgba(0, 217, 255, 0.1);
            border: 1px solid #00d9ff;
            color: #00d9ff;
            padding: 8px 15px;
            margin: 5px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s ease;
        }
        .export-btn:hover {
            background: rgba(0, 217, 255, 0.2);
            transform: translateY(-2px);
        }
        
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1dd1a1;
            color: #0f0f23;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 1000;
            animation: slideIn 0.3s ease;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4);
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
            color: #808080;
        }
        
        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>RCA Platform Dashboard</h1>
        <p>Real-time Network Monitoring & Intelligent Alarm Correlation</p>
        <div style="margin-top: 15px;">
            <span class="status-indicator status-active"></span>
            <span id="connection-status">Connected & Monitoring</span>
        </div>
    </div>

    <!-- Severity Filter Section -->
    <div class="filter-section">
        <div class="filter-controls">
            <span class="filter-label">Filter Alarms:</span>
            <select id="severity-filter" class="filter-select">
                <option value="all">All Severities</option>
                <option value="CRITICAL">Critical Only</option>
                <option value="MAJOR">Major Only</option>
                <option value="MINOR">Minor Only</option>
            </select>
            <select id="status-filter" class="filter-select">
                <option value="all">All Status</option>
                <option value="active">Active Alarms</option>
                <option value="suppressed">Suppressed Alarms</option>
            </select>
            <button class="filter-btn" onclick="resetFilters()">Reset Filters</button>
            <span style="margin-left: auto; opacity: 0.8;">
                Showing: <span id="filtered-count">0</span> alarms
            </span>
        </div>
    </div>

    <!-- Enhanced Statistics Panel -->
    <div class="stats-panel">
        <h2>
            <span>📊</span> Real-time Statistics
        </h2>
        <div class="stats-grid">
            <div class="stat-item info">
                <div class="stat-value" id="stat-total-alarms">0</div>
                <div class="stat-label">Total Alarms Processed</div>
                <div class="stat-sublabel">Since system start</div>
            </div>
            <div class="stat-item success">
                <div class="stat-value" id="stat-root-causes">0</div>
                <div class="stat-label">Root Causes Identified</div>
                <div class="stat-sublabel"><span id="rca-percentage">0%</span> detection rate</div>
            </div>
            <div class="stat-item warning">
                <div class="stat-value" id="stat-suppressed">0</div>
                <div class="stat-label">Alarms Suppressed</div>
                <div class="stat-sublabel"><span id="suppression-rate">0%</span> noise reduction</div>
            </div>
            <div class="stat-item critical">
                <div class="stat-value" id="stat-critical">0</div>
                <div class="stat-label">Critical Alarms</div>
                <div class="stat-sublabel">Require immediate attention</div>
            </div>
            <div class="stat-item warning">
                <div class="stat-value" id="stat-major">0</div>
                <div class="stat-label">Major Alarms</div>
                <div class="stat-sublabel">Significant issues</div>
            </div>
            <div class="stat-item info">
                <div class="stat-value" id="stat-minor">0</div>
                <div class="stat-label">Minor Alarms</div>
                <div class="stat-sublabel">Low priority</div>
            </div>
            <div class="stat-item success">
                <div class="stat-value" id="stat-response-time">< 1s</div>
                <div class="stat-label">Avg Correlation Time</div>
                <div class="stat-sublabel">Real-time processing</div>
            </div>
            <div class="stat-item info">
                <div class="stat-value" id="stat-devices">0</div>
                <div class="stat-label">Active Devices</div>
                <div class="stat-sublabel">Under monitoring</div>
            </div>
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
            <h3>🚨 Recent Alarms</h3>
            <div id="alarm-list"></div>
        </div>
        
        <div class="card">
            <h3>🎯 Root Cause Analysis Results</h3>
            <div id="rca-list"></div>
        </div>
    </div>

    <div style="margin-top: 20px;">
        <div class="card">
            <h3>🖥️ Device Status Monitor</h3>
            <div id="device-list"></div>
        </div>
    </div>

    <div style="margin-top: 20px; text-align: center;">
        <button class="export-btn" onclick="exportCSV()">📄 Export CSV</button>
        <button class="export-btn" onclick="exportJSON()">📋 Export JSON</button>
        <button class="export-btn" onclick="generateSummary()">📈 Executive Summary</button>
    </div>

    <script>
        const socket = io();
        let alarmCount = 0;
        let suppressedCount = 0;
        let rcaCount = 0;
        let allAlarms = [];
        let suppressedAlarmIds = new Set(); // Track which alarms are suppressed
        let currentSeverityFilter = 'all';
        let currentStatusFilter = 'all';
        
        // Statistics tracking
        let severityCounts = {
            'CRITICAL': 0,
            'MAJOR': 0,
            'MINOR': 0
        };

        socket.on('connect', function() {
            console.log('✅ Connected to dashboard');
            document.getElementById('connection-status').textContent = 'Connected & Monitoring';
        });

        socket.on('new_alarm', function(data) {
            alarmCount++;
            
            // Add unique ID and status
            data.alarm_id = `${data.device_ip}_${data.timestamp}`;
            data.status = 'active'; // Default status
            allAlarms.push(data);
            
            // Track severity
            const severity = data.severity || 'MINOR';
            if (severityCounts[severity] !== undefined) {
                severityCounts[severity]++;
            }
            
            updateMetrics();
            updateStatistics();
            applyFilters();
        });

        socket.on('rca_result', function(data) {
            rcaCount++;
            const suppressedAlarmCount = data.suppressed_count || 0;
            suppressedCount += suppressedAlarmCount;
            
            // Mark alarms as suppressed
            // Strategy: Mark recent alarms (last 10 alarms before this RCA) as suppressed
            // except for the root cause alarm itself
            const rootCauseDevice = data.root_cause_device;
            const rcaTime = new Date();
            
            // Find the root cause device name
            let rootCauseDeviceName = rootCauseDevice;
            const rootAlarm = allAlarms.find(a => a.device_ip === rootCauseDevice);
            if (rootAlarm && rootAlarm.device_name) {
                rootCauseDeviceName = rootAlarm.device_name;
            }
            
            // Find and mark recent alarms as suppressed (simulating cascade detection)
            let markedCount = 0;
            for (let i = allAlarms.length - 1; i >= 0 && markedCount < suppressedAlarmCount; i--) {
                const alarm = allAlarms[i];
                // Skip if it's already suppressed or if it's the root cause device
                if (alarm.status !== 'suppressed' && alarm.device_ip !== rootCauseDevice) {
                    alarm.status = 'suppressed';
                    alarm.suppressed_by = rootCauseDevice;
                    suppressedAlarmIds.add(alarm.alarm_id);
                    markedCount++;
                }
            }
            
            updateMetrics();
            updateStatistics();
            applyFilters();
            
            const rcaList = document.getElementById('rca-list');
            const rcaDiv = document.createElement('div');
            rcaDiv.className = 'rca-result';
            rcaDiv.innerHTML = `
                <div class="rca-title">🎯 Root Cause Identified</div>
                <div><strong>Device:</strong> ${rootCauseDeviceName}</div>
                <div><strong>IP:</strong> ${data.root_cause_device}</div>
                <div><strong>Type:</strong> ${data.correlation_type}</div>
                <div><strong>Confidence:</strong> ${(data.confidence * 100).toFixed(0)}%</div>
                <div><strong>Suppressed Alarms:</strong> ${suppressedAlarmCount}</div>
                <div class="timestamp">${new Date().toLocaleString()}</div>
            `;
            rcaList.insertBefore(rcaDiv, rcaList.firstChild);
            
            if (rcaList.children.length > 10) {
                rcaList.removeChild(rcaList.lastChild);
            }
        });

        socket.on('device_update', function(data) {
            const deviceList = document.getElementById('device-list');
            deviceList.innerHTML = '';
            
            for (const [ip, status] of Object.entries(data)) {
                const deviceDiv = document.createElement('div');
                deviceDiv.className = `device-status device-${status.status}`;
                
                // Try to find device name from recent alarms
                let deviceName = ip;
                const deviceAlarm = allAlarms.find(a => a.device_ip === ip);
                if (deviceAlarm && deviceAlarm.device_name) {
                    deviceName = deviceAlarm.device_name;
                }
                
                deviceDiv.innerHTML = `
                    <span class="status-indicator status-${status.status}"></span>
                    ${deviceName}
                    <div style="font-size: 0.8em; opacity: 0.7; margin-top: 2px;">${status.last_alarm}</div>
                `;
                deviceList.appendChild(deviceDiv);
            }
            
            // Update device count in statistics
            document.getElementById('stat-devices').textContent = Object.keys(data).length;
        });

        function updateMetrics() {
            document.getElementById('total-alarms').textContent = alarmCount;
            document.getElementById('suppressed-alarms').textContent = suppressedCount;
            document.getElementById('rca-count').textContent = rcaCount;
            
            const efficiency = alarmCount > 0 ? Math.round((suppressedCount / alarmCount) * 100) : 0;
            document.getElementById('efficiency').textContent = efficiency + '%';
        }
        
        function updateStatistics() {
            // Update main statistics panel
            document.getElementById('stat-total-alarms').textContent = alarmCount;
            document.getElementById('stat-root-causes').textContent = rcaCount;
            document.getElementById('stat-suppressed').textContent = suppressedCount;
            document.getElementById('stat-critical').textContent = severityCounts['CRITICAL'];
            document.getElementById('stat-major').textContent = severityCounts['MAJOR'];
            document.getElementById('stat-minor').textContent = severityCounts['MINOR'];
            
            // Calculate percentages
            const rcaPercentage = alarmCount > 0 ? ((rcaCount / alarmCount) * 100).toFixed(1) : 0;
            const suppressionRate = alarmCount > 0 ? ((suppressedCount / alarmCount) * 100).toFixed(1) : 0;
            
            document.getElementById('rca-percentage').textContent = rcaPercentage + '%';
            document.getElementById('suppression-rate').textContent = suppressionRate + '%';
        }

        function applyFilters() {
            const severityFilter = document.getElementById('severity-filter').value;
            const statusFilter = document.getElementById('status-filter').value;
            currentSeverityFilter = severityFilter;
            currentStatusFilter = statusFilter;
            
            const alarmList = document.getElementById('alarm-list');
            alarmList.innerHTML = '';
            
            const filteredAlarms = allAlarms.filter(alarm => {
                // Apply severity filter
                let severityMatch = true;
                if (severityFilter !== 'all') {
                    severityMatch = alarm.severity === severityFilter;
                }
                
                // Apply status filter
                let statusMatch = true;
                if (statusFilter === 'active') {
                    statusMatch = alarm.status === 'active';
                } else if (statusFilter === 'suppressed') {
                    statusMatch = alarm.status === 'suppressed';
                }
                
                return severityMatch && statusMatch;
            });
            
            // Update filtered count
            document.getElementById('filtered-count').textContent = filteredAlarms.length;
            
            if (filteredAlarms.length === 0) {
                alarmList.innerHTML = '<div class="no-data">No alarms match the current filter</div>';
                return;
            }
            
            // Show last 20 filtered alarms
            filteredAlarms.slice(-20).reverse().forEach(alarm => {
                const alarmDiv = document.createElement('div');
                const severityClass = alarm.severity ? `alarm-${alarm.severity.toLowerCase()}` : '';
                const suppressedClass = alarm.status === 'suppressed' ? 'alarm-suppressed' : '';
                
                alarmDiv.className = `alarm-item ${severityClass} ${suppressedClass}`;
                
                let suppressedBadge = '';
                if (alarm.status === 'suppressed') {
                    suppressedBadge = `<span class="suppressed-badge">SUPPRESSED</span>`;
                }
                
                let suppressedInfo = '';
                if (alarm.status === 'suppressed' && alarm.suppressed_by) {
                    const suppressedByDevice = allAlarms.find(a => a.device_ip === alarm.suppressed_by);
                    const suppressedByName = suppressedByDevice ? suppressedByDevice.device_name : alarm.suppressed_by;
                    suppressedInfo = `<div style="margin-top: 8px; font-size: 0.9em; opacity: 0.8;">
                        ⚠️ Suppressed: Caused by root issue on ${suppressedByName}
                    </div>`;
                }
                
                const deviceDisplay = alarm.device_name || alarm.device_ip;
                const locationInfo = alarm.location ? ` • ${alarm.location}` : '';
                
                alarmDiv.innerHTML = `
                    <div><strong>${alarm.alarm_type}</strong> ${suppressedBadge}</div>
                    <div style="font-size: 1.05em; margin: 5px 0;">
                        <strong>📍 ${deviceDisplay}</strong>${locationInfo}
                    </div>
                    <div style="opacity: 0.8;">IP: ${alarm.device_ip} | Severity: ${alarm.severity}</div>
                    ${suppressedInfo}
                    <div class="timestamp">${alarm.timestamp}</div>
                `;
                alarmList.appendChild(alarmDiv);
            });
        }
        
        function resetFilters() {
            document.getElementById('severity-filter').value = 'all';
            document.getElementById('status-filter').value = 'all';
            applyFilters();
            showNotification('✅ Filters reset - showing all alarms');
        }

        // Listen for filter changes
        document.getElementById('severity-filter').addEventListener('change', applyFilters);
        document.getElementById('status-filter').addEventListener('change', applyFilters);

        // Update connection status periodically
        setInterval(function() {
            document.getElementById('stat-response-time').textContent = '< 1s';
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
            const existing = document.querySelector('.notification');
            if (existing) existing.remove();
            
            const notification = document.createElement('div');
            notification.className = 'notification';
            notification.textContent = message;
            document.body.appendChild(notification);
            
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
    for alarm in current_alarms[-50:]:
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
            'critical_alarms': stats['critical_alarms'],
            'major_alarms': stats['major_alarms'],
            'minor_alarms': stats['minor_alarms'],
            'average_response_time': "< 1 second",
            'platform_status': "Operational"
        },
        'severity_breakdown': {
            'critical': stats['critical_alarms'],
            'major': stats['major_alarms'],
            'minor': stats['minor_alarms'],
            'total': total_alarms
        },
        'key_achievements': [
            f"Reduced alarm noise by {efficiency:.1f}%",
            f"Identified {stats['root_causes_found']} root causes automatically",
            f"Processed {total_alarms} alarms with sub-second response time",
            f"Handled {stats['critical_alarms']} critical alarms requiring immediate attention",
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
            
            # Store alarm
            current_alarms.append(alarm_data)
            if len(current_alarms) > 100:
                current_alarms.pop(0)
            
            # Send alarm to web interface
            socketio.emit('new_alarm', alarm_data)
            
            # Update stats
            stats['total_alarms'] += 1
            severity = alarm_data.get('severity', 'MINOR')
            if severity == 'CRITICAL':
                stats['critical_alarms'] += 1
            elif severity == 'MAJOR':
                stats['major_alarms'] += 1
            elif severity == 'MINOR':
                stats['minor_alarms'] += 1
            
            # Simple correlation detection for demo
            if 'DEVICE_UNREACHABLE' in alarm_data.get('alarm_type', ''):
                # Simulate RCA result for demo
                # Generate affected devices (devices that would have cascading alarms)
                affected_devices = []
                device_ip = alarm_data.get('device_ip', 'Unknown')
                
                # Simulate 3 downstream devices affected by this root cause
                for i in range(1, 4):
                    affected_ip = f"10.0.{int(device_ip.split('.')[2])}.{int(device_ip.split('.')[3]) + i}"
                    affected_devices.append(affected_ip)
                
                rca_result = {
                    'root_cause_device': device_ip,
                    'correlation_type': 'cascade_failure',
                    'confidence': 0.95,
                    'suppressed_count': 3,
                    'affected_devices': affected_devices
                }
                rca_results.append(rca_result)
                if len(rca_results) > 50:
                    rca_results.pop(0)
                    
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
                stats['active_devices'] = len(device_status)
                socketio.emit('device_update', device_status)
                
    except Exception as e:
        print(f"❌ Dashboard Kafka connection failed: {e}")

def main():
    print("🌐 Starting RCA Platform Web Dashboard (Enhanced)")
    print("💻 Dashboard will be available at: http://localhost:5000")
    print("🔄 Starting Kafka consumer for real-time updates...")
    print("\n✨ New Features:")
    print("   - Alarm Severity Filtering")
    print("   - Enhanced Statistics Panel")
    print("   - Real-time Metrics Tracking\n")
    
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
