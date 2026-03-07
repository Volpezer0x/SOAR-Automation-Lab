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

---
### 🧬 Adding Sysmon transforms this lab from:

“Basic SIEM lab”

Into:

“Detection engineering + SOC automation pipeline”


This demonstrates:

- Endpoint telemetry engineering

- Log source integration

- Agent configuration

- Detection pipeline validation
---
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

### Mimikatz Detection Rule Setup in Wazuh

### Overview
Now that our Windows 11 envoroment is configured, lets introduce our endpoint threat.
I'll cover downloading Mimikatz for testing, enabling Wazuh archives, 
creating a custom detection rule, and troubleshooting the XML syntax errors 
encountered along the way.

---

### Step 1 — Download Mimikatz on the Windows 11 VM

Navigate to the official Mimikatz GitHub repository:
`https://github.com/gentilkiwi/mimikatz`

Scroll down in the README to the section that reads  
**"If you don't want to build it, binaries are available on..."**  
and click the releases link.

![Mimikatz GitHub](doc/screenshots/windows11%20config%202%20go%20to%20mimikatz-gentilkiwi-github.png)

![Mimikatz Releases Link](doc/screenshots/windows11%20config%204%20scroll%20down%20to%20if%20you%20dont%20want%20to%20build%20it%20and%20click%20the%20link.png)

Download `mimikatz_trunk.zip`. Windows Defender SmartScreen will flag it as 
unsafe — this is expected since Mimikatz is a known credential dumping tool 
used in penetration testing. Click **Keep anyway** to proceed.

![Defender Warning](doc/screenshots/windows11%20config%206%20defender%20will%20try%20to%20stop%20you%20but%20you%20select%20keep2.png)

Extract the zip, navigate to the `x64` folder and run:
```powershell
.\mimikatz.exe
```

![Mimikatz Running](doc/screenshots/windows11%20config%2010%20run%20mimikatz.png)

> **Note:** This is a controlled lab environment. Only run Mimikatz on systems 
> you own and have explicit permission to test on.

---

### Step 2 — Verify No Mimikatz Alerts in Wazuh Yet

Before creating any rules, search for `mimikatz` in the Wazuh Discovery tab 
under the `wazuh-alerts-*` index pattern. As expected, no results appear — 
Wazuh has no rule to detect it yet.

![No Mimikatz Alert](doc/screenshots/windows11%20config%2011%20no%20mimikatz%20alert%20on%20wazuh.png)

---

### Step 3 — Enable Wazuh Archives

By default Wazuh only indexes events that match an alert rule. To see ALL 
events including ones without rules we need to enable archives.

#### 3a — Backup and edit ossec.conf on the Wazuh VM

SSH into the Wazuh VM and backup the config first:

```bash
sudo cp /var/ossec/etc/ossec.conf ~/ossec_backup.conf
sudo nano /var/ossec/etc/ossec.conf
```

![Backup ossec.conf](doc/screenshots/windows11%20config%2012-%20on%20wazah-vm%20backup%20ossec%20conf.png)

Find the `<global>` section and change both `logall` and `logall_json` to `yes`:

```xml
<logall>yes</logall>
<logall_json>yes</logall_json>
```

![Edit logall](doc/screenshots/windows11%20config%2013%20change%20logall%20and%20logall_json%20to%20yes.png)

Restart the Wazuh manager to apply the changes:

```bash
sudo systemctl restart wazuh-manager.service
```

![Restart Wazuh Manager](doc/screenshots/windows11%20config%2014%20restart%20service%20after%20editing%20ossecconf.png)

#### 3b — Verify archive logs are being written

Switch to root and verify the archive files exist and are being populated:

```bash
sudo su
cd /var/ossec/logs/archives
ls -la
```

You should see `archives.json` and `archives.log` with recent timestamps.

![Check Archives](doc/screenshots/windows11%20config%2015%20check%20logs--archives.png)

#### 3c — Enable archives in Filebeat

Edit the Filebeat configuration:

```bash
nano /etc/filebeat/filebeat.yml
```

Find the `archives` section under the wazuh module and set `enabled` to `true`:

```yaml
filebeat.modules:
  - module: wazuh
    alerts:
      enabled: true
    archives:
      enabled: true
```

![Filebeat Archives](doc/screenshots/windows11%20config%2016%20change%20archives%20enabled%20to%20true.png)

Restart Filebeat to apply changes:

```bash
systemctl restart filebeat.service
```

![Restart Filebeat](doc/screenshots/windows11%20config%2017%20restart%20filebeat%20service.png)

