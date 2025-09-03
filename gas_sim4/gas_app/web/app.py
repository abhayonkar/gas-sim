# web/app.py
from flask import Flask, render_template, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime, timedelta

app = Flask(__name__)

def get_db_connection():
    return psycopg2.connect(
        dbname="pipeline", user="simulator", 
        password="simulator", host="db",
        cursor_factory=RealDictCursor
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/network')
def get_network_data():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get latest data for all edges
    cur.execute("""
        SELECT DISTINCT ON (edge_id) 
            edge_id, flow, from_pressure, to_pressure, timestamp
        FROM pipeline_data 
        ORDER BY edge_id, timestamp DESC
    """)
    
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify(data)

@app.route('/api/history/<edge_id>')
def get_history(edge_id):
    hours = request.args.get('hours', 24)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT timestamp, flow, from_pressure, to_pressure
        FROM pipeline_data 
        WHERE edge_id = %s AND timestamp > %s
        ORDER BY timestamp
    """, (edge_id, datetime.now() - timedelta(hours=int(hours))))
    
    data = cur.fetchall()
    cur.close()
    conn.close()
    
    return jsonify(data)

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    # In a real implementation, this would send commands to the SCADA system
    print(f"Control command received: {data}")
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)