#!/usr/bin/env python3
"""
Enhanced Alarm Generator for RCA Project
Generates realistic network alarms with proper device naming
"""

import json
import time
import random
from datetime import datetime

# Try to import Kafka, if not available we'll just print alarms
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
    print("✅ Kafka library found")
except ImportError:
    print("❌ Kafka library not found. Install with: pip install kafka-python")
    print("📝 Running in simulation mode (will just print alarms)")
    KAFKA_AVAILABLE = False

# Enhanced device inventory with realistic names
DEVICE_INVENTORY = {
    "10.0.1.1": {"name": "Router-Core-01", "type": "router", "location": "Data Center"},
    "10.0.1.2": {"name": "Router-Edge-02", "type": "router", "location": "Branch Office"},
    "10.0.2.10": {"name": "Switch-Access-10", "type": "switch", "location": "Floor 3"},
    "10.0.2.11": {"name": "Switch-Distribution-11", "type": "switch", "location": "Data Center"},
    "10.0.3.20": {"name": "Server-Web-01", "type": "server", "location": "Data Center"},
    "10.0.3.21": {"name": "Server-DB-Primary", "type": "server", "location": "Data Center"},
    "10.0.3.22": {"name": "Server-DB-Backup", "type": "server", "location": "Data Center"},
    "10.0.4.30": {"name": "PC-Finance-05", "type": "workstation", "location": "Finance Dept"},
    "10.0.4.31": {"name": "PC-HR-12", "type": "workstation", "location": "HR Dept"},
    "10.0.5.40": {"name": "Firewall-Main", "type": "firewall", "location": "Data Center"},
}

def get_device_info(device_ip):
    """Get device information from inventory"""
    return DEVICE_INVENTORY.get(device_ip, {
        "name": f"Unknown-Device-{device_ip.split('.')[-1]}",
        "type": "unknown",
        "location": "Unknown"
    })

def generate_fake_alarm():
    """Generate a realistic fake network alarm"""
    
    # Pick random device
    device_ip = random.choice(list(DEVICE_INVENTORY.keys()))
    device_info = get_device_info(device_ip)
    
    # Different types of network problems
    alarm_types = [
        "HIGH_CPU_USAGE",
        "HIGH_MEMORY_USAGE", 
        "INTERFACE_DOWN",
        "DEVICE_UNREACHABLE",
        "HIGH_TRAFFIC",
        "SERVICE_DOWN",
        "DISK_SPACE_LOW",
        "LINK_FLAPPING"
    ]
    
    # Severity levels with realistic distribution
    severities = ["CRITICAL", "MAJOR", "MINOR"]
    severity_weights = [0.2, 0.3, 0.5]  # 20% Critical, 30% Major, 50% Minor
    
    # Pick random problem and severity
    alarm_type = random.choice(alarm_types)
    severity = random.choices(severities, weights=severity_weights)[0]
    
    # Create alarm data
    alarm = {
        "device_id": f"{device_ip}-{alarm_type.lower()}",
        "device_ip": device_ip,
        "device_name": device_info['name'],
        "device_type": device_info['type'],
        "location": device_info['location'],
        "alarm_type": alarm_type,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "description": f"{alarm_type.replace('_', ' ').title()} detected on {device_info['name']}",
        "source": "SNMP_Trap"
    }
    
    return alarm

def simulate_cascade_failure():
    """Simulate a realistic cascade failure scenario"""
    print("\n" + "="*70)
    print("🔥 CASCADE FAILURE SCENARIO - Root Cause Detection Demo")
    print("="*70)
    
    # Scenario: Core router fails, causing cascading issues
    root_device_ip = "10.0.1.1"
    root_device = get_device_info(root_device_ip)
    
    # Root cause alarm
    root_alarm = {
        "device_id": f"{root_device_ip}-device_unreachable",
        "device_ip": root_device_ip,
        "device_name": root_device['name'],
        "device_type": root_device['type'],
        "location": root_device['location'],
        "alarm_type": "DEVICE_UNREACHABLE",
        "severity": "CRITICAL",
        "timestamp": datetime.now().isoformat(),
        "description": f"{root_device['name']} is unreachable - Network connectivity lost",
        "source": "ICMP_Monitor"
    }
    
    # Cascading alarms from dependent devices
    cascading_alarms = [
        {
            "device_ip": "10.0.2.10",
            "alarm_type": "INTERFACE_DOWN",
            "severity": "MAJOR"
        },
        {
            "device_ip": "10.0.3.20",
            "alarm_type": "SERVICE_DOWN",
            "severity": "MAJOR"
        },
        {
            "device_ip": "10.0.3.21",
            "alarm_type": "HIGH_CPU_USAGE",
            "severity": "MAJOR"
        }
    ]
    
    return root_alarm, cascading_alarms

