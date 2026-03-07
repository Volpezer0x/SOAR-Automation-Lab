# 🐝 TheHive 5 Installation & Configuration

## Overview

TheHive is the case management platform in our SOAR pipeline. It sits on a
dedicated Ubuntu Server 22.04 VM alongside its two dependencies: Apache
Cassandra (graph database backend) and Elasticsearch (index/search backend).
The official installation guide can be found here: https://docs.strangebee.com/thehive/installation/installation-guide-linux-standalone-server/

---

## Step 1 — Install Java (Amazon Corretto 11)

TheHive 5 requires Java 11. The default Ubuntu Noble repos offer several
options but we specifically need Java 11 for compatibility. Check if Java
is already installed:

```bash
java -version
```

If Java is missing, Ubuntu will suggest available packages. Update and install
Amazon Corretto 11:

```bash
sudo apt update
sudo apt upgrade
sudo apt install java-common java-11-amazon-corretto-jdk
```

![Java Install](doc/screenshots/TheHive%20setup3%20manually%20install%20java.png)

Verify the installation:

```bash
java -version
```

You should see:
```
openjdk version "11.0.30" 2026-01-20 LTS
OpenJDK Runtime Environment Corretto-11.0.30.7.1
OpenJDK 64-Bit Server VM Corretto-11.0.30.7.1
```

![Java Success](doc/screenshots/TheHive%20setup4%20java%20success.png)

---

## Step 2 — Install Apache Cassandra 4.x

Cassandra is TheHive's graph database backend. We need to add the Apache
repository before installing.

#### 2a — Add the Cassandra APT repository

```bash
wget -qO - https://downloads.apache.org/cassandra/KEYS | sudo gpg --dearmor -o /usr/share/keyrings/cassandra-archive.gpg

echo "deb [signed-by=/usr/share/keyrings/cassandra-archive.gpg] https://debian.cassandra.apache.org 41x main" | sudo tee -a /etc/apt/sources.list.d/cassandra.sources.list
```

![Add Cassandra Repo](doc/screenshots/TheHive%20setup5%20cassandra%20setup2.png)

#### 2b — Update and install

```bash
sudo apt update
sudo apt install cassandra
```

![Cassandra Install](doc/screenshots/TheHive%20setup5%20cassandra%20setup3.png)

Cassandra installs version 4.1.10 and starts automatically. Verify:

```bash
sudo systemctl status cassandra
```

![Cassandra Running](doc/screenshots/TheHive%20setup5%20cassandra%20setup%20success.png)

---

## Step 3 — Configure Cassandra

Open the Cassandra config file:

```bash
sudo nano /etc/cassandra/cassandra.yaml
```

![Open Cassandra Config](doc/screenshots/TheHive%20setup8%20cassandra%20config1.png)

Make the following four changes. Use **Ctrl+W** to search for each setting.

#### cluster_name
Change the default `Test Cluster` to your lab name:
```yaml
cluster_name: 'SOAR-LAB'
```

![Cluster Name](doc/screenshots/TheHive%20setup8%20cassandra%20config2%20cluster_name.png)

#### listen_address
Set to the TheHive VM's IP so Cassandra binds to the right interface:
```yaml
listen_address: 10.181.218.119
```

![Listen Address](doc/screenshots/TheHive%20setup8%20cassandra%20config3%20listen_address%20use%20ctrl-w%20to%20search.png)

#### rpc_address
```yaml
rpc_address: 10.181.218.119
```

![RPC Address](doc/screenshots/TheHive%20setup8%20cassandra%20config4%20rpc_address%20use%20ctrl-w%20to%20search.png)

#### seed_provider
Update the seeds list to point to this node:
```yaml
seed_provider:
  - class_name: org.apache.cassandra.locator.SimpleSeedProvider
    parameters:
      - seeds: "10.181.218.119:7000"
```

![Seed Provider](doc/screenshots/TheHive%20setup8%20cassandra%20config5%20seed_provider%20use%20ctrl-w%20to%20search.png)

Save with **Ctrl+O**, exit with **Ctrl+X**.

#### 3c — Clear old data and restart

