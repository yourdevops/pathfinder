"""
Simple Flask application with health endpoint.
Template variables:
  - {{ service_name }}: Name of the deployed service
"""

import os
from flask import Flask, jsonify

app = Flask(__name__)

# Configuration from environment
PORT = int(os.environ.get("PORT", 8080))
SERVICE_NAME = os.environ.get("SERVICE_NAME", "{{ service_name }}")


@app.route("/")
def hello():
    """Root endpoint returning hello message."""
    return jsonify({
        "message": "Hello, World!",
        "service": SERVICE_NAME
    })


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
