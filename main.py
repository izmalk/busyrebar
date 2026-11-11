import network
import socket
import time
from interstate75 import Interstate75, DISPLAY_INTERSTATE75_64X32

WIFI_SSID = "<YOUR_2.4GHZ_WIFI_SSID>"
WIFI_PASSWORD = "<YOUR_WIFI_PASSWORD>"
UDP_PORT = 4048

# Static network configuration (must match PANEL_IP in repeater.py)
STATIC_IP = "192.168.1.3"
SUBNET_MASK = "255.255.255.0"
GATEWAY = "192.168.1.1"
DNS_SERVER = "8.8.8.8"

i75 = Interstate75(display=DISPLAY_INTERSTATE75_64X32)
graphics = i75.display
width, height = i75.width, i75.height

def clear():
    graphics.set_pen(graphics.create_pen(0, 0, 0))
    graphics.clear()

# --- STAGE 1: POWER UP ---
# Shows a Green dot on the left immediately on boot
clear()
graphics.set_pen(graphics.create_pen(0, 255, 0))
graphics.circle(16, 16, 4)
i75.update(graphics)

# --- STAGE 2: WI-FI CONNECTING ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Disable CYW43 Wi-Fi power-saving so the chip does not drop ARP or UDP packets
try:
    wlan.config(pm=0xa11140)
except Exception:
    pass

# Force Static IP (IP, Subnet Mask, Gateway, DNS)
wlan.ifconfig((STATIC_IP, SUBNET_MASK, GATEWAY, DNS_SERVER))
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

while not wlan.isconnected():
    time.sleep(0.5)

print("Wi-Fi connected. IP config:", wlan.ifconfig())

# Wi-Fi Connected! Add a Blue dot in the middle
graphics.set_pen(graphics.create_pen(0, 0, 255))
graphics.circle(32, 16, 4)
i75.update(graphics)

# --- STAGE 3: WAIT FOR DATA ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT))
sock.setblocking(False)

first_packet = True

while True:
    try:
        data, addr = sock.recvfrom(6144)
        if data and len(data) == 6144:
            if first_packet:
                print("First 6144-byte frame received from:", addr)
                # Data Received! Add a White dot on the right
                graphics.set_pen(graphics.create_pen(255, 255, 255))
                graphics.circle(48, 16, 4)
                i75.update(graphics)

                # Pause for 1.5 seconds so you can visually confirm the handshake
                time.sleep(1.5)
                first_packet = False

            # Render the live Busy Bar frame directly from data
            idx = 0
            for y in range(height):
                for x in range(width):
                    r = data[idx]
                    g = data[idx + 1]
                    b = data[idx + 2]
                    idx += 3
                    graphics.set_pen(graphics.create_pen(r, g, b))
                    graphics.pixel(x, y)
            i75.update(graphics)
    except OSError:
        # No UDP packet waiting in the non-blocking socket buffer
        pass

    time.sleep(0.01)