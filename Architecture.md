# 🏗️ SOAR Lab Architecture & Alert Workflow

This section illustrates the design and flow of our **SOAR Automation Lab**, showing how alerts move from detection to actionable intelligence.

---

## 🌐 System Overview

The lab integrates the following components:

| Component       | Role |
|-----------------|------|
| **Wazuh**       | Collects and generates security alerts from endpoints and servers. |
| **Flask App**   | Acts as the automation engine: receives Wazuh alerts, enriches them with VirusTotal, and triggers TheHive cases & email notifications. |
| **TheHive**     | Centralized security incident management system where alerts are converted into cases. |
| **VirusTotal**  | Provides enrichment and threat intelligence for file hashes detected in alerts. |
| **Email (SMTP)**| Notifies analysts in real-time about new alerts, including enrichment data. |

---

## 🔄 Alert Flow

1. **Detection** – Wazuh identifies suspicious activity (e.g., Mimikatz execution, unusual login patterns).  
2. **Alert Forwarding** – Wazuh POSTs the alert JSON to the Flask automation endpoint (`/wazuh-alert`).  
3. **Processing & Enrichment**  
   - Flask extracts key fields from the alert: agent name, rule description, severity, SHA256 hashes, and MITRE technique IDs.  
   - SHA256 hashes are queried against **VirusTotal** for additional context (malicious, benign, or unknown).  
4. **Case Creation** – Flask sends the processed alert to **TheHive**, automatically creating a case with enriched details.  
5. **Analyst Notification** – Flask sends an email summary to the designated analyst email with alert details, VirusTotal results, and MITRE mapping.  
6. **Optional Investigation** – Security analysts can review TheHive case, check enrichment, and start incident response if necessary.

---

## 🖼️ Architecture Diagram

```text
         +-----------------+              +---------------------------+
         |                 |              |                           |
         |     Wazuh       |  <---------- |   Windows 11              |
         |                 |              |   sysmon / Wazuh agent    |
         |                 |              |   Mimikatz                |
         +--------+--------+              +---------------------------+
                  |
                  | Alert JSON
                  v
         +--------+--------+
         |                 |
         |    Flask App    |
         |                 |
         +----+-------+----+
              |       |
      VirusTotal API  | Email SMTP
              |       v
              |   +---+---+
              |   |       |
              +-->| Email |
              |   |       |
              |   +-------+
              |
              v
         +----+----+
         |         |
         | TheHive |
         |         |
         +---------+
