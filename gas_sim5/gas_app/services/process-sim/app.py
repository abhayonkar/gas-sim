import threading, time, json
from flask import Flask, request, jsonify
from engine import GasNetwork, TransientSolver
from modbus_server import start_modbus_server, write_registers_snapshot

app = Flask(__name__)

net = GasNetwork.from_gaslib134("data/gaslib134.json")  # preprocessed GasLib-134
solver = TransientSolver(net)

state_lock = threading.Lock()
running = True

def sim_loop(dt=0.5):
    global running
    while running:
        with state_lock:
            solver.step(dt)
            snapshot = solver.snapshot()  # pressures, flows, actuator states
        write_registers_snapshot(snapshot)  # exposes to PLCs
        time.sleep(dt)

@app.route("/api/state", methods=["GET"])
def get_state():
    with state_lock:
        return jsonify(solver.snapshot())

@app.route("/api/setpoints", methods=["POST"])
def set_setpoints():
    data = request.get_json()
    with state_lock:
        solver.apply_setpoints(data)
    return jsonify({"ok": True})

@app.route("/api/scenario", methods=["POST"])
def apply_scenario():
    data = request.get_json()  # e.g., valve trip, demand change, compressor outage
    with state_lock:
        solver.apply_scenario(data)
    return jsonify({"ok": True})

if __name__ == "__main__":
    threading.Thread(target=start_modbus_server, daemon=True).start()
    threading.Thread(target=sim_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=7000)
