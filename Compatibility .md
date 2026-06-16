# SimpleRelay - Compatible Devices & Setup Guide

Central list of devices, software, and systems that work with SimpleRelay as SMTP relay on your LAN.

All examples assume SimpleRelay running at `192.168.1.50` port `2525`.
Sender/From address must match the provider email configured in SimpleRelay (e.g. `you@gmail.com`).

> **Important:** Every device must set its From/Sender address to the exact email of the provider configured in SimpleRelay. If the From address doesn't match, SimpleRelay won't route the message.

> **Port note:** Some devices only support port 25. Remap in `docker-compose.yml`: change `"2525:2525"` to `"25:2525"`.

---

## 1. Virtualization & Servers

### Proxmox VE (8.1+)

Datacenter > Notifications > Add > SMTP

| Field | Value |
|-------|-------|
| Server | `192.168.1.50` |
| Port | `2525` |
| Encryption | Insecure |
| Authentication | unchecked |
| From Address | `you@gmail.com` |
| Recipient(s) | select target user |

Proxmox 8.1+ talks SMTP directly, no Postfix config needed.

### Proxmox VE (< 8.1)

Edit `/etc/postfix/main.cf`:

```
relayhost = [192.168.1.50]:2525
```

Restart: `systemctl restart postfix`

### VMware ESXi

Host > Manage > System > Advanced Settings:

| Setting | Value |
|---------|-------|
| `UserVars.esxSMTPServer` | `192.168.1.50` |
| `UserVars.esxSMTPPort` | `2525` |

Or via CLI:
```
esxcli system account set --smtp-server 192.168.1.50 --smtp-port 2525
```

### vCenter Server

Administration > System Configuration > Mail:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| SMTP Port | `2525` |
| Sender | `you@gmail.com` |

### XCP-ng / Xen Orchestra

In Xen Orchestra: Settings > Plugins > transport-email:

```json
{
  "transport": {
    "host": "192.168.1.50",
    "port": 2525,
    "secure": false
  },
  "from": "you@gmail.com"
}
```

### TrueNAS CORE

System > Email:

| Field | Value |
|-------|-------|
| Outgoing Mail Server | `192.168.1.50` |
| Mail Server Port | `2525` |
| Security | Plain (No Encryption) |
| SMTP Authentication | unchecked |
| From Email | `you@gmail.com` |

### TrueNAS SCALE

System Settings > Email:

| Field | Value |
|-------|-------|
| Outgoing Mail Server | `192.168.1.50` |
| Mail Server Port | `2525` |
| Security | Plain (No Encryption) |
| SMTP Authentication | unchecked |
| From Email | `you@gmail.com` |

### Synology DSM

Control Panel > Notification > Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| SMTP Port | `2525` |
| Secure Connection | None |
| Authentication | unchecked |
| Sender email | `you@gmail.com` |

Enable: "Enable email notifications"

Note: DSM 7.x may show a warning when using "No encryption". Sending works fine, ignore the warning.

### QNAP QTS

Control Panel > Notification Center > Service Account > Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| Secure Connection | None |
| Authentication | No |
| Sender email | `you@gmail.com` |

---

## 2. Firewalls & Network

### pfSense

System > Advanced > Notifications > E-Mail:

| Field | Value |
|-------|-------|
| E-Mail Server | `192.168.1.50` |
| SMTP Port | `2525` |
| From e-mail | `you@gmail.com` |
| Notification E-Mail | your target email |
| Disable SMTP SSL/TLS | checked |

### OPNsense

System > Settings > Notifications:

| Field | Value |
|-------|-------|
| SMTP Host | `192.168.1.50` |
| SMTP Port | `2525` |
| From | `you@gmail.com` |
| TLS | unchecked |
| Authentication | unchecked |

### MikroTik RouterOS

```
/tool e-mail
set server=192.168.1.50 port=2525 from=you@gmail.com
```

Test: `/tool e-mail send to=you@gmail.com subject="test" body="hello"`

Note: RouterOS 6.45+ supports custom ports. Older versions use port 25 only.

### Ubiquiti UniFi Network

Settings > System > Advanced > Email Notifications:

| Field | Value |
|-------|-------|
| SMTP Host | `192.168.1.50` |
| SMTP Port | `2525` |
| Use SSL | No |
| Sender | `you@gmail.com` |

Note: UI location varies by UniFi version. In 8.x+ look under System Settings > Advanced.

### EdgeRouter

```
set system name-server 8.8.8.8
set service notification email smtp-server 192.168.1.50
set service notification email smtp-port 2525
set service notification email from you@gmail.com
```

### OpenWRT

