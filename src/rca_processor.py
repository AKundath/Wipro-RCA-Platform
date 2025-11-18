#!/usr/bin/env python3
"""
Simple RCA Processor for RCA Project
This reads alarms and finds simple correlations
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict

# Try to import Kafka
try:
    from kafka import KafkaConsumer
    KAFKA_AVAILABLE = True
    print("✅ Kafka library found")
except ImportError:
    print("❌ Kafka library not found. Install with: pip install kafka-python")
    KAFKA_AVAILABLE = False

class SimpleRCA:
    def __init__(self):
        self.recent_alarms = []
        self.time_window = 30  # 30 seconds correlation window
        self.processed_count = 0
        self.suppressed_count = 0
        self.root_causes_found = 0
        
        print("🧠 Simple RCA Engine initialized")
        print(f"⏱️  Correlation time window: {self.time_window} seconds")
        
    def add_alarm(self, alarm_data):
        """Add new alarm and check for correlations"""
        
        # Convert timestamp string back to datetime if needed
        if isinstance(alarm_data['timestamp'], str):
            alarm_data['timestamp'] = datetime.fromisoformat(alarm_data['timestamp'])
        
        self.recent_alarms.append(alarm_data)
        self.processed_count += 1
        
        # Keep only recent alarms (last 5 minutes)
        cutoff_time = datetime.now() - timedelta(minutes=5)
        self.recent_alarms = [a for a in self.recent_alarms 
                             if a['timestamp'] > cutoff_time]
        
        print(f"\n📨 New alarm #{self.processed_count}:")
        print(f"   🖥️  Device: {alarm_data['device_ip']}")
        print(f"   ⚠️  Type: {alarm_data['alarm_type']}")
        print(f"   🔥 Severity: {alarm_data['severity']}")
        
        # Check for correlations
        correlation = self.find_correlations(alarm_data)
        
        if correlation:
            self.handle_correlation(correlation)
            self.root_causes_found += 1
        else:
            print(f"   ✅ Independent alarm (no correlation found)")
            
        self.print_stats()
        
    def find_correlations(self, new_alarm):
        """Find correlations using simple rules"""
        current_time = new_alarm['timestamp']
        time_threshold = current_time - timedelta(seconds=self.time_window)
        
        # Get recent alarms within time window
        recent = [a for a in self.recent_alarms if a['timestamp'] >= time_threshold]
        
        # Rule 1: Multiple alarms from same device (device-level correlation)
        same_device_alarms = [a for a in recent 
                             if a['device_ip'] == new_alarm['device_ip'] 
                             and a != new_alarm]
        
        if same_device_alarms:
            return {
                'type': 'device_correlation',
                'root_cause_device': new_alarm['device_ip'],
                'root_alarm': new_alarm,
                'correlated_alarms': same_device_alarms,
                'confidence': 0.9,
                'reason': f"Multiple alarms from same device within {self.time_window}s"
            }
        
        # Rule 2: Known cascade patterns
        cascade_correlation = self.check_cascade_patterns(new_alarm, recent)
        if cascade_correlation:
            return cascade_correlation
            
        # Rule 3: Critical device impact (router affects others)
        impact_correlation = self.check_device_impact(new_alarm, recent)
        if impact_correlation:
            return impact_correlation
        
        return None
    
    def check_cascade_patterns(self, new_alarm, recent_alarms):
        """Check for known cascade failure patterns"""
        
        # Pattern: Router unreachable -> other devices have problems
        if new_alarm['alarm_type'] == 'DEVICE_UNREACHABLE' and '192.168.1.1' in new_alarm['device_ip']:
            # This is the main router - check for related failures
            related_failures = [a for a in recent_alarms 
                               if a['device_ip'] != new_alarm['device_ip']
                               and a['alarm_type'] in ['INTERFACE_DOWN', 'SERVICE_DOWN', 'HIGH_CPU_USAGE']]
            
            if related_failures:
                return {
                    'type': 'cascade_failure',
                    'root_cause_device': new_alarm['device_ip'],
                    'root_alarm': new_alarm,
                    'correlated_alarms': related_failures,
                    'confidence': 0.95,
                    'reason': 'Main router failure causing downstream issues'
                }
        
        return None
    
    def check_device_impact(self, new_alarm, recent_alarms):
        """Check if a critical device failure is impacting others"""
        
        # If we see SERVICE_DOWN or INTERFACE_DOWN alarms shortly after a router alarm
        router_alarms = [a for a in recent_alarms 
                        if a.get('device_type') == 'router' and 
                        a['alarm_type'] in ['HIGH_CPU_USAGE', 'DEVICE_UNREACHABLE']]
        
        if (router_alarms and 
            new_alarm['alarm_type'] in ['SERVICE_DOWN', 'INTERFACE_DOWN'] and
            new_alarm.get('device_type') in ['server', 'switch']):
            
            return {
                'type': 'infrastructure_impact',
                'root_cause_device': router_alarms[0]['device_ip'],
                'root_alarm': router_alarms[0],
                'correlated_alarms': [new_alarm],
                'confidence': 0.8,
                'reason': 'Router issue causing service/interface problems'
            }
        
        return None
    
    def handle_correlation(self, correlation):
        """Handle found correlation and generate RCA result"""
        
        print(f"   🎯 ROOT CAUSE ANALYSIS:")
        print(f"      🔍 Type: {correlation['type']}")
        print(f"      🖥️  Root Device: {correlation['root_cause_device']}")
        print(f"      📊 Confidence: {correlation['confidence']*100:.0f}%")
        print(f"      💡 Reason: {correlation['reason']}")
        
        suppressed = len(correlation['correlated_alarms'])
        self.suppressed_count += suppressed
        
        if suppressed > 0:
            print(f"      🔇 Suppressed {suppressed} related alarm(s)")
            print("         └─ These are likely symptoms, not root causes")
        
        # Generate recommendations
        recommendations = self.generate_recommendations(correlation['root_alarm']['alarm_type'])
        print(f"      🔧 Recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"         {i}. {rec}")
    
    def generate_recommendations(self, alarm_type):
        """Generate action recommendations based on alarm type"""
        
        recommendations = {
            'HIGH_CPU_USAGE': [
                "Check running processes on the device",
                "Verify if high traffic is causing CPU load",
                "Consider load balancing or hardware upgrade"
            ],
            'INTERFACE_DOWN': [
                "Check physical cable connections",
                "Verify interface configuration",
                "Test with cable replacement if needed"
            ],
            'DEVICE_UNREACHABLE': [
                "Check device power status",
                "Verify network connectivity to device",
                "Check firewall rules and routing"
            ],
            'SERVICE_DOWN': [
                "Restart the affected service",
                "Check service logs for errors",
                "Verify service dependencies are running"
            ],
            'HIGH_MEMORY_USAGE': [
                "Identify memory-consuming processes",
                "Check for memory leaks",
                "Consider memory upgrade if consistently high"
            ]
        }
        
        return recommendations.get(alarm_type, [
            "Investigate device status and logs",
            "Check for recent configuration changes",
            "Contact network administrator if issue persists"
        ])
    
    def print_stats(self):
        """Print current processing statistics"""
        print(f"   📈 Stats: {self.processed_count} processed | "
              f"{self.suppressed_count} suppressed | "
              f"{self.root_causes_found} root causes found")

def main():
    print("🔍 Starting Simple RCA Processor")
    print("💡 This analyzes network alarms and finds root causes")
    print("⏹️  Press Ctrl+C to stop\n")
    
    rca = SimpleRCA()
    
    if not KAFKA_AVAILABLE:
        print("🧪 Testing with sample data since Kafka is not available\n")
        
        # Simulate a cascade failure scenario
        test_alarms = [
            {
                "device_ip": "192.168.1.1",
                "device_type": "router", 
                "alarm_type": "DEVICE_UNREACHABLE",
                "severity": "CRITICAL",
                "timestamp": datetime.now().isoformat(),
                "description": "Router unreachable"
            },
            {
                "device_ip": "192.168.1.10",
                "device_type": "switch",
                "alarm_type": "INTERFACE_DOWN", 
                "severity": "WARNING",
                "timestamp": (datetime.now() + timedelta(seconds=5)).isoformat(),
                "description": "Interface down on switch"
            },
            {
                "device_ip": "192.168.1.20",
                "device_type": "server",
                "alarm_type": "SERVICE_DOWN",
                "severity": "CRITICAL", 
                "timestamp": (datetime.now() + timedelta(seconds=10)).isoformat(),
                "description": "Web service down"
            }
        ]
        
        print("Simulating cascade failure scenario...")
        for alarm in test_alarms:
            rca.add_alarm(alarm)
            import time
            time.sleep(2)  # Small delay to show sequence
        return
    
    try:
        # Connect to Kafka
        consumer = KafkaConsumer(
            'network-alarms',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='latest',  # Only get new messages
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        
        print("✅ Connected to Kafka")
        print("👂 Listening for alarms on 'network-alarms' topic...")
        print("💡 Start the alarm generator in another terminal to see this in action!\n")
        
        for message in consumer:
            alarm = message.value
            rca.add_alarm(alarm)
            
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopped RCA Processor")
        print(f"📊 Final Stats:")
        print(f"   • Processed: {rca.processed_count} alarms")
        print(f"   • Suppressed: {rca.suppressed_count} alarms") 
        print(f"   • Root causes found: {rca.root_causes_found}")
        
        if rca.processed_count > 0:
            suppression_rate = (rca.suppressed_count / rca.processed_count) * 100
            print(f"   • Suppression rate: {suppression_rate:.1f}%")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure Kafka is running and try again")

if __name__ == "__main__":
    main()
