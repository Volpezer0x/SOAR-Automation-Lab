# 🖥️ Part 1: Virtual Machine Setup

This phase establishes the core lab environment using **four virtual machines** hosted on **VirtualBox**.

---

## 🧱 Virtual Machines

| VM Name     | OS          | Role / Purpose                     | RAM  | Notes                       |
|------------|-------------|------------------------------------|------|-----------------------------|
| soar-wuzah | Ubuntu server 22.04 LTS  | SEIM | 8 GB | no additional requierments |
| soar-thehive | Ubuntu server 22.04 LTS | Case Manager | 16 GB | Java 11 must be installed on the enviroment |
| soar-automation | Ubuntu server 22.04 LTS | Webhook server | 2 GB | Python3, PIP, Flask |
| Windows 11 | Windows 11  | Victim endpoint | 8 GB | Sysmon, Defender, Wuzah agent, Mimikatz |

> Note. All VMs were assigned 60GB of Disk space.

---

## 🛠️ Installation Notes

### soar-wuzah
- Standard Wazah setup. for reference follow instruction on Wazuh's official website https://documentation.wazuh.com/current/quickstart.html

![Wazuh Resource Specs](doc/screenshots/Wazuh%20resource%20specs.png)

---

### soar-thehive
- It is critical that Java 11 is installed on this enviroment 
``` sudo apt install java-common java-11-amazon-corretto-jdk```
- Follow instructions on theHive's official website https://docs.strangebee.com/thehive/installation/installation-guide-linux-standalone-server/#step-2-set-up-the-java-virtual-machine-jvm
- Use elasticsearch v7.x NOT v8.x <---- ⚠️VERY IMPORTANT! verify the version if you will use the latest TheHive version, otherwise TheHive won't boot ! Ask me how I know 😂

![TheHive Resource Specs](doc/screenshots/TheHive%20resource%20specs.png)

---

### soar-automation

- Make sure you have a static IP to avoid any connection issued down the line or when rebooting vms
- You will need to install Python 3, PIP, and Flask on this enviroment
  ```sudo apt install python3 python3-pip -y``` -- 
  ``` pip3 install flask requests```

  ![Flask automation Resource Specs](/doc/screenshots/Flask%20resource%20spec.png)

---
### Windows 11
- Used as the victim endpoint
- Windows Defender left enabled but C drive was added to the exception in order to stop Windows from deleting Mimikatz executables
- Sysmon installed 
- Wazuh agent installed and configured
---
### ⚠️ NOTE: All Ubuntu VMs have OpenSSH installed and all work was done via 🖥️*POWERSHELL* SSH sessions from both the Windows 11 VM and my local host machine.

![Linux OpenSSH Server Installation](doc/screenshots/linux%20setup%20openssh%20server%20install.png)

---
## ✅ Outcome

All virtual machines boot reliably, communicate over the network, and are ready for attack simulation, alert extraction, alert enrichment, automated case filing, Email notifications with MITER tags and Severity headers.