---

### Step 4 — Create the wazuh-archives Index Pattern in Wazuh Dashboard

In the Wazuh dashboard navigate to:  
**Stack Management > Index Patterns**

You will see the existing default index patterns. Click **Create index pattern**.

![Index Patterns Page](doc/screenshots/windows11%20config%2019%20create%20index%20pattern.png)

Type `wazuh-archives-*` — you should see it match the source 
`wazuh-archives-4.x-<date>` confirming archives are flowing.

![Find Index Pattern](doc/screenshots/windows11%20config%2020%20find%20and%20match%20your%20index%20pattern-%20you%20should%20see%20thge%20index%20pattern%20source%20wazuh-archives.png)

Click **Next step**. Under **Time field** select `timestamp` from the dropdown.

![Select Timestamp](doc/screenshots/windows11%20config%2021%20select%20timestamp%20under%20time%20field%20and%20create%20index%20pattern.png)

![Create Index Pattern](doc/screenshots/windows11%20config%2022%20create%20index%20pattern.png)

The index pattern is now created with 747 fields mapped.

![Index Pattern Created](doc/screenshots/windows11%20config%2023%20index%20pattern%20created.png)

Switch to the Discovery tab, select `wazuh-archives-*` as the index pattern 
and confirm logs are appearing.

![Archives Logs Confirmed](doc/screenshots/windows11%20config%2024%20confirm%20new%20index%20pattern%20has%20logs.png)

---

### Step 5 — First Mimikatz Test Run (Archives Confirmation)

With archives now enabled, run Mimikatz again on the Windows 11 VM and search 
for `mimikatz` in the Discovery tab under `wazuh-archives-*`. This time you 
should see hits — the raw Sysmon events are being captured even without an 
alert rule yet.

![Run Mimikatz Again](doc/screenshots/windows11%20config%2025%20lets%20run%20mimikatz%20again%20and%20see%20what%20happens.png)

![Mimikatz Logs in Archives](doc/screenshots/windows11%20config%2026%20we%20got%20mimikatz%20logs.png)

This confirms the full pipeline is working:
```
Mimikatz runs → Sysmon captures it → Wazuh Agent forwards it → 
Wazuh Manager archives it → Filebeat ships it → Visible in Dashboard
```

---

### Step 6 — Create the Mimikatz Detection Rule

In the Wazuh dashboard navigate to **Rules > Manage rules files** and click 
**Custom rules**.

![Custom Rules](doc/screenshots/windows11%20config%2028%20select%20custom%20rules.png)

Click on `local_rules.xml` to open it in the editor.

![Edit local_rules.xml](doc/screenshots/windows11%20config%2029%20click%20and%20edit%20local_rules%20xml.png)
Add the following rule inside the existing `<group>` tags:

```xml
<rule id="100002" level="15">
    <if_group>sysmon_event1</if_group>
    <field name="win.eventdata.originalFileName" type="pcre2">(?i)mimikatz\.exe</field>
    <description>Mimikatz Usage Detected</description>
    <mitre>
        <id>T1003</id>
    </mitre>
</rule>
```

![Type Mimikatz Rule](doc/screenshots/windows11%20config%2030%20type%20in%20your%20new%20rule%20for%20mimikatz.png)

---

### Issue — XML Syntax Error When Saving Rule

**Symptom:**  
Clicking Save returned:
```
Error: Could not upload rule (1113) - XML syntax error
```

![XML Syntax Error](doc/screenshots/windows11%20config%2031%20syntax%20error.png)

**🔎 Root Cause:**  
The `<miter>` tag was used instead of the correct `<mitre>` tag — a simple 
typo. Wazuh's XML validator caught it and rejected the rule. Checking the 
journal logs on the Wazuh VM confirmed the manager was also failing to restart 
due to the same issue:

```
wazuh-analysisd: ERROR: Invalid option 'miter' for rule '100002'
wazuh-analysisd: CRITICAL: (1220): Error loading the rules
wazuh-analysisd: Configuration error. Exiting
```

![Journal Log Error](doc/screenshots/windows11%20config%2031%20syntax%20error%203%20check%20journal%20log.png)

**Fix:**  
Edit the rule file directly on the Wazuh VM, correct the typo, validate with 
`xmllint`, then restart the manager:

```bash
nano /var/ossec/etc/rules/local_rules.xml
xmllint --noout /var/ossec/etc/rules/local_rules.xml
systemctl restart wazuh-manager.service
```

