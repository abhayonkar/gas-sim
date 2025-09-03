from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.device import ModbusDeviceIdentification
from threading import Lock
from collections import defaultdict

lock = Lock()
# Example: holding registers map pressures (kPa*10), flows (kg/s*100), actuators (%*100)
HR_SIZE = 20000
hr = ModbusSequentialDataBlock(0, *HR_SIZE)
context = ModbusServerContext(slaves=ModbusSlaveContext(hr=hr), single=True)

def write_registers_snapshot(snap):
    with lock:
        for i, p in enumerate(snap["pressures"]):  # index to register allocation
            hr.setValues(i, [int(p*10)])
        base = 5000
        for i, q in enumerate(snap["flows"]):
            hr.setValues(base+i, [int(q*100)])
        base = 10000
        for i, u in enumerate(snap["actuators"]):
            hr.setValues(base+i, [int(u*100)])

def start_modbus_server():
    identity = ModbusDeviceIdentification()
    identity.VendorName = "ProcessSim"
    StartTcpServer(context, address=("0.0.0.0", 5020), identity=identity)
