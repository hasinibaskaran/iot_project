# Hardware Wiring Guide & Pin Configuration

## Step 1: Create a Common Ground Rail
Connect a jumper wire from **Physical Pin 6 (GND)** on the Raspberry Pi header to the **Negative (-) Rail** (usually the blue/black strip) on your breadboard. Every switch, button, and LED's short leg (Cathode) will connect to this single common ground rail.

## Step 2: Wire the SPST Toggle Switch & Push Buttons
Because `ACTIVE_LOW = True` is configured, all inputs connect between a GPIO pin and Ground.

```text
                    +--------------------+
[ GPIO 17 (Pin 11) ]---| SPST Switch        |---[ Breadboard GND Rail ]
[ GPIO 18 (Pin 12) ]---| Button A1          |---[ Breadboard GND Rail ]
[ GPIO 27 (Pin 13) ]---| Button A2          |---[ Breadboard GND Rail ]
                    +--------------------+
```

* **SPST Main Switch:**
  * Terminal 1 $\rightarrow$ Physical Pin 11 (GPIO 17)
  * Terminal 2 $\rightarrow$ Breadboard GND Rail
* **Coach A1 Momentary Button:**
  * Leg 1 $\rightarrow$ Physical Pin 12 (GPIO 18)
  * Leg 2 $\rightarrow$ Breadboard GND Rail
* **Coach A2 Momentary Button:**
  * Leg 1 $\rightarrow$ Physical Pin 13 (GPIO 27)
  * Leg 2 $\rightarrow$ Breadboard GND Rail

## Step 3: Wire the 6 Feedback LEDs
> [!WARNING]
> **Critical Rule:** Every LED MUST have a $220\ \Omega$ or $330\ \Omega$ resistor on its **Long Leg (Anode / +)** before connecting to the GPIO pin. Connecting LEDs directly without resistors will damage the Raspberry Pi GPIO pins.

An LED has two legs:
* **Long Leg (Anode / +):** Connects to the Resistor $\rightarrow$ GPIO Pin.
* **Short Leg (Cathode / -):** Connects directly to the Breadboard GND Rail.

```text
[ GPIO Pin ] ---> [ Resistor 220 Ohm ] ---> (Long Leg) [ LED ] (Short Leg) ---> [ GND Rail ]
```

### LED Wiring Matrix

| LED Function | LED Color | Pi BCM Pin | Physical Pin | Anode (+ Long Leg) Wiring | Cathode (- Short Leg) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trip Active** | Blue | `GPIO 5` | **Pin 29** | $220\ \Omega$ Resistor $\rightarrow$ Pin 29 | GND Rail |
| **System Error / Standby** | Red | `GPIO 6` | **Pin 31** | $220\ \Omega$ Resistor $\rightarrow$ Pin 31 | GND Rail |
| **Coach A1 OK** | Green | `GPIO 13` | **Pin 33** | $220\ \Omega$ Resistor $\rightarrow$ Pin 33 | GND Rail |
| **Coach A1 Fail** | Red | `GPIO 19` | **Pin 35** | $220\ \Omega$ Resistor $\rightarrow$ Pin 35 | GND Rail |
| **Coach A2 OK** | Green | `GPIO 20` | **Pin 38** | $220\ \Omega$ Resistor $\rightarrow$ Pin 38 | GND Rail |
| **Coach A2 Fail** | Red | `GPIO 21` | **Pin 40** | $220\ \Omega$ Resistor $\rightarrow$ Pin 40 | GND Rail |
