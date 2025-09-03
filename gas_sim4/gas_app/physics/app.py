# physics/app.py
import numpy as np
import matlab.engine
from scipy import optimize
import json
import time
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

class GasPhysicsSimulator:
    def __init__(self, gaslib_file):
        self.gaslib_file = gaslib_file
        self.eng = matlab.engine.start_matlab()
        self.conn = psycopg2.connect(
            dbname="pipeline", user="simulator", 
            password="simulator", host="db"
        )
        
        # Load GasLib data
        self.load_gaslib_data()
        
    def load_gaslib_data(self):
        # Parse GasLib-134 XML file
        import xml.etree.ElementTree as ET
        tree = ET.parse(self.gaslib_file)
        root = tree.getroot()
        
        self.nodes = {}
        self.edges = {}
        
        # Extract nodes
        for node in root.findall('.//node'):
            node_id = node.get('id')
            self.nodes[node_id] = {
                'type': node.get('type'),
                'x': float(node.find('x').text),
                'y': float(node.find('y').text)
            }
        
        # Extract edges (pipes)
        for edge in root.findall('.//pipe'):
            edge_id = edge.get('id')
            self.edges[edge_id] = {
                'from': edge.get('from'),
                'to': edge.get('to'),
                'length': float(edge.find('length').text),
                'diameter': float(edge.find('diameter').text),
                'roughness': float(edge.find('roughness').text)
            }
    
    def calculate_flow(self, pressure_in, pressure_out, diameter, length, roughness, gas_properties):
        # Use Weymouth equation for gas flow
        # Q = C * sqrt((P1^2 - P2^2) * D^5 / (L * G * T * Z))
        T = gas_properties['temperature'] + 273.15  # Convert to Kelvin
        Z = gas_properties['compressibility']
        G = gas_properties['specific_gravity']
        
        # Calculate flow
        base_pressure = 101.325  # kPa
        base_temperature = 288.15  # K
        
        C = (math.pi/4) * math.sqrt(
            (2 * base_pressure) / 
            (G * 0.0289644 * 8.314462618 * base_temperature * Z)
        )
        
        flow = C * diameter**2.5 * math.sqrt(
            (pressure_in**2 - pressure_out**2) / 
            (length * G * T * Z)
        )
        
        return flow
    
    def simulate_network(self, inputs, demands):
        # Implement network simulation using Newton-Raphson method
        # This is a simplified version - actual implementation would be more complex
        
        results = {}
        
        # Calculate flows and pressures throughout the network
        for edge_id, edge in self.edges.items():
            from_node = edge['from']
            to_node = edge['to']
            
            # Get pressures (simplified - in reality would solve system of equations)
            p_in = inputs.get(from_node, 5000)  # kPa
            p_out = demands.get(to_node, 3000)  # kPa
            
            flow = self.calculate_flow(
                p_in, p_out, 
                edge['diameter'], edge['length'], edge['roughness'],
                {'temperature': 15, 'compressibility': 0.9, 'specific_gravity': 0.6}
            )
            
            results[edge_id] = {
                'flow': flow,
                'from_pressure': p_in,
                'to_pressure': p_out
            }
        
        return results
    
    def save_to_db(self, results):
        cur = self.conn.cursor()
        
        # Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_data (
                timestamp TIMESTAMPTZ NOT NULL,
                edge_id TEXT NOT NULL,
                flow REAL,
                from_pressure REAL,
                to_pressure REAL,
                PRIMARY KEY (timestamp, edge_id)
            )
        """)
        
        # Convert results to list of tuples for batch insert
        data = []
        timestamp = datetime.now()
        for edge_id, values in results.items():
            data.append((
                timestamp, edge_id, 
                values['flow'], 
                values['from_pressure'], 
                values['to_pressure']
            ))
        
        # Insert data
        execute_values(
            cur,
            "INSERT INTO pipeline_data (timestamp, edge_id, flow, from_pressure, to_pressure) VALUES %s",
            data
        )
        
        self.conn.commit()
        cur.close()

if __name__ == "__main__":
    simulator = GasPhysicsSimulator("/gaslib/GasLib-134.xml")
    
    # Main simulation loop
    while True:
        # Get current inputs and demands (in a real system, this would come from SCADA)
        inputs = {"source1": 5000}  # Pressure at source nodes
        demands = {"demand1": 3000}  # Pressure demands at consumption nodes
        
        # Simulate network
        results = simulator.simulate_network(inputs, demands)
        
        # Save to database
        simulator.save_to_db(results)
        
        time.sleep(1)  # Simulate at 1Hz