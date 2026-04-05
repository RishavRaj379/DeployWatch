# Dummy backend for hackathon evaluator

from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.get("/users")
def users():
    return jsonify([]), 200

@app.get("/urls")
def urls():
    return jsonify([]), 200

@app.get("/events")
def events():
    return jsonify([]), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
