# flask_app/app.py
from flask import Flask, request, jsonify, send_file
import os
from gas_simulator import parse_gaslib_xml, build_pandapipes_network, run_steady, run_transient_lumped
from modbus_client import PLCClient
import matplotlib.pyplot as plt
import networkx as nx

app = Flask(__name__)
DATA_DIR = "/data"
os.makedirs(DATA_DIR, exist_ok=True)
plc = PLCClient()

@app.route("/upload_gaslib", methods=["POST"])
def upload_gaslib():
    f = request.files.get("file")
    if not f:
        return jsonify({"error":"no file"}), 400
    path = os.path.join(DATA_DIR, f.filename)
    f.save(path)
    parsed = parse_gaslib_xml(path)
    # save parsed to disk for later use
    return jsonify({"message":"uploaded","nodes":len(parsed['nodes']), "pipes":len(parsed['pipes'])})

@app.route("/simulate/steady", methods=["POST"])
def simulate_steady():
    filename = request.json.get("filename")
    if not filename:
        return jsonify({"error":"need filename"}), 400
    path = os.path.join(DATA_DIR, filename)
    parsed = parse_gaslib_xml(path)
    net = build_pandapipes_network(parsed)
    res = run_steady(net)
    # convert a couple of numbers to JSON-friendly format
    summary = {
        "junctions": res['junctions'].to_dict(orient='index'),
        "pipes": res['pipes'].to_dict(orient='index')
    }
    return jsonify(summary)

@app.route("/simulate/transient", methods=["POST"])
def simulate_transient():
    filename = request.json.get("filename")
    t_end = float(request.json.get("t_end", 60.0))
    dt = float(request.json.get("dt", 1.0))
    path = os.path.join(DATA_DIR, filename)
    parsed = parse_gaslib_xml(path)
    net = build_pandapipes_network(parsed)
    times, pressures = run_transient_lumped(net, t_end=t_end, dt=dt)
    return jsonify({"times": times, "pressures": pressures})

@app.route("/plc/write_valve", methods=["POST"])
def plc_write_valve():
    data = request.json
    coil = int(data.get("coil", 1))
    value = bool(data.get("value", False))
    plc.connect()
    plc.write_coil(coil, value)
    plc.close()
    return jsonify({"coil": coil, "value": value})

@app.route("/visualize_net", methods=["POST"])
def visualize_net():
    filename = request.json.get("filename")
    path = os.path.join(DATA_DIR, filename)
    parsed = parse_gaslib_xml(path)
    G = nx.Graph()
    for nid in parsed['nodes']:
        G.add_node(nid)
    for p in parsed['pipes']:
        G.add_edge(p['from'], p['to'])
    plt.figure(figsize=(8,6))
    pos = {nid:(ndata['x'] or i, ndata['y'] or i+1) for i,(nid,ndata) in enumerate(parsed['nodes'].items())}
    nx.draw(G, pos=pos, with_labels=True, node_size=30)
    img_path = os.path.join(DATA_DIR, "net_vis.png")
    plt.savefig(img_path, dpi=150)
    plt.close()
    return send_file(img_path, mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



# app.py
from flask import Flask, request, jsonify, send_file
import os
from gas_simulator import parse_gaslib_xml, build_pandapipes_network, run_steady, run_transient_lumped
from modbus_client import PLCClient
import matplotlib.pyplot as plt
import networkx as nx


app = Flask(__name__)
DATA_DIR = '/data'
os.makedirs(DATA_DIR, exist_ok=True)
plc = PLCClient()


@app.route('/upload_gaslib', methods=['POST'])
def upload_gaslib():
f = request.files.get('file')
if not f:
return jsonify({'error': 'no file'}), 400
path = os.path.join(DATA_DIR, f.filename)
f.save(path)
parsed = parse_gaslib_xml(path)
return jsonify({'message': 'uploaded', 'nodes': len(parsed['nodes']), 'pipes': len(parsed['pipes'])})


@app.route('/simulate/steady', methods=['POST'])
def simulate_steady():
filename = request.json.get('filename')
if not filename:
return jsonify({'error': 'need filename'}), 400
path = os.path.join(DATA_DIR, filename)
parsed = parse_gaslib_xml(path)
net = build_pandapipes_network(parsed)
res = run_steady(net)
summary = {
'junctions': res['junctions'].to_dict(orient='index'),
'pipes': res['pipes'].to_dict(orient='index')
}
return jsonify(summary)


@app.route('/simulate/transient', methods=['POST'])
def simulate_transient():
filename = request.json.get('filename')
t_end = float(request.json.get('t_end', 60.0))
dt = float(request.json.get('dt', 1.0))
path = os.path.join(DATA_DIR, filename)
parsed = parse_gaslib_xml(path)
net = build_pandapipes_network(parsed)
times, pressures = run_transient_lumped(net, t_end=t_end, dt=dt)
return jsonify({'times': times, 'pressures': pressures})


@app.route('/plc/write_valve', methods=['POST'])
def plc_write_valve():
data = request.json
coil = int(data.get('coil', 1))
value = bool(data.get('value', False))
plc.connect()
plc.write_coil(coil, value)
plc.close()
return jsonify({'coil': coil, 'value': value})      