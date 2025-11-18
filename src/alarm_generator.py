#!/usr/bin/env python3
"""
Simple Alarm Generator for RCA Project
This creates fake network alarms for testing
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

def generate_fake_alarm():
    """Generate a realistic fake network alarm"""
    
    # Simulate different network devices
    devices = [
        {"ip": "192.168.1.1", "name": "Main Router", "type": "router"},
        {"ip": "192.168.1.10", "name": "Core Switch", "type": "switch"},
        {"ip": "192.168.1.20", "name": "Web Server", "type": "server"},
        {"ip": "192.168.1.30", "name": "DB Server", "type": "server"},
    ]
    
    # Different types of network problems
    alarm_types = [
        "HIGH_CPU_USAGE",
        "HIGH_MEMORY_USAGE", 
        "INTERFACE_DOWN",
        "DEVICE_UNREACHABLE",
        "HIGH_TRAFFIC",
        "SERVICE_DOWN"
    ]
    
    # Severity levels
    severities = ["WARNING", "CRITICAL"]
    
    # Pick random device and problem
    device = random.choice(devices)
    alarm_type = random.choice(alarm_types)
    severity = random.choice(severities)
    
    # Create alarm data
    alarm = {
        "device_id": f"{device['ip']}-{alarm_type.lower()}",
        "device_ip": device['ip'],
        "device_name": device['name'],
        "device_type": device['type'],
        "alarm_type": alarm_type,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "description": f"{alarm_type.replace('_', ' ').title()} detected on {device['name']}",
        "source": "simulator"
    }
    
    return alarm

def simulate_cascade_failure():
    """Simulate a cascade failure where one device causes multiple alarms"""
    print("\n🔥 Simulating CASCADE FAILURE...")
    
    # Main router fails first
    root_alarm = {
        "device_id": "192.168.1.1-device_unreachable",
        "device_ip": "192.168.1.1",
        "device_name": "Main Router", 
        "device_type": "router",
        "alarm_type": "DEVICE_UNREACHABLE",
        "severity": "CRITICAL",
        "timestamp": datetime.now().isoformat(),
        "description": "Main Router is unreachable - potential root cause",
        "source": "simulator"
    }
    
    return root_alarm

def main():
    print("🚀 Starting Simple Alarm Generator")
    print("💡 This will generate fake network alarms for testing")
    print("⏹️  Press Ctrl+C to stop\n")
    
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
            # Every 10 alarms, trigger a cascade failure for demonstration
            if alarm_count > 0 and alarm_count % 10 == 0 and not cascade_triggered:
                cascade_triggered = True
                
                # Send root cause alarm
                root_alarm = simulate_cascade_failure()
                
                if mode == "kafka":
                    producer.send('network-alarms', root_alarm)
                    
                print(f"🚨 ROOT CAUSE: {root_alarm['alarm_type']} from {root_alarm['device_ip']}")
                time.sleep(2)
                
                # Send 3 related alarms (caused by the root cause)
                related_devices = ["192.168.1.10", "192.168.1.20", "192.168.1.30"]
                related_alarms = ["INTERFACE_DOWN", "SERVICE_DOWN", "HIGH_CPU_USAGE"]
                
                for i, (device_ip, alarm_type) in enumerate(zip(related_devices, related_alarms)):
                    related_alarm = {
                        "device_id": f"{device_ip}-{alarm_type.lower()}",
                        "device_ip": device_ip,
                        "alarm_type": alarm_type,
                        "severity": "WARNING",
                        "timestamp": datetime.now().isoformat(),
                        "description": f"Impact from router failure: {alarm_type}",
                        "source": "simulator"
                    }
                    
                    if mode == "kafka":
                        producer.send('network-alarms', related_alarm)
                    
                    print(f"📢 RELATED: {related_alarm['alarm_type']} from {related_alarm['device_ip']}")
                    time.sleep(1)
                
                print("💡 This should trigger ROOT CAUSE ANALYSIS!\n")
                cascade_triggered = False
                
            else:
                # Generate normal random alarm
                alarm = generate_fake_alarm()
                
                if mode == "kafka":
                    producer.send('network-alarms', alarm)
                    print(f"📤 Sent: {alarm['alarm_type']} from {alarm['device_ip']} ({alarm['severity']})")
                else:
                    print(f"🚨 Simulated: {alarm['alarm_type']} from {alarm['device_ip']} ({alarm['severity']})")
            
            alarm_count += 1
            time.sleep(3)  # Wait 3 seconds between alarms
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped. Generated {alarm_count} alarms total.")
        if mode == "kafka":
            producer.close()

if __name__ == "__main__":
    main()
