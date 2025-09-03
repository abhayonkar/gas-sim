# ids/app.py
import socket
import struct
import time
from datetime import datetime
import psycopg2
import json

class PipelineIDS:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="pipeline", user="simulator", 
            password="simulator", host="db"
        )
        
        # Known normal patterns
        self.normal_patterns = {
            'flow_rate': {'min': 0, 'max': 10000},
            'pressure': {'min': 1000, 'max': 7000},
            'command_frequency': {'max': 10}  # Max commands per minute
        }
        
        self.command_log = []
    
    def monitor_modbus(self):
        # Create a raw socket to capture Modbus traffic
        try:
            s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
        except:
            print("IDS requires elevated privileges")
            return
        
        while True:
            packet, addr = s.recvfrom(65535)
            
            # Extract Ethernet header
            eth_length = 14
            eth_header = packet[:eth_length]
            eth = struct.unpack('!6s6sH', eth_header)
            eth_protocol = socket.ntohs(eth[2])
            
            # Check for IP packets
            if eth_protocol == 8:
                # Parse IP header
                ip_header = packet[eth_length:eth_length+20]
                iph = struct.unpack('!BBHHHBBH4s4s', ip_header)
                version_ihl = iph[0]
                ihl = version_ihl & 0xF
                iph_length = ihl * 4
                protocol = iph[6]
                s_addr = socket.inet_ntoa(iph[8])
                d_addr = socket.inet_ntoa(iph[9])
                
                # Check for TCP packets
                if protocol == 6:
                    t = iph_length + eth_length
                    tcp_header = packet[t:t+20]
                    tcph = struct.unpack('!HHLLBBHHH', tcp_header)
                    source_port = tcph[0]
                    dest_port = tcph[1]
                    
                    # Check for Modbus TCP (port 502)
                    if dest_port == 502 or source_port == 502:
                        # Extract Modbus data
                        modbus_data = packet[t+20:]
                        if modbus_data:
                            self.analyze_modbus(modbus_data, s_addr, d_addr)
            
            time.sleep(0.001)
    
    def analyze_modbus(self, data, source_ip, dest_ip):
        # Simple Modbus analysis
        if len(data) < 8:
            return
        
        # Extract Modbus fields
        transaction_id = data[0:2]
        protocol_id = data[2:4]
        length = int.from_bytes(data[4:6], byteorder='big')
        unit_id = data[6]
        function_code = data[7]
        
        # Check for suspicious function codes
        suspicious_functions = [5, 6, 15, 16]  # Write operations
        if function_code in suspicious_functions:
            # Log the command
            command_time = datetime.now()
            self.command_log.append({
                'time': command_time,
                'source_ip': source_ip,
                'function_code': function_code,
                'data': data.hex()
            })
            
            # Check command frequency
            recent_commands = [cmd for cmd in self.command_log 
                              if (command_time - cmd['time']).total_seconds() < 60]
            if len(recent_commands) > self.normal_patterns['command_frequency']['max']:
                self.alert(f"High frequency of Modbus commands from {source_ip}")
            
            # If it's a write to a critical register, alert
            if function_code in [6, 16]:  # Write operations
                # Extract address (simplified)
                if function_code == 6:
                    address = int.from_bytes(data[8:10], byteorder='big')
                else:
                    address = int.from_bytes(data[8:10], byteorder='big')
                
                # Check if it's a critical register
                if address in [0, 1, 2]:  # Example critical addresses
                    self.alert(f"Write to critical register {address} from {source_ip}")
    
    def alert(self, message):
        print(f"IDS ALERT: {message}")
        # Log to database
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO ids_alerts (timestamp, message) VALUES (%s, %s)",
            (datetime.now(), message)
        )
        self.conn.commit()
        cur.close()
        
        # In a real system, you might also send an email or notification

if __name__ == "__main__":
    ids = PipelineIDS()
    ids.monitor_modbus()