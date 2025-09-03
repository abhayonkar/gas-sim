from flask import Flask, render_template, request, redirect
import requests

PROCESS_URL = "http://process-sim:7000"

app = Flask(__name__)

@app.route("/")
def home():
    s = requests.get(f"{PROCESS_URL}/api/state").json()
    return render_template("home.html", state=s)

@app.route("/setpoints", methods=["POST"])
def setpoints():
    payload = {
        "compressor_ratios": [float(request.form.get("cr0", 1.0))],
        "valve_openings": [float(request.form.get("v0", 1.0))]
    }
    requests.post(f"{PROCESS_URL}/api/setpoints", json=payload)
    return redirect("/")

@app.route("/scenario", methods=["POST"])
def scenario():
    scn = {"event": request.form.get("event"), "id": int(request.form.get("id", 0))}
    requests.post(f"{PROCESS_URL}/api/scenario", json=scn)
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
