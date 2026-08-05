#!/usr/bin/env python3
"""
Smart Train Sanitation System - Raspberry Pi Gateway Controller (Proteus Native)
Author: final-year project
Description:
    Interfaces with physical GPIO components using RPi.GPIO (Proteus compatible):
      - Toggles on/off state via Main Switch.
      - Dispatches coach sanitation request alerts to FastAPI backend using Buttons A1 & A2.
      - Tracks station progress automatically using a thread-safe 30-minute timer.
      - Updates feedback LEDs (Blue, System Red, Green/Red for A1, Green/Red for A2).
    Includes a fallback local simulator for development/testing on non-Pi machines.
"""

import time
import logging
import threading
import socket
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
except ImportError:
    import os

try:
    import requests
except ImportError:
    print("Warning: 'requests' module not found. Run 'pip install requests' to install it.")

# ==========================================
# CONSTANTS & CONFIGURATIONS
# ==========================================
BACKEND_URL = os.getenv("BACKEND_URL", "https://fastapi-python-boilerplate-gokul-9978.vercel.app").rstrip("/")
TRAIN_NUMBER = os.getenv("TRAIN_NUMBER", "12601")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "secret-test-key-2026")
try:
    STATION_UPDATE_INTERVAL = int(os.getenv("STATION_UPDATE_INTERVAL", "1800"))
except ValueError:
    STATION_UPDATE_INTERVAL = 1800

# Hardware logic configuration:
# Set ACTIVE_LOW = True if your switches/buttons pull the GPIO pin to GND when active. (Standard setup with pull-ups)
# Set ACTIVE_LOW = False if your switches/buttons pull the GPIO pin to 3.3V when active. (Setup with pull-downs)
ACTIVE_LOW = True

# ==========================================
# GPIO PIN MAP (BCM numbering)
# ==========================================
PIN_MAIN_SWITCH = 17
PIN_BUTTON_A1 = 18
PIN_BUTTON_A2 = 27

PIN_LED_BLUE = 5         # System Trip Initialized Successful
PIN_LED_SYS_RED = 6      # System Error / WiFi Offline / API Failure
PIN_LED_GREEN_A1 = 13    # Coach A1 Alert Dispatched Successful
PIN_LED_RED_A1 = 19      # Coach A1 Alert Dispatched Failed
PIN_LED_GREEN_A2 = 20    # Coach A2 Alert Dispatched Successful
PIN_LED_RED_A2 = 21      # Coach A2 Alert Dispatched Failed

ALL_LEDS = [PIN_LED_BLUE, PIN_LED_SYS_RED, PIN_LED_GREEN_A1, PIN_LED_RED_A1, PIN_LED_GREEN_A2, PIN_LED_RED_A2]

# ==========================================
# GLOBAL STATE VARIABLES
# ==========================================
stations = []            # Cached station route list
trip_number = ""         # Active trip number
previous_station = ""    # Last passed station ID
next_station = ""        # Upcoming station ID
current_index = 0        # Index pointer for next_station in stations list
station_timer = None     # Reference to background timer thread
station_lock = threading.Lock()
last_alert_times = {"A1": 0.0, "A2": 0.0}
debounce_lock = threading.Lock()
DEBOUNCE_INTERVAL = 5.0  # Cooldown period in seconds
keep_running = True

# ==========================================
# HARDWARE / MOCK INTERFACE HARDENING
# ==========================================
try:
    import RPi.GPIO as GPIO
    IS_MOCK = False
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Helper functions for physical/Proteus GPIO
    def set_led(pin, state: bool):
        try:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        except Exception as e:
            logging.debug(f"GPIO set_led failed for pin {pin}: {e}")

    def read_switch():
        try:
            # Read switch state based on active-low vs active-high logic
            val = GPIO.input(PIN_MAIN_SWITCH)
            return val == GPIO.LOW if ACTIVE_LOW else val == GPIO.HIGH
        except Exception as e:
            logging.debug(f"GPIO read_switch failed: {e}")
            return False

    def setup_gpio():
        # Setup Switches/Buttons with appropriate pull-up or pull-down configuration
        pud_mode = GPIO.PUD_UP if ACTIVE_LOW else GPIO.PUD_DOWN
        GPIO.setup(PIN_MAIN_SWITCH, GPIO.IN, pull_up_down=pud_mode)
        GPIO.setup(PIN_BUTTON_A1, GPIO.IN, pull_up_down=pud_mode)
        GPIO.setup(PIN_BUTTON_A2, GPIO.IN, pull_up_down=pud_mode)

        # Setup LED Outputs
        for pin in ALL_LEDS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

