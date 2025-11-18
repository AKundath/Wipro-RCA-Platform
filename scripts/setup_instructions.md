# Setup Instructions

## Quick Start Guide

### Prerequisites Check
```bash
# Check Python version
python3 --version

# Check Java version (for Kafka)
java -version
```

### Installation Steps

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd network-rca-platform
```

2. **Install Kafka**
```bash
wget https://downloads.apache.org/kafka/3.8.0/kafka_2.13-3.8.0.tgz
tar -xzf kafka_2.13-3.8.0.tgz
cd kafka_2.13-3.8.0
```

3. **Setup Python Environment**
```bash
python3 -m venv rca-env
source rca-env/bin/activate
pip install -r requirements.txt
```

4. **Start Services (in separate terminals)**
```bash
# Terminal 1: Zookeeper
cd kafka_2.13-3.8.0
bin/zookeeper-server-start.sh config/zookeeper.properties

# Terminal 2: Kafka Broker
bin/kafka-server-start.sh config/server.properties

# Terminal 3: Create Topic
bin/kafka-topics.sh --create --topic network-alarms --bootstrap-server localhost:9092

# Terminal 4: RCA Processor
cd network-rca-platform/src
python rca_processor.py

# Terminal 5: Web Dashboard
python web_dashboard.py

# Terminal 6: Alarm Generator
python alarm_generator.py
```

5. **Access Dashboard**
Open browser: http://localhost:5000

## Troubleshooting

### Kafka Connection Issues
- Ensure Zookeeper is running first
- Check if port 9092 is available
- Verify Kafka broker is started successfully

### Python Dependencies
- Use Python 3.10 or higher
- Activate virtual environment before running
- Re-run `pip install -r requirements.txt` if needed

### Dashboard Not Loading
- Check if Flask is running on port 5000
- Verify no other service is using port 5000
- Check firewall settings
