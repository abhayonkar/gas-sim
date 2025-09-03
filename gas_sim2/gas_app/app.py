# Gas Pipeline Industrial Simulator
# Main Flask Application with SCADA, PLC, and Physical Simulation

import os
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import time
import sqlite3
from datetime import datetime
import requests
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from scipy.integrate import odeint
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gas_pipeline_simulator_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

@dataclass
class PipelineNode:
    """Represents a node in the gas pipeline network"""
    node_id: str
    name: str
    x_coord: float
    y_coord: float
    pressure: float
    temperature: float
    flow_rate: float
    node_type: str  # 'source', 'junction', 'sink', 'compressor'
    
@dataclass
class PipelineEdge:
    """Represents a pipe connection between nodes"""
    edge_id: str
    from_node: str
    to_node: str
    length: float
    diameter: float
    roughness: float
    max_pressure: float
    current_flow: float

class GasPhysicsSimulator:
    """Simulates physical properties of gas flow"""
    
    def __init__(self):
        # Gas properties (Natural Gas)
        self.gas_constant = 8.314  # J/(mol·K)
        self.molar_mass = 0.016043  # kg/mol for methane
        self.specific_gravity = 0.554
        self.viscosity = 1.1e-5  # Pa·s
        self.compressibility_factor = 0.92
        
    def calculate_pressure_drop(self, flow_rate, length, diameter, roughness, inlet_pressure, temperature):
        """Calculate pressure drop using Weymouth equation"""
        try:
            # Convert units
            flow_scf = flow_rate * 1000  # Convert to SCF/day
            length_miles = length / 1609.34  # Convert to miles
            diameter_inches = diameter * 39.37  # Convert to inches
            
            # Weymouth equation
            pressure_drop_squared = (inlet_pressure**2) - (
                433.5 * (flow_scf**1.852) * (self.specific_gravity * temperature * length_miles) /
                (diameter_inches**4.852)
            )
            
            outlet_pressure = np.sqrt(max(0, pressure_drop_squared))
            return max(0, inlet_pressure - outlet_pressure)
        except:
            return 0.1  # Default small pressure drop
    
    def calculate_gas_density(self, pressure, temperature):
        """Calculate gas density using ideal gas law with compressibility"""
        pressure_pa = pressure * 1e5  # Convert bar to Pa
        temperature_k = temperature + 273.15  # Convert to Kelvin
        
        density = (pressure_pa * self.molar_mass) / (
            self.compressibility_factor * self.gas_constant * temperature_k
        )
        return density
    
    def calculate_velocity(self, flow_rate, diameter, density):
        """Calculate gas velocity in pipe"""
        area = np.pi * (diameter / 2)**2
        mass_flow = flow_rate * density
        velocity = mass_flow / (density * area)
        return velocity

class PLCSimulator:
    """Simulates PLC operations and ladder logic"""
    
    def __init__(self):
        self.inputs = {}
        self.outputs = {}
        self.memory = {}
        self.timers = {}
        self.counters = {}
        self.alarms = []
        
    def update_input(self, address, value):
        """Update PLC input"""
        self.inputs[address] = value
        
    def get_output(self, address):
        """Get PLC output"""
        return self.outputs.get(address, False)
    
    def execute_ladder_logic(self, pipeline_data):
        """Execute simplified ladder logic for gas pipeline control"""
        try:
            # Emergency shutdown logic
            for node_id, node in pipeline_data['nodes'].items():
                pressure_high = node['pressure'] > 80  # bar
                pressure_low = node['pressure'] < 5   # bar
                
                # High pressure alarm
                if pressure_high:
                    self.outputs[f'ALARM_HIGH_PRESS_{node_id}'] = True
                    self.alarms.append({
                        'timestamp': datetime.now().isoformat(),
                        'type': 'HIGH_PRESSURE',
                        'node': node_id,
                        'value': node['pressure']
                    })
                
                # Low pressure alarm
                if pressure_low:
                    self.outputs[f'ALARM_LOW_PRESS_{node_id}'] = True
                    self.alarms.append({
                        'timestamp': datetime.now().isoformat(),
                        'type': 'LOW_PRESSURE',
                        'node': node_id,
                        'value': node['pressure']
                    })
                
                # Compressor control
                if node['node_type'] == 'compressor':
                    compressor_on = node['pressure'] < 40  # Start compressor below 40 bar
                    self.outputs[f'COMPRESSOR_{node_id}'] = compressor_on
                    
            # Valve control logic
            for edge_id, edge in pipeline_data['edges'].items():
                valve_open = not (
                    self.outputs.get(f'ALARM_HIGH_PRESS_{edge["from_node"]}', False) or
                    self.outputs.get(f'ALARM_HIGH_PRESS_{edge["to_node"]}', False)
                )
                self.outputs[f'VALVE_{edge_id}'] = valve_open
                
        except Exception as e:
            logger.error(f"PLC logic execution error: {e}")

