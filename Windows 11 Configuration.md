# 🖥 Windows 11 Endpoint Configuration

### Sysmon + Wazuh Agent Telemetry Pipeline
---
## 1️⃣ Installing Sysmon

Sysmon (System Monitor) provides deep Windows telemetry including:

- Process creation

- Network connections

- File creation time changes

- Registry modifications

- Driver loads

- DNS queries

> Without Sysmon, Wazuh only collects basic Windows event logs.
----

### Step 1 — Download Sysmon

- Download from Microsoft Sysinternals:

https://learn.microsoft.com/en-us/sysinternals/downloads/sysmon

![Sysmon Install 1](doc/screenshots/sysmon%20install%201.png)

- Extract the zip file.

### Step 2 — Download a Sysmon Configuration File

We used Olaf Hartong configuration:

[https://github.com/SwiftOnSecurity/sysmon-config](https://github.com/olafhartong/sysmon-modular)

- Scroll down and find sysmonconfig.xml
- open and download the RAW file to the same folder you extracted Sysmon to

![Sysmon Install 4](doc/screenshots/sysmon%20install%204.png)

> This configuration filters noise and focuses on high-value events.

### Step 3 — Install Sysmon

- Open PowerShell as Administrator inside the Windows 11 VM.

- Navigate to the folder where Sysmon was extracted:

```powershell
cd C:\Users\<username>\Downloads\Sysmon
```

- Install with configuration:

```powershell
.\Sysmon64.exe -i sysmonconfig-export.xml
```
![Sysmon Install 9](doc/screenshots/sysmon%20install%209.png)

Expected output:

```Sysmon installed.```

```SysmonDrv installed.```

```Sysmon service started.```

![Sysmon Install 10](doc/screenshots/sysmon%20install%2010.png)

### Step 4 — Verify Installation

- Open Event Viewer:

Applications and Services Logs
  → Microsoft
    → Windows
      → Sysmon
        → Operational

- You should immediately see events such as:

Event ID 1 — Process Creation

Event ID 3 — Network Connection

Event ID 7 — Image Loaded

![Sysmon Install 13](doc/screenshots/sysmon%20install%2013.png)

## 2️⃣ Wazuh Agent Setup

### Deploy the Agent on FROM your Windows endpoint

- In the Wazuh dashboard click Deploy new agent
- Select Windows as the operating system
- Enter the Wazuh VM's IP address as the server address
- Copy and run the generated PowerShell command at the bottom on the Windows 11 VM


![Windows configuration Wazah agent download and install](doc/screenshots/Windows%20configuration%20Wazah%20agent%20download%20and%20install.png)
![wazuh agent started on win11 vm](doc/screenshots/wazuh%20agent%20started%20on%20win11%20vm.png)

## 3️⃣ Configure Wazuh Agent to Ingest Sysmon Logs

Sysmon logs are written to: ```Microsoft-Windows-Sysmon/Operational```

We must tell the Wazuh agent to monitor this channel.

- Edit Wazuh Agent Configuration

File location:

C:\Program Files (x86)\ossec-agent\ossec.conf

![wazuh configuration1](doc/screenshots/wazuh%20configuration1.png)
![wazuh configuration2](doc/screenshots/wazuh%20configuration2.png)
- Add inside <ossec_config>:

```
<localfile>
  <location>Microsoft-Windows-Sysmon/Operational</location>
  <log_format>eventchannel</log_format>
</localfile>
```
![wazuh configuration5](doc/screenshots/wazuh%20configuration5.png)

- Save the file.

- Restart Wazuh Agent

- Open Services:
![wazuh configuration6 restart the service](doc/screenshots/wazuh%20configuration6%20restart%20the%20service.png)
  

```services.msc```

- Restart: Wazuh Agent

Or via PowerShell:

```Powershell
Restart-Service -Name wazuh
```

## 4️⃣ Validate Telemetry in Wazuh Dashboard

- Go to:

Wazuh Dashboard → Security Events

- Search for: sysmon in the DQL search

- You should now see:

Process creation logs

PowerShell execution

Network connections

Suspicious binaries

![wazuh configuration8 type sysmon and expand on of the events](doc/screenshots/wazuh%20configuration8%20type%20sysmon%20and%20expand%20on%20of%20the%20events.png)

- Open one of the logs and scroll down and double check the provider name.
- You should see ```Microsoft-Windows-Sysmon```

![wazuh configuration9 final check](doc/screenshots/wazuh%20configuration9%20final%20check.png)

## 5️⃣ Time to get naughty 😈

### Under contstruction....

## 6️⃣ Full Telemetry Flow Confirmed
```
Windows 11 VM
   ↓
Sysmon Event Logging
   ↓
Wazuh Agent (eventchannel ingestion)
   ↓
Wazuh Manager
   ↓
Indexer
   ↓
Dashboard
   ↓
TheHive (alerts)
   ↓
Flask Automation
```

### 🔎 Adding Sysmon transforms this lab from:

“Basic SIEM lab”

Into:

“Detection engineering + SOC automation pipeline”


This demonstrates:

- Endpoint telemetry engineering

- Log source integration

- Agent configuration

- Detection pipeline validation
