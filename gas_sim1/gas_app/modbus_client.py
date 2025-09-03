# flask_app/modbus_client.py
from pymodbus.client.sync import ModbusTcpClient
import os

OPENPLC_HOST = os.getenv("OPENPLC_HOST", "localhost")
OPENPLC_PORT = int(os.getenv("OPENPLC_PORT", 502))

class PLCClient:
    def __init__(self, host=None, port=None):
        self.host = host or OPENPLC_HOST
        self.port = port or OPENPLC_PORT
        self.client = ModbusTcpClient(self.host, port=self.port)

    def connect(self):
        return self.client.connect()

    def close(self):
        self.client.close()

    def write_coil(self, addr:int, value:bool, unit:int=1):
        rr = self.client.write_coil(addr, value, unit=unit)
        return rr

    def read_coil(self, addr:int, count:int=1, unit:int=1):
        rr = self.client.read_coils(addr, count, unit=unit)
        if rr and hasattr(rr, 'bits'):
            return rr.bits
        return None

    def write_register(self, addr:int, value:int, unit:int=1):
        rr = self.client.write_register(addr, value, unit=unit)
        return rr

    def read_register(self, addr:int, count:int=1, unit:int=1):
        rr = self.client.read_holding_registers(addr, count, unit=unit)
        if rr and hasattr(rr, 'registers'):
            return rr.registers
        return None


# modbus_client.py
import os
from pymodbus.client.sync import ModbusTcpClient


OPENPLC_HOST = os.getenv('OPENPLC_HOST', 'localhost')
OPENPLC_PORT = int(os.getenv('OPENPLC_PORT', 502))


class PLCClient:
def __init__(self, host=None, port=None):
self.host = host or OPENPLC_HOST
self.port = port or OPENPLC_PORT
self.client = ModbusTcpClient(self.host, port=self.port)


def connect(self):
return self.client.connect()


def close(self):
self.client.close()


def write_coil(self, addr: int, value: bool, unit: int = 1):
rr = self.client.write_coil(addr, value, unit=unit)
return rr


def read_coil(self, addr: int, count: int = 1, unit: int = 1):
rr = self.client.read_coils(addr, count, unit=unit)
if rr and hasattr(rr, 'bits'):
return rr.bits
return None


def write_register(self, addr: int, value: int, unit: int = 1):
rr = self.client.write_register(addr, value, unit=unit)
return rr


def read_register(self, addr: int, count: int = 1, unit: int = 1):
rr = self.client.read_holding_registers(addr, count, unit=unit)
if rr and hasattr(rr, 'registers'):
return rr.registers
return None