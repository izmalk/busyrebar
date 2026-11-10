import io
import socket
import time
from datetime import datetime
from PIL import Image, ImageEnhance
from busylib import BusyBar

# --- CONFIGURATION ---
BUSYBAR_IP = "192.168.1.2"
BUSYBAR_TOKEN = "<YOUR_BUSYBAR_PIN>"
PANEL_IP = "192.168.1.3"
PANEL_PORT = 4048
POLL_INTERVAL = 0.25            # 4 FPS update rate

# Screen & Panel Dimensions
PANEL_W, PANEL_H = 64, 32       # Target LED matrix size
SOURCE_W, SOURCE_H = 72, 16     # Busy Bar raw frame capture size

# Flexibility & Layout Controls (Values = pixels to crop inward from each edge)
ENABLE_CROP = False             # True = use side crops, False = scale full width
CROP_LEFT = 4                   # Pixels to trim from the left edge (0 = no crop)
CROP_RIGHT = 4                  # Pixels to trim from the right edge (0 = no crop)
CROP_TOP = 0                    # Pixels to trim from the top edge (0 = no crop)
CROP_BOTTOM = 0                 # Pixels to trim from the bottom edge (0 = no crop)

TARGET_W = 64                   # Desired width after transformation
TARGET_H = 28                   # Target height when cropping
OFFSET_X = 0                    # Horizontal fine-tuning offset (-/+ pixels)
OFFSET_Y = 2                    # Vertical fine-tuning offset (-/+ pixels)
# ---------------------

def get_scheduled_brightness() -> float:
    """Returns a brightness multiplier (0.0 to 1.0) based on the current hour."""
    hour = datetime.now().hour
    if 0 <= hour < 7:
        return 0.0    # Screen completely off overnight
    elif hour >= 21 or hour < 8:
        return 0.4    # Evening setting (compensates for smoked acrylic tint)
    return 0.25       # Standard daytime brightness

def transform_frame(raw_frame_bytes: bytes) -> Image.Image:
    """Transforms the Busy Bar frame with intuitive inward side margins and coordinate offsets."""
    try:
        src = Image.open(io.BytesIO(raw_frame_bytes)).convert("RGB")
    except Exception:
        src = Image.frombytes("RGB", (SOURCE_W, SOURCE_H), raw_frame_bytes)

    canvas = Image.new("RGB", (PANEL_W, PANEL_H), (0, 0, 0))

    if ENABLE_CROP:
        # Convert inward margin numbers into absolute bounding coordinates (left, top, right, bottom)
        box_left = CROP_LEFT
        box_top = CROP_TOP
        box_right = SOURCE_W - CROP_RIGHT
        box_bottom = SOURCE_H - CROP_BOTTOM

        cropped = src.crop((box_left, box_top, box_right, box_bottom))
        scaled = cropped.resize((TARGET_W, TARGET_H), Image.Resampling.NEAREST)
        canvas.paste(scaled, (OFFSET_X, OFFSET_Y))
    else:
        # Full-width bilinear scaling to preserve digit shapes cleanly without clipping edges
        scaled = src.resize((PANEL_W, 14), Image.Resampling.BILINEAR)
        canvas.paste(scaled, (OFFSET_X, 9 + OFFSET_Y))

    return canvas

def main():
    bb = BusyBar(ip=BUSYBAR_IP, token=BUSYBAR_TOKEN)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"Starting BusyRebar bridge: {BUSYBAR_IP} -> {PANEL_IP}:{PANEL_PORT}")
    while True:
        try:
            raw_bytes = bb.get_screen_frame()
            frame = transform_frame(raw_bytes)

            brightness = get_scheduled_brightness()
            if brightness <= 0.0:
                payload = bytes(PANEL_W * PANEL_H * 3)
            else:
                enhancer = ImageEnhance.Brightness(frame)
                adjusted = enhancer.enhance(brightness)
                payload = adjusted.tobytes()

            sock.sendto(payload, (PANEL_IP, PANEL_PORT))
        except Exception as exc:
            print(f"Frame poll/send error: {exc}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()