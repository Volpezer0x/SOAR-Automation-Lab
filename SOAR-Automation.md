# 🤖 SOAR Automation Pipeline
### Flask · Wazuh · TheHive · VirusTotal · Gmail SMTP
> So here it is, the beating heart of this lab.
>  
> A fully functional, Python-built Security Orchestration, Automation and Response (SOAR) pipeline — built from scratch on Ubuntu Server. Alerts flow from a Windows endpoint through Sysmon → Wazuh → Flask → VirusTotal → TheHive → SOC Email, end-to-end with no manual intervention.

---

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Lab Environment](#lab-environment)
- [Phase 1 — Network Configuration](#phase-1--network-configuration)
- [Phase 2 — Python Environment Setup](#phase-2--python-environment-setup)
- [Phase 3 — TheHive Organisation & API Setup](#phase-3--thehive-organisation--api-setup)
- [Phase 4 — Flask Webhook Server](#phase-4--flask-webhook-server)
- [Phase 5 — Wazuh Integration](#phase-5--wazuh-integration)
- [Phase 6 — VirusTotal Enrichment](#phase-6--virustotal-enrichment)
- [Phase 7 — Dynamic Alert Titles & SHA256 Extraction](#phase-7--dynamic-alert-titles--sha256-extraction)
- [Phase 8 — SOC Email Notifications](#phase-8--soc-email-notifications)
- [Phase 9 — Security Hardening (.env + .gitignore)](#phase-9--security-hardening-env--gitignore)
- [app.py — Full Code Walkthrough](#apppy--full-code-walkthrough)
- [Troubleshooting Log](#troubleshooting-log)
- [Results](#results)
- [Skills Demonstrated](#skills-demonstrated)

---

## Architecture Overview

```
Windows Endpoint (Sysmon)
         ↓
   Wazuh Agent
         ↓
   Wazuh Manager  ──────────────────────────────────────────────┐
         ↓                                                       │
  ossec.conf integration block                                   │
  (flask-webhook / custom-webhook / shuffle)                     │
         ↓                                                       │
  Flask Automation Server (:5000/wazuh-alert)                   │
         ↓                                                       │
  Parse JSON → Extract Fields                                    │
  (agent, rule, severity, SHA256, MITRE IDs)                    │
         ↓                ↓                                      │
  VirusTotal API    TheHive Alert API                            │
  (hash lookup)     (case creation)                              │
         ↓                ↓                                      │
  VT Result appended to alert description                        │
         ↓                                                       │
  Gmail SMTP → SOC Email Alert                                   │
  (Subject, Severity, SHA256, VT score, MITRE, JSON body)        │
                                                                  │
  └──────────────────────────────────────────────────────────────┘
```

---

## Lab Environment

| Component | Details |
|---|---|
| Automation Server OS | Ubuntu Server 24.04 (Noble) |
| Python Version | Python 3.12.3 |
| Automation Server IP | 10.181.218.100 |
| TheHive IP | 10.181.218.119:9000 |
| Wazuh Manager IP | 10.181.218.113 |
| Flask Port | 5000 |
| Key Libraries | `flask`, `requests`, `smtplib`, `python-dotenv` |
| Webhook Endpoint | `/wazuh-alert` (POST) |

---

## Phase 1 — Network Configuration

The automation server started with a DHCP-assigned IP. For the webhook to be reliably reachable by the Wazuh manager, a **static IP** was required.

### Step 1.1 — Check current IP assignment

```bash
ip a
```

![Set Static IP 1](doc/screenshots/python%20automation-%20set%20static%20ip%201.png)

### Step 1.2 — Edit the Netplan config

```bash
sudo nano /etc/netplan/00-installer-config.yaml
```

Initial config using the deprecated `gateway4` key:

![Set Static IP 2](doc/screenshots/python%20automation-%20set%20static%20ip%202.png)

### Step 1.3 — Fix deprecated `gateway4` warning

Netplan warned that `gateway4` is deprecated. The config was updated to use the `routes:` block instead:

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp0s3:
      dhcp4: no
      addresses:
        - 10.181.218.100/24
      routes:
        - to: default
          via: 10.181.218.152
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

![Set Static IP 3](doc/screenshots/python%20automation-%20set%20static%20ip%203.png)

Lock permissions to suppress the "too open" warning:

```bash
sudo chmod 600 /etc/netplan/00-installer-config.yaml
sudo netplan apply
```

![Set Static IP 4](doc/screenshots/python%20automation-%20set%20static%20ip%204.png)

### Step 1.4 — Fix conflicting cloud-init network config

The `50-cloud-init.yaml` file was overriding the static config on reboot. It was disabled permanently:

```bash
sudo nano /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg
```

Content added:
```
network: {config: disabled}
```

The conflicting file was then removed:

```bash
sudo rm /etc/netplan/50-cloud-init.yaml
sudo netplan generate
sudo netplan apply
sudo reboot
```

![Gateway Issue Fix Config](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%20.png)
![Gateway Issue Fix Config 2](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%202%20.png)
![Gateway Issue Fix Config 3](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%203%20.png)
![Gateway Issue Fix Config 4](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%204%20.png)
![Gateway Issue Fix Config 5](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%205%20.png)
![Gateway Issue Fix Config 6](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%206%20.png)
![Gateway Issue Fix Config 7](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%207%20.png)

### Step 1.5 — Network confirmed

After reboot, the static IP held and external connectivity was verified:

```bash
ping 8.8.8.8
sudo apt update && sudo apt upgrade -y
```

![Network Configured Successfully](doc/screenshots/python%20automation-%20install%20python3%20cant%20connect-gateway%20issue%20fix%20config%208%20network%20configured%20successfully%20.png)

### Step 1.6 — Verify connectivity to lab hosts

```bash
ping 10.181.218.113   # Wazuh Manager
ping 10.181.218.119   # TheHive
```

![Connection Check All Good](doc/screenshots/python%20automation-%20connection%20check%20all%20good.png)

---

## Phase 2 — Python Environment Setup

### Step 2.1 — Install Python 3 and pip

```bash
sudo apt install python3 python3-pip -y
```

![Install Python3 1](doc/screenshots/python%20automation-%20install%20python3%201.png)

> **Issue encountered:** `Failed to fetch` errors on first attempt — caused by the gateway misconfiguration documented in Phase 1.

![Install Python3 Failed to Fetch](doc/screenshots/python%20automation-%20install%20python3%202%20failed%20to%20fetch.png)

After network fix, the install succeeded:

```bash
python3 --version   # Python 3.12.3
pip3 --version
```

![Install Python3 Success](doc/screenshots/python%20automation-%20install%20python3%20success%20%20.png)


### Step 2.2 — Fix IPv6 apt interference

`apt update` was timing out on IPv6 addresses. This was resolved by forcing IPv4:

```bash
sudo nano /etc/apt/apt.conf.d/99force-ipv4
```

Content added:
```
Acquire::ForceIPv4 "true";
```

![IPv6 Fix 1](doc/screenshots/python%20automation-%20install%20python3%20ipv6%20issue%20fix1%20.png)
![IPv6 Fix 2](doc/screenshots/python%20automation-%20install%20python3%20ipv6%20issue%20fix2%20.png)

### Step 2.3 — Flask install blocked by externally-managed environment

Running `pip3 install flask requests` failed on Ubuntu 24.04 with:

```
error: externally-managed-environment
```

Ubuntu 24.04 enforces PEP 668 — pip packages must not be installed system-wide.

![Flask Install Error 1](doc/screenshots/python%20automation-%20install%20python3%20flask%20install%20error1%20%20.png)
![Flask Install Error 2](doc/screenshots/python%20automation-%20install%20python3%20flask%20install%20error2%20%20.png)

### Step 2.4 — Resolve with a Python virtual environment

```bash
sudo apt install python3-venv -y
mkdir ~/automation
cd ~/automation
python3 -m venv venv
source venv/bin/activate
pip install flask requests
```

![Flask Install Error 3](doc/screenshots/python%20automation-%20install%20python3%20flask%20install%20error3%20%20.png)
![Venv Isolation 4](doc/screenshots/python%20automation-%20install%20python3%20flask%20install%20error4%20venv%20isolation%20%20.png)
![Venv Isolation 5](doc/screenshots/python%20automation-%20install%20python3%20flask%20install%20error5%20venv%20isolation%20%20.png)
![Flask Installed in Venv](doc/screenshots/python%20automation-%20install%20python3%20flask%20install%20error6%20venv%20isolation%20flask%20installed%20successfuly%20in%20venv%20%20.png)

### Step 2.5 — Building the webhook inside the venv

```bash
nano app.py
```

![Building Webhook in Venv 1](doc/screenshots/python%20automation-%20install%20python3%20building%20the%20webhook%20in%20venv%201%20%20.png)
![Building Webhook in Venv 2](doc/screenshots/python%20automation-%20install%20python3%20building%20the%20webhook%20in%20venv%202%20%20.png)

---

## Phase 3 — TheHive Organisation & API Setup

### Step 3.1 — Create organisation in TheHive

Navigate to **Administration → Organisations → +** and create a new organisation:

- **Name:** `SOAR-LAB`
- **Description:** `Python Automation`

![TheHive Setup 1](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%201%20%20.png)
![TheHive Setup 2](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%202%20%20.png)
![TheHive Setup 3](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%203%20%20.png)
### Step 3.2 — Create users

Two users were created under the `SOAR-LAB` organisation:

| Login | Type | Purpose |
|---|---|---|
| `soar@random.com` | Normal | Human analyst account |
| `flask@random.com` | Service | API integration account |

![TheHive Setup 4](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%204%20%20.png)
![TheHive Setup 5](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%205%20%20.png)

### Step 3.3 — Generate API key for flask service user

Click the eyeball icon to reveal the `flask@random.com` user, then click **Create API Key**:

![TheHive Setup 6 - Click Eyeball](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%206%20click%20the%20eyeball%20%20.png)
![TheHive Setup 7 - Create API Key](/doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%207%20create%20api%20key%20%20.png)

### Step 3.4 — Paste API key into app.py

![TheHive Setup 8 - Paste API Key](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%208%20paste%20in%20api%20key%20%20.png)

### Step 3.5 — Start the automation server

```bash
source venv/bin/activate
python app.py
```

![TheHive Setup 9 - Server Running](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%209%20automation%20server%20is%20up%20and%20running%20%20.png)

### Step 3.6 — POST test to confirm TheHive connectivity

```bash
curl -X POST http://10.181.218.100:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "hello from automation"}'
```

![TheHive Setup 10 - POST Test Success](doc/screenshots/python%20automation-%20setting%20up%20theHive%20accounts%20and%20api%2010%20POST%20test%20successful%20%20.png)

### Step 3.7 — Wazuh/TheHive API sanity check

```bash
curl -X GET http://10.181.218.119:9000/api/v1/status \
  -H "Authorization: Bearer QOlu7vyORsW3o3bZUdW9jc9/FzVNE5oH"
```

![TheHive Post Sanity Check](doc/screenshots/python%20automation%20thehive%20post%20sanity%20check.png)

---

## Phase 4 — Flask Webhook Server

### Initial webhook (connectivity test)

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("\n=== Received Alert From Wazuh ===")
    print(json.dumps(data, indent=4))
    return jsonify({"status": "received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

![Flask Configuration Final Cleanup](doc/screenshots/python%20automation%20flask%20configuration%20final%20cleanup.png)

### Upgraded to `/wazuh-alert` route with TheHive integration

The webhook route was renamed to `/wazuh-alert` and wired directly to TheHive's alert API:

![TheHive API and Wazuh Alerts](doc/screenshots/python%20automation-%20setting%20up%20theHive%20api%20and%20Wazuh%20alerts%20.png)

---

## Phase 5 — Wazuh Integration

### Step 5.1 — Edit ossec.conf on the Wazuh manager

```bash
sudo nano /var/ossec/etc/ossec.conf
```

An `<integration>` block was added pointing at the Flask server. The `<name>` field was iterated through several values before finding what works:

| Name tried | Result |
|---|---|
| `flask-webhook` | Not a built-in — Wazuh ignores unknown names silently |
| `custom-webhook` | Requires the integration script to exist in `/var/ossec/integrations/` |
| `shuffle` | ✅ Built-in to Wazuh — triggers correctly with a custom `hook_url` |

```xml
<integration>
  <name>shuffle</name>
  <hook_url>http://10.181.218.100:5000/wazuh-alert</hook_url>
  <alert_format>json</alert_format>
</integration>
```

![Wazuh Adding Custom Webhook](doc/screenshots/wazuh%20adding%20custom%20webhook.png)
![Wazuh Not Sending 1](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook.png)
![Wazuh Not Sending 2](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook%202.png)
![Wazuh Not Sending 3 - Use Custom](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook%203%20use%20custom%20not%20flask-webhook.png)
![Wazuh Not Sending 4 - Custom Not Installed](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook%204%20custom-webhook%20isn't%20installed%20in%20the%20first%20place...we'll%20use%20shuffle.png)
![Wazuh Not Sending 5 - Use Shuffle](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook%205%20custom-webhook%20isn't%20installed%20in%20the%20first%20place...we'll%20use%20shuffle.png)

### Step 5.2 — Restart Wazuh manager

```bash
sudo systemctl restart wazuh-manager
sudo tail -f /var/ossec/logs/ossec.log
```

### Step 5.3 — Alerts confirmed arriving at Flask

![Wazuh Success - Alerts Posting on Flask](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook%206%20success%20alerts%20are%20posting%20on%20flask.png)
![Wazuh - Mimikatz Alert on Flask](doc/screenshots/wazuh%20not%20sending%20anything%20to%20the%20webhook7%20mimikatz%20alert%20showing%20on%20flask.png)

---

## Phase 6 — VirusTotal Enrichment

### Step 6.1 — Get VirusTotal API key

Navigate to [virustotal.com](https://www.virustotal.com) → sign in → click your profile → **API Key**:

![VirusTotal Get API Key 1](doc/screenshots/Virustotal%20get%20your%20api%20key1.png)
![VirusTotal Get API Key 2](doc/screenshots/Virustotal%20get%20your%20api%20key2.png)

### Step 6.2 — Store VT API key in .bashrc

```bash
sudo nano ~/.bashrc
```

Add to the bottom:

```bash
export VT_API_KEY="YOUR_VIRUSTOTAL_API_KEY_HERE"
```

Reload:

```bash
source ~/.bashrc
echo $VT_API_KEY
```

![VirusTotal API Key Setup 1](doc/screenshots/python%20automation-%20virustotal%20setup%20api%20key1.png)
![VirusTotal API Key Setup 2](doc/screenshots/python%20automation-%20virustotal%20setup%20api%20key2.png)
![VirusTotal API Key Setup 3](doc/screenshots/python%20automation-%20virustotal%20setup%20api%20key3.png)

> **Note:** `sudo source ~/.bashrc` returns "command not found" — this is expected behaviour. Use `source ~/.bashrc` (without sudo) to reload environment variables in the current shell session.

### Step 6.3 — VirusTotal lookup function in app.py

```python
VT_API_KEY = os.getenv("VT_API_KEY", "")

def check_virustotal(sha256):
    if not VT_API_KEY or not sha256:
        return "VirusTotal → Not checked (no key or hash)"
    url = f"https://www.virustotal.com/api/v3/files/{sha256}"
    headers = {"x-apikey": VT_API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        stats = response.json()["data"]["attributes"]["last_analysis_stats"]
        return f"VirusTotal → Malicious: {stats['malicious']}, Suspicious: {stats['suspicious']}"
    elif response.status_code == 404:
        return "VirusTotal → Hash not found in VirusTotal"
    else:
        return f"VirusTotal → Error {response.status_code}"
```

### Step 6.4 — SHA256 and VT results confirmed in terminal

![VirusTotal SHA256 and VT Results on Terminal](doc/screenshots/python%20automation-%20virustotal%20sha256and%20vt%20results%20on%20terminal.png)

### Step 6.5 — VirusTotal results appear in TheHive case

![VirusTotal Successfully Shows on TheHive Case Alert](doc/screenshots/python%20automation-%20virustotal%20successfully%20showes%20up%20on%20thehive%20case%20alert.png)

---

## Phase 7 — Dynamic Alert Titles & SHA256 Extraction

### The problem: all alerts titled "Wazuh Alert"

Early versions sent every alert to TheHive with a static title, making triage impossible.

![TheHive Cases Before Dynamic Titles](doc/screenshots/TheHive%20cases%20before%20dynamic%20titles.png)

### The fix: extract rule description, agent name, and severity

```python
agent_name    = alert["all_fields"]["agent"]["name"]
rule_desc     = alert["all_fields"]["rule"]["description"]
severity_level = alert["all_fields"]["rule"]["level"]
mitre_ids     = alert["all_fields"]["rule"].get("mitre", {}).get("id", [])

# Extract SHA256 using regex
full_log = alert["all_fields"].get("full_log", "")
sha256_match = re.search(r"SHA256=([A-Fa-f0-9]{64})", full_log)
sha256_value = sha256_match.group(1) if sha256_match else None

# Map severity
if severity_level >= 12:
    severity_label = "HIGH"
    thehive_severity = 3
elif severity_level >= 7:
    severity_label = "MEDIUM"
    thehive_severity = 2
else:
    severity_label = "LOW"
    thehive_severity = 1

# Professional title
title = f"[{severity_label}] {rule_desc} on {agent_name}"
```

![Flask Pro Titles and SHA256 Extraction](doc/screenshots/python%20automation%20flask%20pro%20titles%20and%20sha256%20extraction%20.png)
![Flask Pro Titles and SHA256 Extraction 2](doc/screenshots/python%20automation%20flask%20pro%20titles%20and%20sha256%20extraction%202%20.png)

### Avoiding duplicate alerts in TheHive

Duplicate alerts were created due to retries from Wazuh. The `sourceRef` field was set to a unique value per alert to prevent TheHive from accepting duplicates:

![Avoiding TheHive Duplicates](doc/screenshots/python%20automation%20flask%20pro%20titles%20and%20sha256%20extraction%203%20avoiding%20thehive%20duplicates%20tightening%20and%20cleaning%20up%20more%20.png)

### Bug fix: `event_id is not defined`

A `NameError` was thrown because `event_id` was referenced in the `sourceRef` field before being defined. It was replaced with the alert's rule ID:

```python
"sourceRef": alert["all_fields"]["rule"]["id"],
```

![Event ID Not Defined Error](doc/screenshots/python%20automation%20flask%20pro%20titles%20and%20sha256%20extraction%204%20event_id%20not%20defined%20.png)

### Result: professional, actionable alert titles

![TheHive Cases After Dynamic Titles](doc/screenshots/TheHive%20cases%20after%20dynamic%20titles.png)

---

## Phase 8 — SOC Email Notifications

### Step 8.1 — Enable Gmail 2FA and create App Password

Gmail requires **2-Step Verification** to be active before an App Password can be generated.

Navigate to: `myaccount.google.com → Security → 2-Step Verification`

![Email Notification 1 - 2FA Confirmation](docs/screenshots/email%20notification%201%202fa%20confirmation.png)

Then navigate to: `myaccount.google.com/apppasswords`

Create a new app password named `SOAR-LAB`:

![Email Notification 2 - App Passwords Hidden](docs/screenshots/email%20notification%202%20go%20to%20app%20passwords%20its%20hidden.png)
![Email Notification 3 - App Password Generated](docs/screenshots/email%20notification%203%20you%20get%20your%20app%20password.png)

### Step 8.2 — Add credentials to .bashrc

```bash
nano ~/.bashrc
```

Add:

```bash
export VT_API_KEY="your_virustotal_api_key"
export EMAIL_USER="soar.lab.notifications@gmail.com"
export EMAIL_PASS="paste_the_16_char_app_password"
export THEHIVE_URL="http://10.181.218.119:9000/api/alert"
export THEHIVE_API_KEY="QOlu7vyORsW3o3bZUdW9jc9/FzVNE5oH"
export EMAIL_TO="soar.lab.notifications@gmail.com"
```

```bash
source ~/.bashrc
```

![Edit Bashrc Add Email Credentials](docs/screenshots/email%20notification%204%20edit%20your%20bashrc%20and%20add%20your%20email%20credentials.png)
![Edit Bashrc Keys and Emails](docs/screenshots/email%20notification%205%20edit%20bashrc%20and%20add%20your%20keys%20and%20emails.png)

### Step 8.3 — SMTP email function in app.py

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO   = os.getenv("EMAIL_TO")

def send_email_alert(subject, body):
    if not EMAIL_USER or not EMAIL_PASS:
        print("Email credentials not configured")
        return
    msg = MIMEMultipart()
    msg["From"]    = EMAIL_USER
    msg["To"]      = EMAIL_USER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print("[+] Email alert sent successfully")
    except Exception as e:
        print(f"[!] Email failed: {e}")
```

![Edit app.py SMTP 1](docs/screenshots/email%20notification%204%20edit%20app%20py%20to%20setup%20SMTP1.png)
![Edit app.py SMTP 2](docs/screenshots/email%20notification%204%20edit%20app%20py%20to%20setup%20SMTP2.png)
![Edit app.py SMTP 3](docs/screenshots/email%20notification%204%20edit%20app%20py%20to%20setup%20SMTP3.png)

### Step 8.4 — Email test confirmed working

Mimikatz was executed on the Windows endpoint. The pipeline triggered and the SOC alert email arrived in the inbox:

![Email Test Works](docs/screenshots/email%20notification%206%20email%20test%20works.png)

### Step 8.5 — Final email structure

The email body was refined to include all relevant fields:

- Alert title with severity prefix
- Agent hostname
- SHA256 hash
- VirusTotal direct link
- MITRE ATT&CK technique IDs
- Full raw Wazuh JSON

![Email Structure Check](docs/screenshots/email%20notification%207%20checking%20email%20structure.png)

### Step 8.6 — VirusTotal results enriched in email body

![Better VirusTotal Results in Email](docs/screenshots/email%20notification%208%20better%20virustotal%20results.png)
![Better Email Subject](docs/screenshots/email%20notification%209%20better%20email%20subject.png)
![Better VT Results in Email](docs/screenshots/email%20notification%2010%20better%20virustotal%20results%20in%20email.png)

### Final email format

```
Subject: [HIGH] Mimikatz Usage Detected on SOAR-Wazuh

Alert Title: [HIGH] Mimikatz Usage Detected on SOAR-Wazuh
Severity:    HIGH
Agent:       SOAR-Wazuh
SHA256:      61C0810A23580CF492A6BA4F7654566108331E7A4134C968C2D6A05261B2D8A1
VirusTotal:  https://www.virustotal.com/gui/file/<sha256>
MITRE IDs:   T1003

VirusTotal Result:
VirusTotal scan stats: {'malicious': 63, 'suspicious': 0, ...}

Full Wazuh Alert JSON:
{ ... }
```

---

## Phase 9 — Security Hardening (.env + .gitignore)

Before pushing to GitHub, all secrets were moved out of the source code and into environment files.

### Step 9.1 — Install python-dotenv

```bash
pip install python-dotenv
```

![Final Cleanup 1 - dotenv](docs/screenshots/python%20automation-%20FINAL%20CLEANUP1%20dotenv.png)

### Step 9.2 — Create .env file

```bash
nano .env
```

```ini
THEHIVE_URL=http://10.181.218.119:9000/api/alert
THEHIVE_API_KEY=your_thehive_api_key_here
VT_API_KEY=your_virustotal_api_key_here
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_16_char_app_password
EMAIL_TO=your_email@gmail.com
```

![Final Cleanup 2 - Create .env](docs/screenshots/python%20automation-%20FINAL%20CLEANUP2%20create%20and%20edit%20dotenv.png)

### Step 9.3 — Create .gitignore

```bash
nano .gitignore
```

```
.env
__pycache__/
venv/
*.pyc
```

![Final Cleanup 3 - Create .gitignore](docs/screenshots/python%20automation-%20FINAL%20CLEANUP3%20create%20and%20edit%20%20gitignore%20for%20saftey.png)
![Final Cleanup 4 - .gitignore Content](docs/screenshots/python%20automation-%20FINAL%20CLEANUP4%20create%20and%20edit%20%20gitignore%20for%20saftey.png)

### Step 9.4 — Initialise Git and verify .env is excluded

```bash
git init
git status
```

`git status` showed only `app.py`, `.gitignore`, and `app.py.bak` — the `.env` file was correctly excluded.

![Final Cleanup 5 - Git Init Success, .env Not Showing](docs/screenshots/python%20automation-%20FINAL%20CLEANUP5%20git%20initiated%20and%20%20env%20is%20not%20showing%20SUCCESS.png)

---

## app.py — Full Code Walkthrough

The final `app.py` is a clean, production-structured automation engine. All secrets are loaded from the `.env` file via `python-dotenv` — no hardcoded credentials anywhere in the codebase.

### 1. Imports & environment loading

```python
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
```

`load_dotenv()` reads the `.env` file at startup and injects all key-value pairs into the environment, making them available via `os.getenv()` throughout the script.

### 2. Configuration block

```python
# --- Environment Config ---
THEHIVE_URL     = os.getenv("THEHIVE_URL", "http://10.181.218.119:9000/api/alert")
THEHIVE_API_KEY = os.getenv("THEHIVE_API_KEY")
VT_API_KEY      = os.getenv("VT_API_KEY")
EMAIL_USER      = os.getenv("EMAIL_USER")
EMAIL_PASS      = os.getenv("EMAIL_PASS")
EMAIL_TO        = os.getenv("EMAIL_TO")

HEADERS_THEHIVE = {
    "Authorization": f"Bearer {THEHIVE_API_KEY}",
    "Content-Type": "application/json"
}
```

All six credentials are pulled from the environment. The TheHive authorization header is constructed once at startup and reused across all API calls.

### 3. HTML email function

```python
def send_email(subject: str, body: str):
    try:
        msg = EmailMessage()
        msg['From']    = EMAIL_USER
        msg['To']      = EMAIL_TO
        msg['Subject'] = subject
        msg.set_content(body, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"[+] Email sent to {EMAIL_TO}")

    except Exception as e:
        print(f"[!] Failed to send email: {e}")
```

Notable improvements over earlier iterations: uses `SMTP_SSL` on port 465 (implicit TLS — more secure than STARTTLS on 587), uses the standard `EmailMessage` class, and sends HTML-formatted email body for clean SOC inbox readability.

### 4. VirusTotal query function

```python
def query_virustotal(sha256_hash: str) -> dict:
    url = f"https://www.virustotal.com/api/v3/files/{sha256_hash}"
    headers = {"x-apikey": VT_API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data  = response.json().get("data", {}).get("attributes", {})
            stats = data.get("last_analysis_stats", {})

            return {
                "malicious":  stats.get("malicious",  0),
                "suspicious": stats.get("suspicious", 0),
                "undetected": stats.get("undetected", 0),
                "harmless":   stats.get("harmless",   0)
            }
        else:
            print(f"[!] VT API returned {response.status_code}")
            return {}

    except Exception as e:
        print(f"[!] VT query error: {e}")
        return {}
```

Returns a structured dict of the four key scan stats. Returns an empty dict on failure — this allows the downstream code to safely check `if vt_summary:` before trying to use the results.

### 5. Wazuh webhook route — the main pipeline

```python
@app.route("/wazuh-alert", methods=["POST"])
def wazuh_alert():
    try:
        alert = request.json
        print("=== WAZUH ALERT RECEIVED ===")
        print(json.dumps(alert, indent=4))

        # --- Extract fields ---
        agent_name     = alert["all_fields"]["agent"]["name"]
        rule_desc      = alert["all_fields"]["rule"]["description"]
        severity_level = alert["all_fields"]["rule"]["level"]
        mitre_ids      = alert["all_fields"]["rule"].get("mitre", {}).get("id", [])
        full_log       = alert["all_fields"].get("full_log", "")
        event_id       = alert["all_fields"]["id"]

        # --- SHA256 extraction via regex ---
        sha256_match = re.search(r"SHA256=([A-Fa-f0-9]{64})", full_log)
        sha256_value = sha256_match.group(1) if sha256_match else None

        # --- Severity mapping ---
        if severity_level >= 12:
            severity_label   = "HIGH"
            thehive_severity = 3
        elif severity_level >= 7:
            severity_label   = "MEDIUM"
            thehive_severity = 2
        else:
            severity_label   = "LOW"
            thehive_severity = 1

        title       = f"[{severity_label}] {rule_desc} on {agent_name}"
        description = json.dumps(alert, indent=4)

        # --- VirusTotal enrichment ---
        vt_summary = {}
        if sha256_value:
            vt_summary = query_virustotal(sha256_value)
            if vt_summary:
                description += "\n\nVirusTotal Summary:\n"
                description += json.dumps(vt_summary, indent=4)

        # --- TheHive alert creation ---
        payload = {
            "title":       title,
            "description": description,
            "type":        "internal",
            "source":      "Wazuh",
            "sourceRef":   str(event_id),
            "severity":    thehive_severity,
            "tlp":         2,
            "pap":         2,
            "tags":        mitre_ids
        }

        response = requests.post(THEHIVE_URL, headers=HEADERS_THEHIVE, json=payload)
        print("=== TheHive response ===")
        print(response.text)

        # --- Post SHA256 as artifact to TheHive alert ---
        if sha256_value and response.status_code in (200, 201):
            alert_id = response.json().get("id")

            artifact_payload = {
                "dataType": "hash",
                "data":     sha256_value,
                "message":  "SHA256 extracted automatically from Wazuh alert",
                "tlp":      2
            }

            requests.post(
                f"{THEHIVE_URL}/{alert_id}/artifact",
                headers=HEADERS_THEHIVE,
                json=artifact_payload
            )

        # --- Build and send HTML email ---
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
```

### Key design decisions

| Decision | Reason |
|---|---|
| Entire route wrapped in `try/except` | Flask won't crash on malformed Wazuh payloads — returns `500` gracefully |
| `sourceRef` set to `event_id` | Prevents TheHive from creating duplicate alerts for the same event |
| SHA256 artifact posted separately | Makes the hash directly observable in TheHive's Observables tab, not just buried in the description |
| `query_virustotal()` only called if SHA256 found | Avoids unnecessary API quota consumption on alerts without file hashes |
| HTML email body | Renders cleanly in Gmail — severity, agent, and VT results are immediately scannable |
| `SMTP_SSL` on port 465 | Implicit TLS — more reliable than STARTTLS for automated sending |

---

## Troubleshooting Log

| # | Issue | Root Cause | Fix |
|---|---|---|---|
| 1 | `Failed to fetch` on `apt install` | Incorrect gateway in Netplan config | Fixed gateway IP in `00-installer-config.yaml` |
| 2 | Netplan warnings on every apply | Deprecated `gateway4` key | Replaced with `routes:` block |
| 3 | Static IP reset after reboot | `50-cloud-init.yaml` was overriding config | Disabled cloud-init network management, deleted conflicting file |
| 4 | `apt update` IPv6 timeouts | Ubuntu 24 tries IPv6 first | Created `/etc/apt/apt.conf.d/99force-ipv4` |
| 5 | `pip3 install flask` blocked | Ubuntu 24.04 externally-managed-environment (PEP 668) | Created Python venv, installed inside it |
| 6 | Wazuh not sending to Flask | `flask-webhook` is not a recognised Wazuh integration name | Switched to `shuffle` (built-in), which accepts a custom `hook_url` |
| 7 | `custom-webhook` also failed | Script not present in `/var/ossec/integrations/` | Used `shuffle` instead |
| 8 | All TheHive alerts titled "Wazuh Alert" | Static title in early payload | Extracted `rule.description`, `agent.name`, `rule.level` dynamically |
| 9 | `NameError: name 'event_id' is not defined` | `event_id` variable referenced before assignment | Replaced `str(event_id)` with `alert["all_fields"]["rule"]["id"]` |
| 10 | `sudo source ~/.bashrc` fails | `source` is a shell built-in, not an executable | Use `source ~/.bashrc` without sudo |
| 11 | API keys visible in source code | Hard-coded credentials | Moved to `.env` file, loaded via `os.getenv()`, `.env` excluded via `.gitignore` |

---

## Results

### End-to-end pipeline confirmed

Running Mimikatz on the Windows endpoint triggered the full automation chain:

1. ✅ Sysmon detected process creation
2. ✅ Wazuh rule fired (rule level 15, MITRE T1003)
3. ✅ Wazuh POSTed alert JSON to Flask `/wazuh-alert`
4. ✅ Flask extracted agent name, rule description, SHA256, MITRE IDs
5. ✅ VirusTotal returned: `Malicious: 63, Suspicious: 0`
6. ✅ TheHive alert created with title `[HIGH] Mimikatz Usage Detected on SOAR-Wazuh`
7. ✅ SOC email delivered with full enrichment context

### Final email output

![Final Email Result Clean](docs/screenshots/python%20automation-%20FINAL%20CLEANUP6%20final%20email%20result%20CLEAN.png)

### TheHive alert queue — before vs after

| Before | After |
|---|---|
| Every alert titled "Wazuh Alert" | Descriptive titles with severity prefix, agent name, MITRE tag |

---

## Skills Demonstrated

| Skill | Applied |
|---|---|
| Security Orchestration (SOAR) | End-to-end automated detection-to-response pipeline |
| Python Development | Flask, requests, smtplib, regex, os.getenv |
| Linux System Administration | Netplan, cloud-init, apt, venv, systemctl |
| Threat Intelligence Integration | VirusTotal API v3, SHA256 hash lookup |
| Case Management Automation | TheHive 5 alert API, severity mapping, MITRE tagging |
| SOC Alert Engineering | Structured email with severity, IOCs, VT score, MITRE IDs |
| Secrets Management | `.env` file, `.gitignore`, `os.getenv()` — no hardcoded credentials |
| Troubleshooting | Documented and resolved 11 distinct technical obstacles |
| Git / Version Control | Repo initialisation, staged commits, `.env` exclusion verified |

---

> *Lab built and documented by a SOC analyst in training — every error, fix, and iteration included.*