Install `msmtp`:

```
opkg update && opkg install msmtp
```

`/etc/msmtprc`:
```
account default
host 192.168.1.50
port 2525
from you@gmail.com
auth off
tls off
```

### VyOS

```
set system notification email smtp-server 192.168.1.50
set system notification email smtp-port 2525
set system notification email from you@gmail.com
```

---

## 3. Monitoring & Alerting

### Grafana

`grafana.ini` or env variables:

```ini
[smtp]
enabled = true
host = 192.168.1.50:2525
skip_verify = true
from_address = you@gmail.com
from_name = Grafana
```

Or via env: `GF_SMTP_ENABLED=true GF_SMTP_HOST=192.168.1.50:2525`

### Uptime Kuma

Settings > Notifications > Add > Email (SMTP):

| Field | Value |
|-------|-------|
| Hostname | `192.168.1.50` |
| Port | `2525` |
| Security | None |
| From Email | `you@gmail.com` |

### Zabbix

Administration > Media types > Email:

| Field | Value |
|-------|-------|
| SMTP server | `192.168.1.50` |
| SMTP server port | `2525` |
| SMTP email | `you@gmail.com` |
| Connection security | None |
| Authentication | None |

### Nagios / Icinga

Edit notification command in `/etc/nagios/commands.cfg`:

```
define command {
    command_name    notify-by-email
    command_line    /usr/bin/printf "%b" "$NOTIFICATIONTYPE$: $HOSTALIAS$/$SERVICEDESC$\n$SERVICEOUTPUT$" | \
                    /usr/bin/mail -S smtp=192.168.1.50:2525 -S from=you@gmail.com -s "$NOTIFICATIONTYPE$ - $HOSTALIAS$/$SERVICEDESC$" $CONTACTEMAIL$
}
```

### Prometheus Alertmanager

`alertmanager.yml`:

```yaml
global:
  smtp_smarthost: '192.168.1.50:2525'
  smtp_from: 'you@gmail.com'
  smtp_require_tls: false

receivers:
  - name: 'email'
    email_configs:
      - to: 'you@gmail.com'
```

### Netdata

`/etc/netdata/health_alarm_notify.conf`:

```
EMAIL_SENDER="you@gmail.com"
SEND_EMAIL="YES"
```

`/etc/msmtprc`:
```
account default
host 192.168.1.50
port 2525
from you@gmail.com
auth off
tls off
```

### Checkmk

Setup > Notifications > SMTP Server:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| SMTP Port | `2525` |
| From | `you@gmail.com` |
| Security | None |

---

## 4. IP Cameras & Security

All IP cameras use basic SMTP without OAuth or modern TLS. SimpleRelay is ideal for them.

### Hikvision

Configuration > Network > Advanced > Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| SMTP Port | `2525` |
| Enable SSL/TLS | unchecked |
| Authentication | unchecked |
| Sender | `you@gmail.com` |
| Receiver | your target email |

Attach snapshot: check "Attached Image" under Events > Email Linkage.

### Dahua

Setup > Network > SMTP (Email):

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| Anonymous | checked |
| Sender | `you@gmail.com` |
| SSL | None |

### Reolink

Settings > Surveillance > Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| TLS | None |
| Sender | `you@gmail.com` |

Note: Some Reolink models only support port 25. Remap in docker-compose.

### Axis

Setup > Events > Recipients > Add Recipient > Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| From | `you@gmail.com` |
| Authentication | None |

### Uniview

Setup > Network > Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| SSL | Disabled |
| Sender | `you@gmail.com` |

### Hanwha / Wisenet

Setup > Event > SMTP:

| Field | Value |
|-------|-------|
| Server Address | `192.168.1.50` |
| Port | `2525` |
| Use SSL | unchecked |
| Sender | `you@gmail.com` |

---

## 5. Smart Home & Automation

### Home Assistant

`configuration.yaml`:

```yaml
notify:
  - name: email
    platform: smtp
    server: 192.168.1.50
    port: 2525
    encryption: none
    sender: you@gmail.com
    recipient: you@gmail.com
```

Restart Home Assistant after edit.

### Node-RED

Use `node-red-node-email` node:

| Field | Value |
|-------|-------|
| Server | `192.168.1.50` |
| Port | `2525` |
| Secure | No |
| From | `you@gmail.com` |

### openHAB

`services/mail.cfg`:

```
hostname=192.168.1.50
port=2525
from=you@gmail.com
security=NONE
```

### ioBroker

Install `iobroker.email` adapter:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| Security | None |
| From | `you@gmail.com` |

---

## 6. Backup & Storage

