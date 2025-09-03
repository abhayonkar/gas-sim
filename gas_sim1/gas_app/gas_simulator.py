# flask_app/gas_simulator.py
import xml.etree.ElementTree as ET
import pandapipes as pp
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, Tuple, Any, List

def parse_gaslib_xml(path: str) -> Dict[str,Any]:
    """
    Minimal parser for GasLib XML extracts:
      - nodes (id, x,y optional)
      - arcs/pipes (id, from, to, length, diameter)
      - supplies/demands (node id and massflow or pressure)
    GasLib has many fields; this parser extracts common fields for prototyping.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {'g':'http://www.gaslib.org/schema'}  # GasLib may use namespace; ignore if not present
    nodes = {}
    pipes = []
    # generic node parsing (GasLib uses <nodes> or <nodesList> -- we try several)
    for n in root.findall(".//node"):
        nid = n.get('id') or n.findtext('id') or n.findtext('nodeId') 
        if nid is None:
            continue
        # coords if present
        x = n.findtext('x') or n.findtext('posx')
        y = n.findtext('y') or n.findtext('posy')
        nodes[nid] = {'id':nid, 'x': float(x) if x else None, 'y': float(y) if y else None}
    # pipe/arc parsing
    for c in root.findall(".//arc") + root.findall(".//pipe") + root.findall(".//branch"):
        aid = c.get('id') or c.findtext('id')
        frm = c.findtext('from') or c.findtext('startNode') or c.findtext('fromNode')
        to = c.findtext('to') or c.findtext('endNode') or c.findtext('toNode')
        length = c.findtext('length')
        diam = c.findtext('diameter') or c.findtext('diam')
        if aid and frm and to:
            pipes.append({'id':aid, 'from':frm, 'to':to, 'length': float(length) if length else 1000.0, 'diam': float(diam) if diam else 0.5})
    # simplistic supply/demand parse
    supplies = []
    demands = []
    for s in root.findall(".//supply") + root.findall(".//source"):
        node = s.findtext('node') or s.findtext('nodeId')
        p = s.findtext('pressure') or s.findtext('p')
        m = s.findtext('massFlow') or s.findtext('m')
        supplies.append({'node':node, 'pressure': float(p) if p else None, 'massflow': float(m) if m else None})
    for d in root.findall(".//demand") + root.findall(".//sink"):
        node = d.findtext('node') or d.findtext('nodeId')
        m = d.findtext('massFlow') or d.findtext('m')
        demands.append({'node':node, 'massflow': float(m) if m else 0.0})
    return {'nodes':nodes, 'pipes':pipes, 'supplies':supplies, 'demands':demands}

def build_pandapipes_network(parsed: Dict[str,Any]) -> pp.pandapipesNet:
    net = pp.create_empty_network(fluid="lgas")  # light gas model; choose appropriate fluid
    node_to_junction = {}
    # create junctions
    for i, (nid, ndata) in enumerate(parsed['nodes'].items()):
        # pn_bar: initial nominal pressure (1 bar), tfluid_k: 293 K
        jidx = pp.create_junction(net, pn_bar=40.0, tfluid_k=293.0, name=str(nid))
        node_to_junction[nid] = jidx
    # create pipes
    for p in parsed['pipes']:
        a = node_to_junction.get(p['from'])
        b = node_to_junction.get(p['to'])
        if a is None or b is None:
            continue
        # diameter in m, length in m
        pp.create_pipe(net, from_junction=a, to_junction=b, length_m=p['length'], diameter_m=p['diam'], name=p['id'])
    # external grids (supplies) and sinks (demands)
    for s in parsed['supplies']:
        if s['node'] in node_to_junction:
            j = node_to_junction[s['node']]
            # if pressure given, create ext_grid with p_bar
            if s.get('pressure'):
                pp.create_ext_grid(net, junction=j, p_bar=s['pressure'], tfluid_k=293.0, name=f"ext_{s['node']}")
            elif s.get('massflow'):
                # create a source using sink with negative mass? For pandapipes we typically use ext_grid or create_source (advanced).
                pp.create_ext_grid(net, junction=j, p_bar=40.0, tfluid_k=293.0, name=f"ext_{s['node']}")
    for d in parsed['demands']:
        if d['node'] in node_to_junction:
            j = node_to_junction[d['node']]
            # create sinks: mass_flow_kg_per_s in pandapipes uses "mdot_kg_per_s"
            pp.create_sink(net, junction=j, mdot_kg_per_s=d.get('massflow', 0.0), name=f"sink_{d['node']}")
    return net

def run_steady(net: pp.pandapipesNet) -> Dict[str,pd.DataFrame]:
    """
    Run pandapipes pipeflow and return results tables (junctions + pipes).
    """
    pp.pipeflow(net)
    res_j = net.res_junction.copy()
    res_p = net.res_pipe.copy()
    return {'junctions': res_j, 'pipes': res_p}

# Simple lumped transient solver (DEMOnstration only)
def run_transient_lumped(net: pp.pandapipesNet, t_end=60.0, dt=1.0) -> Tuple[List[float], Dict[str, List[float]]]:
    """
    Very simplified transient: treat each junction as a capacitance where pressure changes according to net massflow.
    This is not a substitute for full PDE transient solver (method of characteristics), but good for control testing.
    """
    # initialize: use pandapipes steady solution as initial
    pp.pipeflow(net)
    junctions = list(net.junction.index)
    # collect initial pressures (Pa)
    pressures = {j: [net.res_junction.loc[j, 'p_bar'] * 1e5] for j in junctions}
    times = np.arange(0, t_end+dt, dt)
    # choose arbitrary capacitance per junction (demo parameter)
    C = {j: 1e5 for j in junctions}  # [Pa / (kg/s)] scaling factor - tune for realistic responses
    for k in range(1, len(times)):
        # for demonstration, recompute steady at each step is expensive; instead, compute net massflows from pipes using last pressures (approx)
        # we will use pandapipes to compute fluxes given the previous pressures by setting initial conditions (quick hack)
        # write last pressures back into net initial guess
        # NOTE: This is hacky; for realism use dedicated transient models.
        for j in junctions:
            net.junction.at[j, 'pn_bar'] = pressures[j][-1] / 1e5
        try:
            pp.pipeflow(net)
        except Exception:
            pass
        # compute net massflow into each junction: sum of connected pipes' massflow (approx)
        # net.res_pipe has 'mdot_kg_per_s' as result
        mdot_per_j = {j: 0.0 for j in junctions}
        for idx, row in net.res_pipe.iterrows():
            from_j = int(net.pipe.at[idx, 'from_junction'])
            to_j = int(net.pipe.at[idx, 'to_junction'])
            mdot = row.get('mdot_kg_per_s', 0.0)
            # massflow positive from 'from_j'->'to_j'
            mdot_per_j[from_j] -= mdot
            mdot_per_j[to_j] += mdot
        # update pressures
        for j in junctions:
            dP = (mdot_per_j[j] / C[j]) * dt  # very simplified
            newP = pressures[j][-1] + dP
            pressures[j].append(newP)
    # return times and pressures (pressure histories per junction)
    return times.tolist(), {str(j): pressures[j] for j in junctions}


import xml.etree.ElementTree as ET
# supplies and demands
supplies = []
demands = []
for s in root.findall('.//supply') + root.findall('.//source'):
node = s.findtext('node') or s.findtext('nodeId')
p = s.findtext('pressure') or s.findtext('p')
m = s.findtext('massFlow') or s.findtext('m')
supplies.append({'node': node, 'pressure': float(p) if p else None, 'massflow': float(m) if m else None})
for d in root.findall('.//demand') + root.findall('.//sink'):
node = d.findtext('node') or d.findtext('nodeId')
m = d.findtext('massFlow') or d.findtext('m')
demands.append({'node': node, 'massflow': float(m) if m else 0.0})


return {'nodes': nodes, 'pipes': pipes, 'supplies': supplies, 'demands': demands}




def build_pandapipes_network(parsed: Dict[str, Any]) -> pp.pandapipesNet:
net = pp.create_empty_network(fluid='lgas')
node_to_junction = {}
for i, (nid, ndata) in enumerate(parsed['nodes'].items()):
jidx = pp.create_junction(net, pn_bar=40.0, tfluid_k=293.0, name=str(nid))
node_to_junction[nid] = jidx
for p in parsed['pipes']:
a = node_to_junction.get(p['from'])
b = node_to_junction.get(p['to'])
if a is None or b is None:
continue
pp.create_pipe(net, from_junction=a, to_junction=b,
length_m=p['length'], diameter_m=p['diam'], name=p['id'])
for s in parsed['supplies']:
if s['node'] in node_to_junction:
j = node_to_junction[s['node']]
if s.get('pressure'):
pp.create_ext_grid(net, junction=j, p_bar=s['pressure'], tfluid_k=293.0, name=f"ext_{s['node']}")
else:
pp.create_ext_grid(net, junction=j, p_bar=40.0, tfluid_k=293.0, name=f"ext_{s['node']}")
for d in parsed['demands']:
if d['node'] in node_to_junction:
j = node_to_junction[d['node']]
pp.create_sink(net, junction=j, mdot_kg_per_s=d.get('massflow', 0.0), name=f"sink_{d['node']}")
return net




def run_steady(net: pp.pandapipesNet) -> Dict[str, pd.DataFrame]:
pp.pipeflow(net)
return {'junctions': net.res_junction.copy(), 'pipes': net.res_pipe.copy()}




# Very small lumped transient demo for control testing only


def run_transient_lumped(net: pp.pandapipesNet, t_end: float = 60.0, dt: float = 1.0) -> Tuple[List[float], dict]:
pp.pipeflow(net)
junctions = list(net.junction.index)
pressures = {j: [net.res_junction.loc[j, 'p_bar'] * 1e5] for j in junctions}
times = np.arange(0, t_end + dt, dt)
C = {j: 1e5 for j in junctions}
for k in range(1, len(times)):
for j in junctions:
net.junction.at[j, 'pn_bar'] = pressures[j][-1] / 1e5
try:
pp.pipeflow(net)
except Exception:
pass
mdot_per_j = {j: 0.0 for j in junctions}
for idx, row in net.res_pipe.iterrows():
from_j = int(net.pipe.at[idx, 'from_junction'])
to_j = int(net.pipe.at[idx, 'to_junction'])
mdot = row.get('mdot_kg_per_s', 0.0)
mdot_per_j[from_j] -= mdot
mdot_per_j[to_j] += mdot
for j in junctions:
dP = (mdot_per_j[j] / C[j]) * dt
newP = pressures[j][-1] + dP
pressures[j].append(newP)
return times.tolist(), {str(j): pressures[j] for j in junctions}