After changing `cluster_name` the existing data directory will have a
mismatch. Clear it and restart:

```bash
sudo rm -rf /var/lib/cassandra/*
sudo systemctl start cassandra.service
sudo systemctl status cassandra.service
```

![Cassandra Restart](doc/screenshots/TheHive%20setup8%20cassandra%20config6%20stop%20cassandra-remove-restart.png)

Cassandra should show `active (running)`.

> #### **⚠️Note:** If you ever see the fatal error:
> `Saved cluster name Test Cluster != configured name SOAR-LAB`
> it means the data directory wasn't cleared before changing the cluster name.
> Fix: edit `cassandra.yaml`, revert `cluster_name` back to `'Test Cluster'`,
> then clear `/var/lib/cassandra/*` again and restart.

---

## Step 4 — Install Elasticsearch

TheHive uses Elasticsearch as its index backend.

> **Critical:** TheHive 5 is **not** compatible with Elasticsearch 8.x.
> We initially installed 8.x which caused failures later. See the Issue section
> below. Install 7.17.20 directly to avoid this problem.

#### 4a — Add the Elasticsearch 7.x repo and install

```bash
sudo nano /etc/elasticsearch/elasticsearch.yml
```

![Open Elastic Config](doc/screenshots/TheHive%20setup9%20elasticsearch%20setup1.png)

Edit the config file:

```bash
sudo nano /etc/elasticsearch/elasticsearch.yml
```

![Elastic Config](doc/screenshots/TheHive%20setup9%20elasticsearch%20setup2.png)

Uncomment and set the following values. Use **Ctrl+W** to find each one:

```yaml
cluster.name: SOAR_LAB
node.name: node-1
network.host: 10.181.218.119
http.port: 9200
cluster.initial_master_nodes: ["node-1"]
```

![Elastic Network Settings](doc/screenshots/TheHive%20setup9%20elasticsearch%20setup3%20unhash%20networkhost-httpport-cluster.ini-master-use%20node-1only.png)

> **Important:** Make sure `cluster.initial_master_nodes` appears **only once**
> in the file. Having it twice causes a `Duplicate field` JSON parse error and
> prevents Elasticsearch from starting (see Issue section below).

![Full Config View](doc/screenshots/TheHive%20setup9%20elasticsearch%20setup3.png)

#### 4b — Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch.service
sudo systemctl start elasticsearch.service
sudo systemctl status elasticsearch
```

![Elastic Running](doc/screenshots/TheHive%20setup6%20elasticsearch%20setup%20success.png)

#### 4c — Verify Elasticsearch is responding

```bash
curl -k -u elastic:8N=99ali8IUEFgNbsqRg https://10.181.218.119:9200
```

You should receive a JSON response showing:
- `"name": "node-1"`
- `"cluster_name": "SOAR_LAB"`
- `"number": "8.19.11"` (or `"7.17.20"` after the downgrade below)

![Elastic Verification](doc/screenshots/TheHive%20setup9%20elasticsearch%20setup5%20final%20verification-all%20good.png)

---

## Step 5 — Download and Install TheHive

Download the TheHive `.deb` package along with its SHA256 checksum and GPG
signature for integrity verification:

```bash
wget -O /tmp/thehive_5.6.0-1_all.deb https://thehive.download.strangebee.com/5.6/deb/thehive_5.6.0-1_all.deb

wget -O /tmp/thehive_5.6.0-1_all.deb.sha256 https://thehive.download.strangebee.com/5.6/sha256/thehive_5.6.0-1_all.deb.sha256

