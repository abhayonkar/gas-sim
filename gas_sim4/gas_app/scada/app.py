# scada/app.py
from flask import Flask, jsonify
import requests
import json
import time
from datetime import datetime
import psycopg2

app = Flask(__name__)

class SCADASimulator:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="pipeline", user="simulator", 
            password="simulator", host="db"
        )
        self.plc_url = "http://openplc:8080"
        
    def get_sensor_data(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT edge_id, flow, from_pressure, to_pressure 
            FROM pipeline_data 
            WHERE timestamp = (SELECT MAX(timestamp) FROM pipeline_data)
        """)
        
        data = {}
        for row in cur.fetchall():
            edge_id, flow, from_pressure, to_pressure = row
            data[edge_id] = {
                'flow': flow,
                'from_pressure': from_pressure,
                'to_pressure': to_pressure
            }
        
        cur.close()
        return data
    
    def send_to_plc(self, data):
        # Convert to Modbus format (simplified)
        # In a real implementation, you would use a Modbus library
        modbus_data = {}
        
        for edge_id, values in data.items():
            # Map values to Modbus registers
            modbus_data[f"flow_{edge_id}"] = int(values['flow'] * 100)
            modbus_data[f"pressure_in_{edge_id}"] = int(values['from_pressure'] * 10)
            modbus_data[f"pressure_out_{edge_id}"] = int(values['to_pressure'] * 10)
        
        # Send to OpenPLC (simplified)
        try:
            response = requests.post(
                f"{self.plc_url}/api/data", 
                json=modbus_data,
                timeout=1
            )
            return response.status_code == 200
        except:
            return False
    
    def get_plc_commands(self):
        # Get control commands from PLC
        try:
            response = requests.get(f"{self.plc_url}/api/commands", timeout=1)
            return response.json()
        except:
            return {}

@app.route('/api/data', methods=['GET'])
def get_data():
    scada = SCADASimulator()
    data = scada.get_sensor_data()
    return jsonify(data)

@app.route('/api/control', methods=['POST'])
def control():
    # Receive control commands from web interface
    scada = SCADASimulator()
    commands = request.json
    
    # Send commands to PLC
    success = scada.send_to_plc_control(commands)
    
    return jsonify({"success": success})

if __name__ == "__main__":
    scada = SCADASimulator()
    
    # Main SCADA loop
    while True:
        # Get sensor data from physics engine (via database)
        sensor_data = scada.get_sensor_data()
        
        # Send to PLC
        scada.send_to_plc(sensor_data)
        
        # Get commands from PLC
        commands = scada.get_plc_commands()
        
        # Process commands (in a real system, this would affect the physics simulation)
        if commands:
            print(f"Received commands: {commands}")
        
        time.sleep(0.5)  # SCADA typically runs at 2Hz

    # Start Flask app
    app.run(host='0.0.0.0', port=5001)