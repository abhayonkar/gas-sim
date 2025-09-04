# Data Manager - Handles data storage and retrieval
import sqlite3
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DataManager:
    """Manages data storage and retrieval"""
    
    def __init__(self, db_path="gas_simulator/data/pipeline.db"):
        self.db_path = db_path
        self.init_database()
        logger.info("Data Manager initialized")
    
    def init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create simulation data table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simulation_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    network_data TEXT,
                    sensor_data TEXT,
                    plc_outputs TEXT
                )
            ''')
            
            # Create alarms table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    plc_id TEXT,
                    alarm_id TEXT,
                    severity TEXT,
                    message TEXT,
                    acknowledged INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
    
    def store_simulation_data(self, timestamp: datetime, network_data: Dict[str, Any], 
                            sensor_data: Dict[str, Any], plc_outputs: Dict[str, Any]):
        """Store simulation data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO simulation_data (timestamp, network_data, sensor_data, plc_outputs)
                VALUES (?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                json.dumps(network_data),
                json.dumps(sensor_data),
                json.dumps(plc_outputs)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Data storage error: {e}")
    
    def get_historical_data(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get historical simulation data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute('''
                SELECT timestamp, network_data, sensor_data, plc_outputs
                FROM simulation_data
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1000
            ''', (cutoff_time,))
            
            rows = cursor.fetchall()
            conn.close()
            
            historical_data = []
            for row in rows:
                historical_data.append({
                    'timestamp': row[0],
                    'network_data': json.loads(row[1]) if row[1] else {},
                    'sensor_data': json.loads(row[2]) if row[2] else {},
                    'plc_outputs': json.loads(row[3]) if row[3] else {}
                })
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Historical data retrieval error: {e}")
            return []