wget -O /tmp/thehive_5.6.0-1_all.deb.asc https://thehive.download.strangebee.com/5.6/asc/thehive_5.6.0-1_all.deb.asc
```

![Download TheHive](doc/screenshots/TheHive%20setup7%20download%20thehive1.png)

#### 5a — Verify integrity

```bash
sha256sum /tmp/thehive_5.6.0-1_all.deb
cat /tmp/thehive_5.6.0-1_all.deb.sha256
```

Both hashes must match exactly:
```
8552b8062aeb1e8f0bed58dbca1ccefe8ddf5ef8929ac55b28dd5b5e4d135a19
```

![Verify Integrity](doc/screenshots/TheHive%20setup7%20download%20thehive2%20validate%20integrity.png)

#### 5b — Install

```bash
sudo apt-get install /tmp/thehive_5.6.0-1_all.deb
```

![TheHive Install](doc/screenshots/TheHive%20setup7%20complete.png)

---

## Step 6 — Set Folder Permissions

TheHive needs ownership of its data directory `/opt/thp`:

```bash
cd /opt/thp
ll
```

Initially owned by root:

![Before Permissions](doc/screenshots/TheHive%20setup10%20folder%20previlages%20edit1.png)

✅Fix ownership:

```bash
sudo chown -R thehive:thehive /opt/thp
ll
```

After the fix the directory should be owned by `thehive:thehive`:

![After Permissions](doc/screenshots/TheHive%20setup10%20folder%20previlages%20edit2.png)

---

## Step 7 — Configure TheHive (application.conf)

```bash
sudo nano /etc/thehive/application.conf
```

![Open App Config](doc/screenshots/TheHive%20setup11%20configure%20application.conf1.png)

Set the following values to point TheHive at your Cassandra and Elasticsearch
instances:

```hocon
db.janusgraph {
  storage {
    backend = cql
    hostname = ["10.181.218.119"]
    cql {
      cluster-name = thp
      keyspace = thehive
    }
  }
}

index.search {
  backend = elasticsearch
  hostname = ["10.181.218.119"]
  index-name = thehive
}

storage {
  provider = localfs
  localfs.location = /opt/thp/thehive/files
}

application.baseUrl = "http://10.181.218.119:9000"
play.http.context = "/"
```

![App Config](doc/screenshots/TheHive%20setup11%20configure%20application.conf2.png)

Start TheHive and verify it's running:

```bash
sudo systemctl start thehive
sudo systemctl status thehive
```

![TheHive Running](doc/screenshots/TheHive%20setup11%20configure%20application.conf3%20success.png)

---

## Step 8 — Final System Check

Confirm all three services are active and running:

```bash
sudo systemctl status thehive
sudo systemctl status cassandra
sudo systemctl status elasticsearch
```

![All Green](doc/screenshots/TheHive%20setup12%20final%20system%20check-all%20green.png)

All three should show `active (running)`.

---

## ❌ Issue — Browser Can't Reach Port 9000

**Symptom:**  
Navigating to `http://10.181.218.119:9000` returned:
```
Hmmm... can't reach this page
ERR_CONNECTION_REFUSED
```

![No Connection](doc/screenshots/TheHive%20setup13%20no%20connection.png)

### 🔎 Root Cause: Ubuntu's UFW firewall was blocking port 9000.

### ✅Fix:

```bash
sudo ufw allow 9000
```

![Allow Port 9000](doc/screenshots/TheHive%20setup14%20allow%20port%209000%20through%20firewall.png)

---

## ❌ Issue — TheHive Crashes: "Could not instantiate implementation"

**Symptom:**  
After opening port 9000 and accessing the web UI, TheHive would start but then
crash in a retry loop with:

```
[WARN] An error occurs (java.lang.IllegalArgumentException:
Could not instantiate implementation:
org.janusgraph.diskstorage.es.ElasticSearchIndex), retrying (7/10)
Caused by: org.apache.http.ConnectionClosedException: Connection is closed
```

![Implementation Error](doc/screenshots/TheHive%20setup15%20issue%20could%20not%20initiate%20implementation.png)

### 🔎 Root Cause:  
TheHive 5 uses JanusGraph which requires **Elasticsearch 7.x**. We had
installed Elasticsearch 8.19.11 which is incompatible — the JanusGraph
Elasticsearch driver cannot connect to the 8.x API. This happened after preforming ``` sudo apt upgrade ``` which accidentally upgraded elasticsearch from 7.x to 8.x

### ✅Fix — Downgrade Elasticsearch to 7.17.20:

#### Step 1 — Remove Elasticsearch 8.x completely

```bash
sudo systemctl stop elasticsearch
sudo apt remove elasticsearch -y
sudo rm -rf /var/lib/elasticsearch
sudo rm -rf /etc/elasticsearch
```