class SCADASystem:
    """SCADA system for monitoring and control"""
    
    def __init__(self):
        self.hmi_data = {}
        self.historical_data = []
        self.alarms = []
        self.trends = {}
        
    def update_hmi_data(self, pipeline_data, plc_outputs):
        """Update HMI display data"""
        self.hmi_data = {
            'timestamp': datetime.now().isoformat(),
            'nodes': pipeline_data['nodes'],
            'edges': pipeline_data['edges'],
            'plc_status': plc_outputs,
            'system_status': self.get_system_status(pipeline_data)
        }
        
        # Store historical data
        self.historical_data.append({
            'timestamp': datetime.now().isoformat(),
            'data': pipeline_data.copy()
        })
        
        # Keep only last 1000 records
        if len(self.historical_data) > 1000:
            self.historical_data = self.historical_data[-1000:]
    
    def get_system_status(self, pipeline_data):
        """Get overall system status"""
        total_nodes = len(pipeline_data['nodes'])
        alarm_nodes = 0
        
        for node in pipeline_data['nodes'].values():
            if node['pressure'] > 80 or node['pressure'] < 5:
                alarm_nodes += 1
        
        if alarm_nodes == 0:
            status = 'NORMAL'
        elif alarm_nodes / total_nodes < 0.2:
            status = 'WARNING'
        else:
            status = 'ALARM'
            
        return {
            'status': status,
            'total_nodes': total_nodes,
            'alarm_nodes': alarm_nodes,
            'efficiency': max(0, 100 - (alarm_nodes / total_nodes) * 100)
        }