### Veeam Backup & Replication

Menu > Notifications > SMTP Server:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| Use SSL/TLS | unchecked |
| From | `you@gmail.com` |

### Duplicati

Settings > Email options:

| Field | Value |
|-------|-------|
| smtp-url | `smtp://192.168.1.50:2525` |
| send-mail-from | `you@gmail.com` |
| send-mail-to | your target email |

### UrBackup

Settings > Mail:

| Field | Value |
|-------|-------|
| Mail server name | `192.168.1.50` |
| Mail server port | `2525` |
| Sender email | `you@gmail.com` |

### Bacula / Bareos

`bacula-dir.conf`:

```
Messages {
  Name = Standard
  mailcommand = "/usr/bin/bsmtp -h 192.168.1.50:2525 -f you@gmail.com -s \"Bacula: %t %e\" %r"
  mail = you@gmail.com = all, !skipped
}
```

### BorgBackup / Restic (scripts)

See section "Linux / Scripts" below.

---

## 7. Linux / Scripts

Anything running on Linux can send through SimpleRelay using standard tools.

### msmtp (recommended for scripts)

Install: `apt install msmtp` / `yum install msmtp`

`/etc/msmtprc`:
```
account default
host 192.168.1.50
port 2525
from you@gmail.com
auth off
tls off
```

Usage: `echo "Backup done" | msmtp you@gmail.com`

### mailx / mail

```bash
echo "Disk alert" | mail -S smtp=192.168.1.50:2525 \
  -S from=you@gmail.com -s "Alert" you@gmail.com
```

### curl (no dependencies)

```bash
curl smtp://192.168.1.50:2525 \
  --mail-from you@gmail.com \
  --mail-rcpt you@gmail.com \
  -T - <<EOF
From: you@gmail.com
To: you@gmail.com
Subject: Backup completed

Nightly backup finished successfully.
EOF
```

### Python

```python
import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg["From"] = "you@gmail.com"
msg["To"] = "you@gmail.com"
msg["Subject"] = "Alert"
msg.set_content("Something happened.")

with smtplib.SMTP("192.168.1.50", 2525) as s:
    s.send_message(msg)
```

### cron + sendmail

Edit Postfix `/etc/postfix/main.cf`:
```
relayhost = [192.168.1.50]:2525
```

Then standard cron MAILTO works:
```
MAILTO=you@gmail.com
0 3 * * * /root/backup.sh
```

### fail2ban

`/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
destemail = you@gmail.com
sender = you@gmail.com
mta = mail
action = %(action_mwl)s
```

Configure mail to use SimpleRelay via msmtp or Postfix relayhost.

### smartd (SMART disk alerts)

`/etc/smartd.conf`:
```
/dev/sda -a -m you@gmail.com -M exec /usr/share/smartmontools/smartd-runner
```

Requires msmtp or Postfix relayhost configured.

### logwatch

`/etc/logwatch/conf/logwatch.conf`:
```
MailTo = you@gmail.com
MailFrom = you@gmail.com
```

Requires msmtp or Postfix relayhost configured.

---

## 8. UPS, Printers, Hardware

### APC UPS (PowerChute)

PowerChute Business Edition > Email Settings:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| From | `you@gmail.com` |
| Authentication | None |

### Eaton UPS (Network Card)

Network > SMTP Settings:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| SMTP Port | `2525` |
| From | `you@gmail.com` |

### CyberPower UPS (RMCARD)

Notifications > SMTP:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| Sender | `you@gmail.com` |

### HP LaserJet (Enterprise)

Networking > Email Alerts (via EWS web interface):

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` |
| From | `you@gmail.com` |

Note: Many printers support only port 25. Remap in docker-compose.

### Kyocera / Ricoh / Brother

Web UI > Notifications or Scan-to-Email:

| Field | Value |
|-------|-------|
| SMTP Server | `192.168.1.50` |
| Port | `2525` (or 25) |
| Authentication | Off |
| From | `you@gmail.com` |

Scan-to-email: set the relay as SMTP server, your Gmail as From address.

---

## What does NOT work with SimpleRelay

- **Desktop email clients** (Outlook, Thunderbird) - these need full IMAP/SMTP with authentication
- **Mobile email apps** - same as above
- **Apps requiring OAuth2** - SimpleRelay accepts plain SMTP, not OAuth tokens
- **Software requiring SMTPS (port 465) with certificate validation** - SimpleRelay doesn't provide TLS to connecting clients
- **Cloud SaaS applications** - they use their own email infrastructure
- **Applications that hardcode the From address** to something other than your provider email - the From must match the provider in SimpleRelay