except (ImportError, RuntimeError):
    IS_MOCK = True
    logging.warning("RPi.GPIO not found or not in Proteus environment. Enabling local terminal simulator.")

    mock_states = {
        "switch": False,
        "a1": False,
        "a2": False,
        "leds": {pin: False for pin in ALL_LEDS}
    }

    def set_led(pin, state: bool):
        if mock_states["leds"][pin] != state:
            mock_states["leds"][pin] = state
            status = "ON (SUCCESS/ACTIVE)" if state else "OFF (STBY/CLEARED)"
            print(f"[Mock LED] Pin {pin:02d} -> {status}")

    def read_switch():
        return mock_states["switch"]

    def setup_gpio():
        pass


def interruptible_sleep(seconds):
    global keep_running
    for _ in range(int(seconds * 10)):
        if not keep_running or not read_switch():
            return False
        time.sleep(0.1)
    return True


# ==========================================
# THREAD-SAFE STATION TIMER
# ==========================================
class StationTimer(threading.Thread):
    def __init__(self, interval_seconds, callback):
        super().__init__()
        self.interval = interval_seconds
        self.callback = callback
        self.stop_event = threading.Event()
        self.daemon = True

    def run(self):
        while not self.stop_event.wait(self.interval):
            self.callback()

    def stop(self):
        self.stop_event.set()


# ==========================================
# CORE UTILITY & API FUNCTIONS
# ==========================================
def check_wifi():
    try:
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except OSError:
        return False


def check_backend_reachability():
    try:
        parsed_url = urlparse(BACKEND_URL)
        host = parsed_url.hostname or "localhost"
        port = parsed_url.port or (80 if parsed_url.scheme == "http" else 443)
        
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False


def init_trip():
    global stations, trip_number, previous_station, next_station, current_index
    url = f"{BACKEND_URL}/api/init-trip"
    params = {"train_number": TRAIN_NUMBER}
    headers = {"x-api-key": API_SECRET_KEY}

    logging.info(f"Connecting to Backend to fetch trip sequence for Train {TRAIN_NUMBER}...")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=8)
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                if "text/html" in content_type and "Vercel" in response.text:
                    logging.error("Received HTML response from Vercel instead of JSON. "
                                  "This is likely due to 'Vercel Deployment Protection' (Authentication) being enabled. "
                                  "Please go to Vercel Project Settings -> Deployment Protection and disable it.")
                else:
                    logging.error(f"Expected JSON response, but received Content-Type '{content_type}': {response.text[:200]}")
                return False
            data = response.json()
            if data.get("success"):
                with station_lock:
                    stations = data.get("stations", [])
                    trip_number = data.get("trip_number", "")
                    
                    logging.info(f"Loaded Trip Number: {trip_number}")
                    logging.info(f"Loaded Route Stations count: {len(stations)}")
                    
                    if len(stations) >= 2:
                        previous_station = stations[0]["station_id"]
                        next_station = stations[1]["station_id"]
                        current_index = 1
                    elif len(stations) == 1:
                        previous_station = stations[0]["station_id"]
                        next_station = stations[0]["station_id"]
                        current_index = 0
                    else:
                        previous_station = "START"
                        next_station = "END"
                        current_index = 0

                    logging.info(f"Ready. Initial Segment: {previous_station} -> {next_station}")
                return True
            else:
                logging.error(f"Backend init-trip error: {data.get('detail', 'Unknown error')}")
        else:
            logging.error(f"Failed HTTP {response.status_code} on init-trip: {response.text}")
    except Exception as e:
        logging.error(f"Connection Exception during init_trip: {str(e)}")
    
    return False


def update_station():
    global stations, previous_station, next_station, current_index

    with station_lock:
        if not stations or current_index >= len(stations):
            logging.warning("Station timer fired, but cache is empty or current index is out of bounds. Cannot progress.")
            return

        if current_index < len(stations) - 1:
            previous_station = stations[current_index]["station_id"]
            current_index += 1
            next_station = stations[current_index]["station_id"]
            logging.info(f"[Timer Track] Segment updated: Passed '{previous_station}' | Heading to '{next_station}' (Progress: {current_index}/{len(stations)-1})")
        else:
            logging.info("[Timer Track] Train has arrived at the final terminal station. Segment progression stopped.")