class PipelineSimulator:
    """Main pipeline simulation engine"""
    
    def __init__(self):
        self.nodes = {}
        self.edges = {}
        self.physics = GasPhysicsSimulator()
        self.plc = PLCSimulator()
        self.scada = SCADASystem()
        self.simulation_running = False
        self.simulation_thread = None
        
        # Initialize database
        self.init_database()
        
        # Load GasLib data (simplified version)
        self.load_gaslib_data()
        
    def init_database(self):
        """Initialize SQLite database for data storage"""
        conn = sqlite3.connect('pipeline_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS simulation_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                node_id TEXT,
                pressure REAL,
                temperature REAL,
                flow_rate REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                type TEXT,
                node_id TEXT,
                description TEXT,
                value REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def load_gaslib_data(self):
        """Load simplified GasLib-134 network data"""
        # Simplified version of GasLib nodes and connections
        gaslib_nodes = [
            {'id': 'N1', 'name': 'Source_1', 'x': 0, 'y': 0, 'type': 'source'},
            {'id': 'N2', 'name': 'Junction_1', 'x': 100, 'y': 50, 'type': 'junction'},
            {'id': 'N3', 'name': 'Compressor_1', 'x': 200, 'y': 75, 'type': 'compressor'},
            {'id': 'N4', 'name': 'Junction_2', 'x': 300, 'y': 100, 'type': 'junction'},
            {'id': 'N5', 'name': 'Sink_1', 'x': 400, 'y': 125, 'type': 'sink'},
            {'id': 'N6', 'name': 'Junction_3', 'x': 150, 'y': -50, 'type': 'junction'},
            {'id': 'N7', 'name': 'Sink_2', 'x': 250, 'y': -75, 'type': 'sink'}
        ]
        
        gaslib_edges = [
            {'id': 'E1', 'from': 'N1', 'to': 'N2', 'length': 111.8, 'diameter': 0.6},
            {'id': 'E2', 'from': 'N2', 'to': 'N3', 'length': 111.8, 'diameter': 0.6},
            {'id': 'E3', 'from': 'N3', 'to': 'N4', 'length': 111.8, 'diameter': 0.6},
            {'id': 'E4', 'from': 'N4', 'to': 'N5', 'length': 111.8, 'diameter': 0.6},
            {'id': 'E5', 'from': 'N2', 'to': 'N6', 'length': 111.8, 'diameter': 0.4},
            {'id': 'E6', 'from': 'N6', 'to': 'N7', 'length': 111.8, 'diameter': 0.4}
        ]
        
        # Initialize nodes
        for node_data in gaslib_nodes:
            self.nodes[node_data['id']] = PipelineNode(
                node_id=node_data['id'],
                name=node_data['name'],
                x_coord=node_data['x'],
                y_coord=node_data['y'],
                pressure=50.0,  # Initial pressure in bar
                temperature=20.0,  # Initial temperature in Celsius
                flow_rate=10.0,  # Initial flow rate in kg/s
                node_type=node_data['type']
            )
        
        # Initialize edges
        for edge_data in gaslib_edges:
            self.edges[edge_data['id']] = PipelineEdge(
                edge_id=edge_data['id'],
                from_node=edge_data['from'],
                to_node=edge_data['to'],
                length=edge_data['length'] * 1000,  # Convert to meters
                diameter=edge_data['diameter'],
                roughness=0.05,  # mm
                max_pressure=100.0,  # bar
                current_flow=10.0
            )
    
    def simulate_step(self):
        """Execute one simulation step"""
        try:
            # Update node pressures based on physics
            for edge_id, edge in self.edges.items():
                from_node = self.nodes[edge.from_node]
                to_node = self.nodes[edge.to_node]
                
                # Calculate pressure drop
                pressure_drop = self.physics.calculate_pressure_drop(
                    edge.current_flow,
                    edge.length,
                    edge.diameter,
                    edge.roughness,
                    from_node.pressure,
                    from_node.temperature
                )
                
                # Update downstream pressure
                if from_node.node_type == 'source':
                    from_node.pressure = 60 + np.random.normal(0, 2)  # Source pressure variation
                elif from_node.node_type == 'compressor':
                    # Compressor boosts pressure
                    compressor_on = self.plc.get_output(f'COMPRESSOR_{from_node.node_id}')
                    if compressor_on:
                        from_node.pressure = min(80, from_node.pressure + 15)
                
                # Apply pressure drop
                new_pressure = from_node.pressure - pressure_drop
                if to_node.node_type != 'sink':
                    to_node.pressure = max(5, new_pressure)
                
                # Update flow rates based on valve positions
                valve_open = self.plc.get_output(f'VALVE_{edge_id}')
                if not valve_open:
                    edge.current_flow = 0
                else:
                    # Simple flow calculation based on pressure difference
                    pressure_diff = from_node.pressure - to_node.pressure
                    edge.current_flow = max(0, 5 + pressure_diff * 0.5)
            
            # Update temperatures (simplified heat transfer)
            ambient_temp = 20
            for node in self.nodes.values():
                node.temperature += (ambient_temp - node.temperature) * 0.01
                node.temperature += np.random.normal(0, 0.5)  # Random variation
            
            # Execute PLC logic
            pipeline_data = {
                'nodes': {nid: {
                    'pressure': node.pressure,
                    'temperature': node.temperature,
                    'flow_rate': node.flow_rate,
                    'node_type': node.node_type,
                    'x': node.x_coord,
                    'y': node.y_coord
                } for nid, node in self.nodes.items()},
                'edges': {eid: {
                    'from_node': edge.from_node,
                    'to_node': edge.to_node,
                    'current_flow': edge.current_flow,
                    'length': edge.length,
                    'diameter': edge.diameter
                } for eid, edge in self.edges.items()}
            }
            
            self.plc.execute_ladder_logic(pipeline_data)
            
            # Update SCADA system
            self.scada.update_hmi_data(pipeline_data, self.plc.outputs)
            
            # Store data in database
            self.store_simulation_data()
            
            # Emit real-time data via WebSocket
            socketio.emit('simulation_data', {
                'nodes': pipeline_data['nodes'],
                'edges': pipeline_data['edges'],
                'plc_outputs': self.plc.outputs,
                'system_status': self.scada.get_system_status(pipeline_data)
            })
            
        except Exception as e:
            logger.error(f"Simulation step error: {e}")
    
    def store_simulation_data(self):
        """Store current simulation data in database"""
        try:
            conn = sqlite3.connect('pipeline_data.db')
            cursor = conn.cursor()
            
            timestamp = datetime.now().isoformat()
            
            for node_id, node in self.nodes.items():
                cursor.execute('''
                    INSERT INTO simulation_data (timestamp, node_id, pressure, temperature, flow_rate)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp, node_id, node.pressure, node.temperature, node.flow_rate))
            
            # Store alarms
            for alarm in self.plc.alarms:
                cursor.execute('''
                    INSERT INTO alarms (timestamp, type, node_id, description, value)
                    VALUES (?, ?, ?, ?, ?)
                ''', (alarm['timestamp'], alarm['type'], alarm['node'], 
                     f"{alarm['type']} at {alarm['node']}", alarm['value']))
            
            self.plc.alarms.clear()  # Clear processed alarms
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database storage error: {e}")
    
    def start_simulation(self):
        """Start the simulation loop"""
        self.simulation_running = True
        
        def simulation_loop():
            while self.simulation_running:
                self.simulate_step()
                time.sleep(1)  # 1-second simulation step
        
        self.simulation_thread = threading.Thread(target=simulation_loop)
        self.simulation_thread.start()
        logger.info("Simulation started")
    
    def stop_simulation(self):
        """Stop the simulation"""
        self.simulation_running = False
        if self.simulation_thread:
            self.simulation_thread.join()
        logger.info("Simulation stopped")

# Initialize global simulator
simulator = PipelineSimulator()

# Flask Routes
@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/start_simulation', methods=['POST'])
def start_simulation():
    """Start the simulation"""
    if not simulator.simulation_running:
        simulator.start_simulation()
        return jsonify({'status': 'started', 'message': 'Simulation started successfully'})
    return jsonify({'status': 'running', 'message': 'Simulation is already running'})

@app.route('/api/stop_simulation', methods=['POST'])
def stop_simulation():
    """Stop the simulation"""
    if simulator.simulation_running:
        simulator.stop_simulation()
        return jsonify({'status': 'stopped', 'message': 'Simulation stopped successfully'})
    return jsonify({'status': 'stopped', 'message': 'Simulation is not running'})

@app.route('/api/current_data')
def get_current_data():
    """Get current simulation data"""
    pipeline_data = {
        'nodes': {nid: {
            'pressure': node.pressure,
            'temperature': node.temperature,
            'flow_rate': node.flow_rate,
            'node_type': node.node_type,
            'x': node.x_coord,
            'y': node.y_coord
        } for nid, node in simulator.nodes.items()},
        'edges': {eid: {
            'from_node': edge.from_node,
            'to_node': edge.to_node,
            'current_flow': edge.current_flow,
            'length': edge.length,
            'diameter': edge.diameter
        } for eid, edge in simulator.edges.items()}
    }
    
    return jsonify({
        'pipeline_data': pipeline_data,
        'plc_outputs': simulator.plc.outputs,
        'system_status': simulator.scada.get_system_status(pipeline_data),
        'simulation_running': simulator.simulation_running
    })

@app.route('/api/historical_data')
def get_historical_data():
    """Get historical simulation data"""
    conn = sqlite3.connect('pipeline_data.db')
    
    # Get last 100 records for each node
    query = '''
        SELECT timestamp, node_id, pressure, temperature, flow_rate
        FROM simulation_data
        WHERE timestamp > datetime('now', '-1 hour')
        ORDER BY timestamp DESC
        LIMIT 1000
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return jsonify(df.to_dict('records'))

@app.route('/api/alarms')
def get_alarms():
    """Get recent alarms"""
    conn = sqlite3.connect('pipeline_data.db')
    
    query = '''
        SELECT timestamp, type, node_id, description, value
        FROM alarms
        WHERE timestamp > datetime('now', '-24 hours')
        ORDER BY timestamp DESC
        LIMIT 100
    '''
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return jsonify(df.to_dict('records'))

@app.route('/api/control_valve/<valve_id>/<action>')
def control_valve(valve_id, action):
    """Manual valve control"""
    valve_address = f'VALVE_{valve_id}'
    
    if action == 'open':
        simulator.plc.outputs[valve_address] = True
        message = f'Valve {valve_id} opened'
    elif action == 'close':
        simulator.plc.outputs[valve_address] = False
        message = f'Valve {valve_id} closed'
    else:
        return jsonify({'error': 'Invalid action'}), 400
    
    return jsonify({'message': message, 'valve_id': valve_id, 'status': action})

@app.route('/api/control_compressor/<compressor_id>/<action>')
def control_compressor(compressor_id, action):
    """Manual compressor control"""
    compressor_address = f'COMPRESSOR_{compressor_id}'
    
    if action == 'start':
        simulator.plc.outputs[compressor_address] = True
        message = f'Compressor {compressor_id} started'
    elif action == 'stop':
        simulator.plc.outputs[compressor_address] = False
        message = f'Compressor {compressor_id} stopped'
    else:
        return jsonify({'error': 'Invalid action'}), 400
    
    return jsonify({'message': message, 'compressor_id': compressor_id, 'status': action})

@app.route('/api/trend_data/<node_id>')
def get_trend_data(node_id):
    """Get trend data for a specific node"""
    conn = sqlite3.connect('pipeline_data.db')
    
    query = '''
        SELECT timestamp, pressure, temperature, flow_rate
        FROM simulation_data
        WHERE node_id = ? AND timestamp > datetime('now', '-1 hour')
        ORDER BY timestamp
    '''
    
    df = pd.read_sql_query(query, conn, params=(node_id,))
    conn.close()
    
    return jsonify(df.to_dict('records'))

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to pipeline simulator'})
    logger.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

if __name__ == '__main__':
    # Create templates directory and basic HTML template
    os.makedirs('templates', exist_ok=True)
    
    # Run the application
    logger.info("Starting Gas Pipeline Industrial Simulator")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)