# Gas Pipeline Simulator

A comprehensive industrial control system simulator for gas pipeline operations, featuring SCADA systems, physics modeling, cybersecurity monitoring, and web-based visualization.

## Project Structure

```
gas-pipeline-simulator/
├── web/                 # Web interface and visualization
├── scada/              # SCADA system implementation
├── physics/            # Physical process simulation
├── ids/                # Intrusion Detection System
├── plc-programs/       # PLC control logic
├── gaslib/            # GasLib-134 network data
├── docker-compose.yml
└── README.md
```

## Features

- **Real-time Physics Simulation**: Accurate gas flow modeling using GasLib-134 network data
- **SCADA Interface**: Industrial control system with HMI capabilities
- **Cybersecurity Monitoring**: Integrated IDS for Modbus traffic analysis
- **Web Dashboard**: Browser-based monitoring and control interface
- **Containerized Architecture**: Docker-based deployment for easy setup and scaling

## Setup Instructions

### 1. Clone and Setup Project Structure

```bash
mkdir gas-pipeline-simulator
cd gas-pipeline-simulator
mkdir web scada physics ids plc-programs gaslib
```

### 2. Download GasLib-134

1. Download the GasLib-134 XML file from the official GasLib repository
2. Place the XML file in the `gaslib` directory

### 3. Create Dockerfiles for Each Service

Each service directory (`web`, `scada`, `physics`, `ids`) needs a Dockerfile.

**Example Dockerfile for physics service:**

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

### 4. Create Requirements Files

Create `requirements.txt` files for each Python service.

**Example for physics service:**

```txt
numpy
scipy
matlabengine
psycopg2-binary
```

### 5. Build and Run with Docker Compose

```bash
docker-compose up --build
```

### 6. Access the Web Interface

Open your browser and navigate to:
```
http://localhost:5000
```

## Adding Cybersecurity Measures

The integrated IDS system monitors Modbus traffic for suspicious patterns. To enhance security further:

### Authentication & Authorization
- Add user authentication to the web interface
- Implement role-based access control for API endpoints
- Use JWT tokens for session management

### Encrypted Communication
- Implement TLS encryption between all components
- Use certificate-based authentication for service communication
- Encrypt sensitive data at rest

### Network Segmentation
- Configure Docker networks to isolate critical components
- Implement firewall rules within containers
- Use separate networks for control and monitoring traffic

### Security Monitoring
- Enable comprehensive logging across all services
- Implement security event correlation
- Add real-time alerting for security incidents
- Regular security auditing and compliance checks

### Anomaly Detection
- Monitor physical system behavior for unusual patterns
- Implement machine learning-based anomaly detection
- Set up automated response to detected threats

## Testing the System

### Component Testing
Test each service individually using Docker:

```bash
# Test physics service
docker build -t gas-physics ./physics
docker run -p 8001:8001 gas-physics

# Test SCADA service  
docker build -t gas-scada ./scada
docker run -p 8002:8002 gas-scada

# Test IDS service
docker build -t gas-ids ./ids
docker run -p 8003:8003 gas-ids
```

### Integration Testing
Use Docker Compose to test the complete system:

```bash
docker-compose up --build
# Run integration test scripts
python tests/integration_tests.py
```

### Load Testing
Simulate multiple users and high traffic scenarios:

```bash
# Install Locust
pip install locust

# Run load tests
locust -f tests/load_tests.py --host=http://localhost:5000
```

### Security Testing
Use penetration testing tools to identify vulnerabilities:

```bash
# Network scanning
nmap -sV localhost

# Web application testing
# Use tools like OWASP ZAP or Burp Suite

# Modbus protocol testing
# Use specialized ICS security testing tools
```

## Architecture Overview

The system consists of several interconnected components:

1. **Physics Engine**: Simulates gas flow dynamics and pipeline physics
2. **SCADA System**: Provides industrial control and monitoring capabilities
3. **Web Interface**: Browser-based dashboard for system visualization
4. **IDS Monitor**: Real-time cybersecurity threat detection
5. **PLC Programs**: Automated control logic for pipeline operations

## Development Notes

This implementation provides a foundation for a realistic gas pipeline simulator. You can extend it by adding:

- More sophisticated physical models and equations
- Enhanced visualization with real-time charts and diagrams
- Additional cybersecurity features and threat detection
- Integration with external systems and databases
- Advanced control algorithms and optimization
- Historical data analysis and reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions, issues, or contributions, please open an issue on the project repository or contact the development team.