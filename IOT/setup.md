# Smart Train Sanitation System - Gateway Controller Setup

This repository contains the software and hardware integration setup for the **Smart Train Sanitation Gateway Controller** running on a Raspberry Pi. The gateway interacts with physical switches/buttons, dispatches real-time sanitation alerts to a FastAPI backend server, tracks station progression using background threads, and drives status LEDs.

---

## 📋 System Prerequisites

* **Hardware:**
  * Raspberry Pi (3B / 4 / 5 or Zero W)
  * 1× SPST Toggle Switch (Main Power / Trip Switch)
  * 2× Momentary Push Buttons (Coach A1 & Coach A2 Alerts)
  * 6× LEDs (1 Blue, 3 Red, 2 Green)
  * 6× 220 Ω or 330 Ω Resistors
  * Breadboard & Jumper Wires
* **Operating System:** Raspberry Pi OS (64-bit / Debian Bookworm or Bullseye)
* **Software:** Python 3.9+ with `pip` installed

---

## 🛠️ Hardware Wiring Diagram

### 1. GPIO Pin Mapping (BCM Numbering)

| Device / Component | Function | BCM Pin | Physical Header Pin |
| :--- | :--- | :--- | :--- |
| **Main SPST Switch** | System Power / Trip Toggle | `GPIO 17` | **Pin 11** |
| **Button A1** | Coach A1 Alert Trigger | `GPIO 18` | **Pin 12** |
| **Button A2** | Coach A2 Alert Trigger | `GPIO 27` | **Pin 13** |
| **Blue LED** | Trip Active / Init Success | `GPIO 5` | **Pin 29** |
| **System Red LED** | System Standby / Error | `GPIO 6` | **Pin 31** |
| **Green LED A1** | Coach A1 Alert Success | `GPIO 13` | **Pin 33** |
| **Red LED A1** | Coach A1 Alert Failed | `GPIO 19` | **Pin 35** |
| **Green LED A2** | Coach A2 Alert Success | `GPIO 20` | **Pin 38** |
| **Red LED A2** | Coach A2 Alert Failed | `GPIO 21` | **Pin 40** |

> **Note on Switches & Buttons:** All inputs use `ACTIVE_LOW = True` logic. Connect one side of each switch/button to its designated GPIO pin, and the other side directly to **Ground (GND)**.
>
> **Note on LEDs:** Connect the long leg (Anode / +) of each LED to its designated GPIO pin through a 220 Ω resistor. Connect all short legs (Cathode / -) to the **Common Ground Rail (GND)**.

---

## 🚀 Installation & Software Setup

### Step 1: Create Project Directory
Log into your Raspberry Pi via SSH or open the terminal and execute:

```bash
mkdir -p ~/smart_train_gateway
cd ~/smart_train_gateway
```

### Step 2: Install Python Dependencies
Install required Python libraries (requests, python-dotenv, and RPi.GPIO):

```bash
sudo apt install -y python3-pip python3-dotenv python3-requests python3-rpi.gpio
```

### Step 3: Configure Environment Variables (.env)
Create a `.env` file inside the `~/smart_train_gateway` directory:

```bash
nano .env
```

Paste your environment variables:

```env
BACKEND_URL=https://fastapi-python-boilerplate-gokul-9978.vercel.app
TRAIN_NUMBER=12601
API_SECRET_KEY=_KzR9gWnZ2sF7yQv8Jb_X6d5K8t3P1m0s9A4v6L3D2o
STATION_UPDATE_INTERVAL=1800
```

Save and exit nano (Ctrl+O, Enter, Ctrl+X).

### Step 4: Transfer / Deploy gateway_controller.py
Ensure the `gateway_controller.py` script is transferred from your local development machine (located at `IOT/gateway_controller.py` in this project repository) into the target directory `~/smart_train_gateway/` on your Raspberry Pi.

If copying from your local laptop to the Raspberry Pi via `scp`, run the following command from the root of this project repository:

```bash
scp IOT/gateway_controller.py pi@train-alert.local:/home/pi/smart_train_gateway/
```

---

## 🧪 Testing & Verification

### 1. Run Hardware Diagnostics
To manually run the controller and watch the live console logs:

```bash
python3 ~/smart_train_gateway/gateway_controller.py
```

### 2. Verify Physical Operations
* **System Off (SPST Off):** Only System Red LED turns ON (Standby state).
* **System On (SPST On):**
  * Red LED turns OFF.
  * Pi connects to the backend API and pulls the trip schedule for Train 12601.
  * Blue LED turns ON (Trip Active).
* **Button Presses:**
  * Press Button A1 / A2: The script posts the alert to the FastAPI backend.
  * **On Success:** Corresponding Green LED lights up for 3 seconds.
  * **On API Failure:** Corresponding Red LED lights up for 3 seconds.

---

## ⚙️ Enable Auto-Start on Boot (systemd Service)
To run the gateway controller automatically when the Raspberry Pi boots:

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/train-gateway.service
```

Paste the following service configuration:

```ini
[Unit]
Description=Smart Train Sanitation Gateway Controller
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smart_train_gateway
ExecStart=/usr/bin/python3 /home/pi/smart_train_gateway/gateway_controller.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable train-gateway.service
sudo systemctl start train-gateway.service
```

Check live service status / logs:

```bash
sudo systemctl status train-gateway.service
```