![Fix and Validate](doc/screenshots/windows11%20config%2031%20syntax%20error%204%20xml%20modified%20tested%20and%20wazuh-manager%20restarts%20without%20errors.png)

Verify the manager starts cleanly with `active (running)` status:

```bash
systemctl status wazuh-manager
```

![Wazuh Manager Running](doc/screenshots/windows11%20config%2031%20syntax%20error%205%20wazuh-manager%20restarts%20without%20errors.png)

The corrected and working rule:

```xml
<rule id="100002" level="15">
    <if_group>sysmon_event1</if_group>
    <field name="win.eventdata.originalFileName" type="pcre2">(?i)mimikatz\.exe</field>
    <description>Mimikatz Usage Detected</description>
    <mitre>
        <id>T1003</id>
    </mitre>
</rule>
```

![Corrected Rule in Editor](doc/screenshots/windows11%20config%2031%20syntax%20error%207%20rule%20is%20showing%20on%20wazuh.png)

Confirm the rule now appears in the Wazuh Rules panel under Custom rules — 
rule ID `100002` with description **Mimikatz Usage Detected** and level **15**.

![Rule Confirmed in Wazuh](doc/screenshots/windows11%20config%2031%20syntax%20error%206%20rule%20is%20showing%20on%20wazuh.png)

> **Tip:** Always validate your XML with `xmllint` before saving rules. 
> A single typo will prevent the Wazuh manager from starting.

---

### Issue — Windows Defender Deleted Mimikatz

**Symptom:**  
After re-enabling Defender and attempting to run Mimikatz again for testing, 
the binary was silently deleted by Windows Defender. Running the command 
returned:

```
.\mimikatz.exe : The term '.\mimikatz.exe' is not recognized as the name 
of a cmdlet, function, script file, or operable program.
```

![Mimikatz Deleted](doc/screenshots/windows11%20config%2032%20windows%20removed%20my%20minikatz.png)

**Fix — Add a Defender Exclusion:**

Navigate to **Windows Security > Virus & threat protection > Manage settings > 
Add or remove exclusions**.

![Go to Defender Exclusions](doc/screenshots/windows11%20config%2033%20go%20to%20defender%20exclusions.png)

Click **Add an exclusion** and select **Folder**.

![Select Folder](doc/screenshots/windows11%20config%2034%20select%20folder.png)

Select the entire `C:\` drive as the exclusion path to prevent Defender from 
interfering with any lab tools.

![Exclude C Drive](doc/screenshots/windows11%20config%2035%20exlude%20the%20whole%20c%20drive%20lol.png)

> **Note:** Excluding the entire C:\ drive is only appropriate in an isolated 
> lab VM. Never do this on a production or personal machine.

Re-enable Real-time protection after adding the exclusion — Defender will now 
remain active for monitoring purposes but will not delete tools in the excluded 
path.

![Turn Defender Back On](doc/screenshots/windows11%20config%2036%20turn%20defender%20back%20on.png)

Re-download Mimikatz and confirm it runs without being deleted.

![Mimikatz Runs Without Deletion](doc/screenshots/windows11%20config%2037%20minikatz%20can%20now%20run%20without%20fear%20of%20delition.png)

---

### Step 7 — Final Verification

Run Mimikatz on the Windows 11 VM. Navigate to the Wazuh Discovery tab, 
select the `wazuh-alerts-*` index pattern and search for `mimikatz`.

The alert fires with:
- **Rule ID:** 100002
- **Description:** Mimikatz Usage Detected  
- **Level:** 15 (Critical)
- **MITRE ATT&CK:** T1003 (Credential Dumping)
- **Agent:** SOAR-Wazuh (Windows 11 VM)

![Mimikatz Alert Hit](doc/screenshots/windows11%20config%2038%20testing%20the%20rules%20on%20wazuh...we%20got%20a%20hit%20perfect.png)

Expanding the alert confirms the full rule details including rule description, 
rule ID, groups, and level.

![Rule Description Confirmed](doc/screenshots/windows11%20config%2039%20custom%20rule%20confirmation%20rule%20description.png)

## 6️⃣ Full Telemetry Flow Confirmed
```
Mimikatz runs on Windows 11 VM
       ↓
Sysmon captures process creation event (Event ID 1)
       ↓
Wazuh Agent forwards event to Wazuh Manager
       ↓
Wazuh Manager matches rule 100002
       ↓
Alert fires at Level 15 with MITRE T1003 tag
       ↓
Alert visible in Wazuh Dashboard Discovery tab
```

