# 📡 Wuzah Installation 

I had followed the instructions on the official Wazuh website documentiation but have faced several issues. Below I highlight my process of troubleshooting and resolving these issues.

####  Official documentation can be found here ---> https://documentation.wazuh.com/current/quickstart.html

---

## ❌ Issue 1 — Installation Error

- Everything seemed normal I let the installation process run. 
- When I returned to check it's progress I was greeted with an error. 

Installer output:

```Wazuh dashboard web application not yet initialized
ERROR: Wazuh dashboard installation failed
```
![Wazuh Resource Specs](doc/screenshots/wazuh%20installation%20error.png)

---
- I proceeded to check the installation log.

```bash
sudo cat /var/log/wazuh-install.log | tail -50
```

![Wazuh Installation Error 2](doc/screenshots/wazuh%20installation%20error2.png)

## 🔍 Root Cause

Indexer failed due to missing vm.max_map_count.

## ✅ Fix — Make sure memory parameters in your enviroment are correct

## ⚙ Pre-Installation Requirement

Set required memory parameter:

``` sudo sysctl -w vm.max_map_count=262144 ```

> ⚠️ Skipping this = guaranteed dashboard failure.

---

## Install Wazuh All-in-One again

```bash
curl -sO https://packages.wazuh.com/4.14/wazuh-install.sh
sudo bash ./wazuh-install.sh -a
```
![Wazuh Installation Error Memory Optimization and Manual Install](doc/screenshots/wazuh%20installation%20error%20memory%20optimization%20and%20manual%20install.png)

---

- After a successful installation I noted down the admin password and Wazuh URL.

``` INFO: --- Wazuh indexer ---
INFO: Wazuh indexer installation finished.
INFO: wazuh-indexer service started.
INFO: Wazuh indexer cluster initialized.
INFO: --- Wazuh server ---
INFO: Wazuh manager installation finished.
INFO: --- Wazuh dashboard ---
INFO: Wazuh dashboard installation finished.
INFO: Wazuh dashboard web application initialized.
INFO: You can access the web interface https://<wazuh-ip>:443
    User: admin
    Password: <generated-password>
INFO: Installation finished.
```
- If you have to reinstall make sure you clean up and remove all artifacts.
  
``` sudo rm -rf /var/log/wazuh-install.log
sudo rm -rf /etc/wazuh-*
sudo rm -rf /var/lib/wazuh-*
sudo rm -rf /var/log/wazuh-*
sudo rm -rf /usr/share/wazuh-*
sudo rm -rf wazuh-install.sh
```
- Verify clean:
``` bashdpkg -l | grep wazuh```
---

## ❌ Issue 2 — Dashboard Initialization Timeout

### Accessing the Dashboard
- I navigate to ```https://<wazuh-vm-ip>:443``` in the browser. Accepted the self-signed certificate warning (expected in a lab environment). 
- Wazuh seemed to be having issues initializing on the webpage.
![Wazuh Startup Issue 2](doc/screenshots/wazuh%20startup%20issue2.png)

- I then checked the Wazuh manager status ```sudo systemctl status wazuh-indexer``` and got this. 

![Wazuh Startup Issue 4 Check Write Command and Double Tab to See Services](doc/screenshots/wazuh%20startup%20issue4%20check%20write%20command%20and%20double%20tab%20to%20see%20services.png)


## 🔍 Root Cause:

On boot, all services attempt to start simultaneously. The Wazuh manager starts before the Wazuh indexer is fully initialized, times out waiting for it, and fails.

## ✅ Fix — Manual service start in correct order:
```bash
sudo systemctl start wazuh-indexer
```

### Wait 30 seconds
```bash
sudo systemctl start wazuh-manager
sudo systemctl start wazuh-dashboard
```
![Wazuh Startup Issue 6 Final Check Resolved](doc/screenshots/wazuh%20startup%20issue6%20final%20check%20resolved.png)

## 👨‍🔧 Permanent Fix — Make manager wait for indexer:

- I accessed the service settings
``` sudo nano /etc/systemd/system/wazuh-manager.service```

- Added to the [Unit] section:
```bash
After=wazuh-indexer.service
Requires=wazuh-indexer.service
Reload systemd:
```
- Reloaded the systemd
```bash
sudo systemctl daemon-reload
```
- Manager started and I was able to login to Wazuh using the credentials generated during installation. 