def main():
    print("🚀 Enhanced Alarm Generator for RCA Platform")
    print("=" * 70)
    print("💡 Generating realistic network alarms with proper device naming")
    print("🎯 This demonstrates intelligent Root Cause Analysis")
    print("⏹️  Press Ctrl+C to stop\n")
    
    # Display device inventory
    print("📋 Device Inventory:")
    for ip, info in DEVICE_INVENTORY.items():
        print(f"   • {ip:15} - {info['name']:25} [{info['type']:12}] ({info['location']})")
    print()
    
    if KAFKA_AVAILABLE:
        try:
            # Connect to Kafka
            producer = KafkaProducer(
                bootstrap_servers=['localhost:9092'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("✅ Connected to Kafka")
            print("📤 Sending alarms to 'network-alarms' topic\n")
            mode = "kafka"
        except Exception as e:
            print(f"❌ Failed to connect to Kafka: {e}")
            print("📝 Falling back to simulation mode\n")
            mode = "simulation"
    else:
        mode = "simulation"
    
    alarm_count = 0
    cascade_triggered = False
    
    try:
        while True:
            # Every 12 alarms, trigger a cascade failure for demonstration
            if alarm_count > 0 and alarm_count % 12 == 0 and not cascade_triggered:
                cascade_triggered = True
                
                # Generate cascade failure scenario
                root_alarm, cascading_alarms = simulate_cascade_failure()
                
                # Send root cause alarm
                if mode == "kafka":
                    producer.send('network-alarms', root_alarm)
                    
                print(f"🚨 ROOT CAUSE: {root_alarm['device_name']} - {root_alarm['alarm_type']}")
                print(f"   Device: {root_alarm['device_ip']} ({root_alarm['location']})")
                print(f"   Severity: {root_alarm['severity']}")
                time.sleep(2)
                
                # Send cascading alarms
                print("\n📊 Cascading Effects:")
                for i, cascade_data in enumerate(cascading_alarms, 1):
                    device_info = get_device_info(cascade_data['device_ip'])
                    
                    cascade_alarm = {
                        "device_id": f"{cascade_data['device_ip']}-{cascade_data['alarm_type'].lower()}",
                        "device_ip": cascade_data['device_ip'],
                        "device_name": device_info['name'],
                        "device_type": device_info['type'],
                        "location": device_info['location'],
                        "alarm_type": cascade_data['alarm_type'],
                        "severity": cascade_data['severity'],
                        "timestamp": datetime.now().isoformat(),
                        "description": f"{cascade_data['alarm_type'].replace('_', ' ').title()} - Impact from {root_alarm['device_name']} failure",
                        "source": "Correlation_Engine"
                    }
                    
                    if mode == "kafka":
                        producer.send('network-alarms', cascade_alarm)
                    
                    print(f"   {i}. {cascade_alarm['device_name']} - {cascade_alarm['alarm_type']}")
                    print(f"      Impact: {cascade_alarm['description']}")
                    time.sleep(1)
                
                print("\n💡 RCA Engine should identify these as suppressed alarms!")
                print("   ➜ Root Cause: " + root_alarm['device_name'])
                print("   ➜ Suppressed: 3 cascading alarms")
                print("="*70 + "\n")
                cascade_triggered = False
                
            else:
                # Generate normal random alarm
                alarm = generate_fake_alarm()
                
                if mode == "kafka":
                    producer.send('network-alarms', alarm)
                    print(f"📤 {alarm['device_name']:25} | {alarm['alarm_type']:20} | {alarm['severity']:8} | {alarm['location']}")
                else:
                    print(f"🚨 {alarm['device_name']:25} | {alarm['alarm_type']:20} | {alarm['severity']:8}")
            
            alarm_count += 1
            time.sleep(3)  # Wait 3 seconds between alarms
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped. Generated {alarm_count} alarms total.")
        if mode == "kafka":
            producer.close()
        print("✅ Alarm generator shutdown complete")

if __name__ == "__main__":
    main()