def send_alert(coach):
    if coach == "A1":
        green_led = PIN_LED_GREEN_A1
        red_led = PIN_LED_RED_A1
    elif coach == "A2":
        green_led = PIN_LED_GREEN_A2
        red_led = PIN_LED_RED_A2
    else:
        logging.error(f"Attempted to alert invalid coach segment: {coach}")
        return

    from datetime import datetime
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    url = f"{BACKEND_URL}/api/alert"
    headers = {
        "x-api-key": API_SECRET_KEY,
        "Content-Type": "application/json"
    }
    with station_lock:
        last_station = previous_station
        nxt_station = next_station
        active_trip = trip_number

    if not active_trip:
        logging.warning(f"Aborting alert dispatch: No active trip initialized (system may have been reset).")
        return

    payload = {
        "train_number": TRAIN_NUMBER,
        "trip_number": active_trip,
        "coach_number": coach,
        "last_station_id": last_station,
        "next_station_id": nxt_station,
        "time": time_str
    }

    logging.info(f"[Button Pressed] Dispatching sanitation alert for Coach {coach}...")
    success = False
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                if "text/html" in content_type and "Vercel" in response.text:
                    logging.error("Received HTML response from Vercel instead of JSON. "
                                  "This is likely due to 'Vercel Deployment Protection' (Authentication) being enabled. "
                                  "Please go to Vercel Project Settings -> Deployment Protection and disable it.")
                else:
                    logging.error(f"Expected JSON response, but received Content-Type '{content_type}': {response.text[:200]}")
            else:
                data = response.json()
                if data.get("success"):
                    logging.info(f"[Alert Sent Success] Dispatched to: {data.get('dispatched_to')}")
                    success = True
                else:
                    logging.error(f"[Alert API Refused] success=False: {response.text}")
        else:
            logging.error(f"[Alert Response Error] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(f"[Network Exception] Failed to post alert for Coach {coach}: {str(e)}")

    if success:
        set_led(green_led, True)
        set_led(red_led, False)
    else:
        set_led(green_led, False)
        set_led(red_led, True)

    time.sleep(3)
    set_led(green_led, False)
    set_led(red_led, False)


def handle_a1(channel=None):
    now = time.time()
    with debounce_lock:
        if now - last_alert_times["A1"] < DEBOUNCE_INTERVAL:
            logging.info("[Button Debounced] Ignoring press on button A1 (rate limited).")
            return
        last_alert_times["A1"] = now

    threading.Thread(target=send_alert, args=("A1",), daemon=True).start()


def handle_a2(channel=None):
    now = time.time()
    with debounce_lock:
        if now - last_alert_times["A2"] < DEBOUNCE_INTERVAL:
            logging.info("[Button Debounced] Ignoring press on button A2 (rate limited).")
            return
        last_alert_times["A2"] = now

    threading.Thread(target=send_alert, args=("A2",), daemon=True).start()


def reset_system():
    global stations, trip_number, previous_station, next_station, current_index, station_timer, last_alert_times
    
    if station_timer:
        station_timer.stop()
        station_timer = None

    with station_lock:
        stations = []
        trip_number = ""
        previous_station = ""
        next_station = ""
        current_index = 0

    with debounce_lock:
        last_alert_times = {"A1": 0.0, "A2": 0.0}

    for pin in ALL_LEDS:
        if pin == PIN_LED_SYS_RED:
            set_led(pin, True)  # Standby / Waiting for Switch ON
        else:
            set_led(pin, False)
    
    logging.info("System state has been reset to standby.")


# ==========================================
# INTERACTIVE CONSOLE FOR LOCAL MOCK TESTING
# ==========================================
def console_simulator():
    global keep_running
    time.sleep(1.5)
    print("\n" + "="*60)
    print("          IOT CONTROLLER LOCAL CONSOLE SIMULATOR")
    print("   Type any of these commands to simulate hardware events:")
    print("     'switch' : Flip Main Switch ON / OFF")
    print("     'a1'     : Simulates Push Button A1 (Sanitation Alert)")
    print("     'a2'     : Simulates Push Button A2 (Sanitation Alert)")
    print("     'exit'   : Shuts down the gateway program")
    print("="*60 + "\n")

    while True:
        try:
            cmd = input().strip().lower()
            if cmd == 'switch':
                mock_states["switch"] = not mock_states["switch"]
                print(f"[Sim] Main Switch toggled to: {'ON' if mock_states['switch'] else 'OFF'}")
            elif cmd == 'a1':
                if not mock_states["switch"]:
                    print("[Sim] Cannot alert: Main Switch is currently OFF")
                else:
                    print("[Sim] Button A1 Pressed!")
                    handle_a1()
            elif cmd == 'a2':
                if not mock_states["switch"]:
                    print("[Sim] Cannot alert: Main Switch is currently OFF")
                else:
                    print("[Sim] Button A2 Pressed!")
                    handle_a2()
            elif cmd == 'exit':
                print("[Sim] Exiting simulator and gateway program cleanly...")
                keep_running = False
                break
            elif cmd:
                print(f"[Sim] Unknown command: '{cmd}'. Try 'switch', 'a1', 'a2', or 'exit'.")
        except (EOFError, KeyboardInterrupt):
            keep_running = False
            break


# Polling loop for hardware push buttons (scope-safe)
def button_monitor_loop():
    global keep_running
    active_state = GPIO.LOW if ACTIVE_LOW else GPIO.HIGH
    
    last_state_a1 = not active_state
    last_state_a2 = not active_state

    while keep_running and read_switch():
        try:
            # Check Button A1
            state_a1 = GPIO.input(PIN_BUTTON_A1)
            if state_a1 == active_state and last_state_a1 != active_state:
                handle_a1()
            last_state_a1 = state_a1

            # Check Button A2
            state_a2 = GPIO.input(PIN_BUTTON_A2)
            if state_a2 == active_state and last_state_a2 != active_state:
                handle_a2()
            last_state_a2 = state_a2

        except Exception as e:
            logging.debug(f"Button polling exception: {e}")

        time.sleep(0.05)  # 50ms poll rate


# ==========================================
# MAIN EXECUTION ROUTINE
# ==========================================
def main():
    global station_timer, keep_running
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.info("Starting Smart Train Sanitation Pi Controller...")
    logging.info(f"Targeting FastAPI Backend: {BACKEND_URL}")
    logging.info(f"Train Configured Number: {TRAIN_NUMBER}")

    setup_gpio()
    set_led(PIN_LED_SYS_RED, True)  # Initially show Standby Red LED on script start

    if IS_MOCK:
        threading.Thread(target=console_simulator, daemon=True).start()

    system_active = False

    try:
        while keep_running:
            switch_on = read_switch()
            

            # Transition: Switch turned ON
            if not system_active and switch_on:
                logging.info("Main Switch ON. Starting initialization routine...")
                set_led(PIN_LED_SYS_RED, True)
                # Step 1: Network Check and Trip init API
                network_ready = False
                init_success = False
                while switch_on and not (network_ready and init_success):
                    
                    if not network_ready:
                        if check_wifi():
                            if check_backend_reachability():
                                logging.info("Network check succeeded. Backend is reachable.")
                                network_ready = True
                            else:
                                logging.warning("General internet is OK, but backend is unreachable. Retrying in 5s...")
                                if not interruptible_sleep(5):
                                    switch_on = False
                        else:
                            logging.warning("Wi-Fi network connection offline. Retrying in 5s...")
                            if not interruptible_sleep(5):
                                switch_on = False

                    if switch_on and network_ready and not init_success:
                        if init_trip():
                            init_success = True
                        else:
                            logging.warning("Failed to initialize trip. Retrying in 10s...")
                            if not interruptible_sleep(10):
                                switch_on = False

                    if switch_on:
                        switch_on = read_switch()

                if not switch_on:
                    reset_system()
                    continue                    

                # Step 2: Initialization Completed
                set_led(PIN_LED_SYS_RED, False)
                set_led(PIN_LED_BLUE, True)
                system_active = True
                
                # Step 3: Register background timer
                logging.info(f"Registering station update timer. Interval = {STATION_UPDATE_INTERVAL}s")
                station_timer = StationTimer(STATION_UPDATE_INTERVAL, update_station)
                station_timer.start()

                # Step 4: Assign Event listeners safely
                if not IS_MOCK:
                    threading.Thread(target=button_monitor_loop, daemon=True).start()
                logging.info("Button monitor thread started for A1 and A2.")

            # Transition: Switch turned OFF
            elif system_active and not switch_on:
                logging.info("Main Switch turned OFF. Entering standby sleep mode...")
                reset_system()
                system_active = False

            time.sleep(0.5)

    except KeyboardInterrupt:
        logging.info("Terminated by keyboard interrupt (Ctrl+C).")
    finally:
        logging.info("Cleaning up controller resources...")
        reset_system()
        if not IS_MOCK:
            try:
                time.sleep(2)
                GPIO.cleanup()
            except Exception as e:
                logging.debug(f"GPIO cleanup failed: {e}")
        logging.info("Clean exit accomplished.")


if __name__ == "__main__":
    main()