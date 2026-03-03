import os
import json
import re
import requests
import smtplib
from email.message import EmailMessage
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- Environment Config ---
THEHIVE_URL = os.getenv("THEHIVE_URL", "http://10.181.218.119:9000/api/alert")
THEHIVE_API_KEY = os.getenv("THEHIVE_API_KEY")

VT_API_KEY = os.getenv("VT_API_KEY")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

HEADERS_THEHIVE = {
    "Authorization": f"Bearer {THEHIVE_API_KEY}",
    "Content-Type": "application/json"
}

# --- Send HTML Email ---
def send_email(subject: str, body: str):
    try:
        msg = EmailMessage()
        msg['From'] = EMAIL_USER
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.set_content(body, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"[+] Email sent to {EMAIL_TO}")

    except Exception as e:
        print(f"[!] Failed to send email: {e}")

# --- VirusTotal Query ---
def query_virustotal(sha256_hash: str) -> dict:
    url = f"https://www.virustotal.com/api/v3/files/{sha256_hash}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json().get("data", {}).get("attributes", {})
            stats = data.get("last_analysis_stats", {})

            return {
                "malicious": stats.get("malicious", 0),
                "suspicious": stats.get("suspicious", 0),
                "undetected": stats.get("undetected", 0),
                "harmless": stats.get("harmless", 0)
            }
        else:
            print(f"[!] VT API returned {response.status_code}")
            return {}

    except Exception as e:
        print(f"[!] VT query error: {e}")
        return {}

# --- Wazuh Webhook ---
@app.route("/wazuh-alert", methods=["POST"])
def wazuh_alert():
    try:
        alert = request.json
        print("=== WAZUH ALERT RECEIVED ===")
        print(json.dumps(alert, indent=4))

        agent_name = alert["all_fields"]["agent"]["name"]
        rule_desc = alert["all_fields"]["rule"]["description"]
        severity_level = alert["all_fields"]["rule"]["level"]
        mitre_ids = alert["all_fields"]["rule"].get("mitre", {}).get("id", [])
        full_log = alert["all_fields"].get("full_log", "")
        event_id = alert["all_fields"]["id"]

        sha256_match = re.search(r"SHA256=([A-Fa-f0-9]{64})", full_log)
        sha256_value = sha256_match.group(1) if sha256_match else None

        if severity_level >= 12:
            severity_label = "HIGH"
            thehive_severity = 3
        elif severity_level >= 7:
            severity_label = "MEDIUM"
            thehive_severity = 2
        else:
            severity_label = "LOW"
            thehive_severity = 1

        title = f"[{severity_label}] {rule_desc} on {agent_name}"

        description = json.dumps(alert, indent=4)

        vt_summary = {}
        if sha256_value:
            vt_summary = query_virustotal(sha256_value)

            if vt_summary:
                description += "\n\nVirusTotal Summary:\n"
                description += json.dumps(vt_summary, indent=4)

        payload = {
            "title": title,
            "description": description,
            "type": "internal",
            "source": "Wazuh",
            "sourceRef": str(event_id),
            "severity": thehive_severity,
            "tlp": 2,
            "pap": 2,
            "tags": mitre_ids
        }

        response = requests.post(THEHIVE_URL, headers=HEADERS_THEHIVE, json=payload)
        print("=== TheHive response ===")
        print(response.text)

        if sha256_value and response.status_code in (200, 201):
            alert_id = response.json().get("id")

            artifact_payload = {
                "dataType": "hash",
                "data": sha256_value,
                "message": "SHA256 extracted automatically from Wazuh alert",
                "tlp": 2
            }

            requests.post(
                f"{THEHIVE_URL}/{alert_id}/artifact",
                headers=HEADERS_THEHIVE,
                json=artifact_payload
            )

        email_body = f"""
        <h2>{title}</h2>
        <p><b>Agent:</b> {agent_name}</p>
        <p><b>Severity:</b> {severity_label}</p>
        <p><b>Rule:</b> {rule_desc}</p>
        <p><b>SHA256:</b> {sha256_value if sha256_value else "N/A"}</p>
        """

        if vt_summary:
            email_body += f"""
            <h3>VirusTotal Results</h3>
            <ul>
                <li>Malicious: {vt_summary.get("malicious", 0)}</li>
                <li>Suspicious: {vt_summary.get("suspicious", 0)}</li>
                <li>Undetected: {vt_summary.get("undetected", 0)}</li>
                <li>Harmless: {vt_summary.get("harmless", 0)}</li>
            </ul>
            """

        send_email(f"Wazuh Alert - {severity_label}", email_body)

        return jsonify({"status": "processed"}), 200

    except Exception as e:
        print(f"[!] Error processing alert: {e}")
        return jsonify({"status": "error"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
