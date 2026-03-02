#!/usr/bin/env python3
"""
Small web UI for the weather agent. Run with: python app.py
Open http://127.0.0.1:5000 in the browser.
"""

from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from flask import Flask, render_template, request, jsonify

from agent import run_agent

app = Flask(__name__, template_folder="web")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True, silent=True) or request.form
    message = (data.get("message") or data.get("question") or "").strip()
    if not message:
        return jsonify({"response": "Please enter a question."}), 400
    try:
        response = run_agent(message)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"Error: {e}"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