![Remove Elastic](doc/screenshots/TheHive%20setup16%20need%20to%20downgrade%20elasticsearch..remove%20elast.png)

#### Step 2 — Add the Elasticsearch 7.x repository

```bash
wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -

echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-7.x.list

sudo apt update
```

![Add 7.x Repo](doc/screenshots/TheHive%20setup17%20wget%20v7%20elastic.png)

#### Step 3 — Install Elasticsearch 7.17.20

```bash
sudo apt install elasticsearch=7.17.20
```

![Install 7.17.20](doc/screenshots/TheHive%20setup17%20wget%20v7%20elastic2.png)

#### Step 4 — Recreate the config file

Since we deleted `/etc/elasticsearch`, recreate it:

```bash
sudo nano /etc/elasticsearch/elasticsearch.yml
```

Apply the same settings as before:

```yaml
cluster.name: SOAR_LAB
node.name: node-1
path.data: /var/lib/elasticsearch
path.logs: /var/log/elasticsearch
network.host: 10.181.218.119
http.port: 9200
cluster.initial_master_nodes: ["node-1"]
```

#### Step 5 — Pin the version to prevent auto-upgrade back to 8.x

```bash
sudo apt-mark hold elasticsearch
```

#### Step 6 — Start and verify

```bash
sudo systemctl daemon-reload
sudo systemctl enable elasticsearch.service
sudo systemctl start elasticsearch.service
sudo systemctl status elasticsearch
```

---

## ❌ Issue — Elasticsearch Fails: Duplicate `cluster.initial_master_nodes`

**Symptom:**  
Elasticsearch failed to start with:
```
Caused by: com.fasterxml.jackson.core.JsonParseException:
Duplicate field 'cluster.initial_master_nodes'
SettingsException: Failed to load settings from [elasticsearch.yml]
```

![Duplicate Error](doc/screenshots/TheHive%20setup9%20elasticsearch%20setup4%20start-enable-status%20duplicate%20cluster%20error-hash%20the%20duplicate%20to%20fix.png)

### 🔎Root Cause:  
The `cluster.initial_master_nodes` key appeared twice in `elasticsearch.yml` —
once uncommented and once still commented. Elasticsearch parsed both as active
settings.

## ✅Fix:  
Open the config and comment out the duplicate line, leaving only one active
`cluster.initial_master_nodes` entry:

```bash
sudo nano /etc/elasticsearch/elasticsearch.yml
```

After fixing, restart:

```bash
sudo systemctl start elasticsearch.service
sudo systemctl status elasticsearch
```

Elasticsearch should now start cleanly with `active (running)`.

---

## Final Verification — TheHive Accessible

With all services running and port 9000 open, navigate to:

```
http://10.181.218.119:9000
```

Log in with the default credentials:
- **Username:** `admin@thehive.local`
- **Password:** `secret`

> Change the admin password immediately after first login.

TheHive loads and shows the Organisation List — confirming the full stack is
working:

![TheHive Working](doc/screenshots/TheHive%20setup18%20all%20working.png)

---

## Service Startup Order

**Always start services in this order** — each one must be healthy before
starting the next:

```bash
sudo systemctl start cassandra
# wait ~30 seconds
sudo systemctl start elasticsearch
# wait ~30 seconds
sudo systemctl start thehive
```

**To verify all are running:**

```bash
sudo systemctl status cassandra
sudo systemctl status elasticsearch
sudo systemctl status thehive
```

---

## ⚙️ Summary of Issues Encountered

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | Cassandra cluster name mismatch | Changed `cluster_name` without clearing old data | Revert name OR clear `/var/lib/cassandra/*` |
| 2 | Port 9000 unreachable | UFW firewall blocking port | `sudo ufw allow 9000` |
| 3 | TheHive crashes on startup | Elasticsearch 8.x incompatible with JanusGraph | Downgrade to Elasticsearch 7.17.20 |
| 4 | Elasticsearch fails to start | Duplicate `cluster.initial_master_nodes` in config | Comment out the duplicate line |
