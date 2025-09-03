import pandapipes as pp
import xml.etree.ElementTree as ET
import matlab.engine  # Requires MATLAB installed
from flask import Flask, render_template, request, jsonify
from pymodbus.client import ModbusTcpClient
import threading
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

app = Flask(__name__)

# Global variables
net = None
eng = matlab.engine.start_matlab()  # Start MATLAB engine
plc_client = ModbusTcpClient('localhost', port=502)  # Assume OpenPLC at localhost:502
simulation_running = False

def load_gaslib_network(net_file='gaslib_data/GasLib-134.net', scn_file='gaslib_data/GasLib-134.scn'):
    global net
    net = pp.create_empty_network(fluid="hgas")  # High-calorific gas
    tree = ET.parse(net_file)
    root = tree.getroot()
    node_map = {}
    for node in root.findall('.//node'):
        id_ = node.get('id')
        pressure = float(node.get('pMin', '1'))  # Use min pressure as initial
        node_map[id_] = pp.create_junction(net, pn_bar=pressure, tfluid_k=293, name=id_)
    for pipe in root.findall('.//pipe'):
        from_node = pipe.get('from')
        to_node = pipe.get('to')
        length = float(pipe.get('length')) / 1000  # m to km
        diameter = float(pipe.get('diameter')) / 1000  # mm to m
        roughness = float(pipe.get('roughness', '0.0001'))  # Default
        pp.create_pipe_from_parameters(net, node_map[from_node], node_map[to_node], length_km=length, diameter_m=diameter, k_mm=roughness * 1000)
    # Add compressors, valves similarly (extend as needed)
    
    # Load scenarios (sinks/sources)
    tree_scn = ET.parse(scn_file)
    root_scn = tree_scn.getroot()
    density = pp.get_fluid(net).get_density(t=293)  # kg/m3 for mass flow conversion
    for source in root_scn.findall('.//source'):
        node = source.get('node')
        vol_flow = float(source.get('value'))  # Nm3/h
        mass_flow = (vol_flow / 3600) * density  # to kg/s
        pp.create_ext_grid(net, node_map[node], p_bar=60, t_k=293)  # Example pressure
    for sink in root_scn.findall('.//sink'):
        node = sink.get('node')
        vol_flow = float(sink.get('value'))
        mass_flow = (vol_flow / 3600) * density
        pp.create_sink(net, node_map[node], mdot_kg_per_s=mass_flow)
    return net

def run_pipeflow():
    pp.pipeflow(net)
    return net.res_junction, net.res_pipe

def matlab_transient_simulation(pipe_length=1, diameter=0.1, initial_pressure=1, flow_rate=0.02):
    # Call MATLAB for transient (e.g., pressure wave during transition)
    eng.cd(r'/path/to/matlab/scripts')  # Set to your MATLAB script dir
    result = eng.simulate_gas_transition(float(pipe_length), float(diameter), float(initial_pressure), float(flow_rate))
    return result  # Assume returns dict with time, pressure, velocity

def plc_control():
    while simulation_running:
        plc_client.connect()
        pressure = plc_client.read_holding_registers(0, 1).registers[0]  # Read sensor (pressure)
        if pressure > 5000:  # Example threshold (scale appropriately)
            plc_client.write_coil(0, False)  # Close valve
        plc_client.close()
        time.sleep(1)

# ICSSIM Extension Example (in ICSSIM/src/physical_processes/gas_pipeline.py)
# class GasPipelineProcess(PhysicalProcess):
#     def __init__(self):
#         super().__init__()
#         self.net = load_gaslib_network()
#     def update(self):
#         run_pipeflow()
#         # Update based on PLC inputs

@app.route('/')
def index():
    return render_template('index.html')  # Basic HTML with buttons, plots

@app.route('/load_network', methods=['POST'])
def load_network():
    global net
    net = load_gaslib_network()
    return jsonify({'status': 'Network loaded', 'nodes': len(net.junction)})

@app.route('/run_simulation', methods=['POST'])
def run_simulation():
    global simulation_running
    simulation_running = True
    threading.Thread(target=plc_control).start()
    junction_res, pipe_res = run_pipeflow()
    transient_res = matlab_transient_simulation()  # Example call
    # Generate Plotly figure
    fig = make_subplots(rows=2, cols=1)
    fig.add_trace(go.Scatter(x=junction_res.index, y=junction_res.p_bar, mode='lines', name='Pressure'), row=1, col=1)
    fig.add_trace(go.Scatter(x=pipe_res.index, y=pipe_res.v_mean_m_per_s, mode='lines', name='Velocity'), row=2, col=1)
    graphJSON = fig.to_json()
    return jsonify({'graph': graphJSON, 'transient': transient_res})

@app.route('/stop_simulation', methods=['POST'])
def stop_simulation():
    global simulation_running
    simulation_running = False
    return jsonify({'status': 'Simulation stopped'})

if __name__ == '__main__':
    app.run(debug=True)