import json
import numpy as np

class GasNetwork:
    def __init__(self, nodes, pipes, compressors, valves):
        self.nodes = nodes
        self.pipes = pipes
        self.compressors = compressors
        self.valves = valves

    @staticmethod
    def from_gaslib134(path):
        with open(path) as f:
            data = json.load(f)
        # Map GasLib-134 nodes/edges to internal indices
        return GasNetwork(data["nodes"], data["pipes"], data["compressors"], data["valves"])

class TransientSolver:
    def __init__(self, net):
        self.net = net
        n = len(net["nodes"]) if isinstance(net, dict) else len(net.nodes)
        self.p = np.full(n, 5000.0)  # kPa initial
        self.q_edges = np.zeros(len(net.pipes))
        self.u = np.zeros(len(net.compressors) + len(net.valves))  # actuator targets

    def step(self, dt):
        # Simplified demo transient: relax to steady using algebraic pipe equations + linepack
        # Replace with isothermal Euler/semi-implicit scheme for realism
        self.p += 0.1*np.random.randn(*self.p.shape)  # placeholder stochastic perturbation

    def apply_setpoints(self, sp):
        # sp: {"compressor_ratios":[...], "valve_openings":[...], "injections":[(node,val)], "demands":[(node,val)]}
        pass

    def apply_scenario(self, scn):
        pass

    def snapshot(self):
        return {
            "pressures": self.p.tolist(),
            "flows": self.q_edges.tolist(),
            "actuators": self.u.tolist()
        }
