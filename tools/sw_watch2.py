import binascii
import time

import hid

VID, PID = 0x258A, 0x0138


def open_by(pred):
    for d in hid.enumerate():
        if d["vendor_id"] == VID and d["product_id"] == PID and pred(d):
            try:
                h = hid.device()
                h.open_path(d["path"])
                return h
            except Exception:
                return None
    return None


mi = open_by(lambda d: d.get("usage_page") == 1 and d.get("usage") == 2)
c7 = open_by(lambda d: d.get("usage_page") == 0xFF02)
print("watch2: mi00:", bool(mi), "col07:", bool(c7), flush=True)
print("PHASE 1 (t=0-120s): use the mouse - move, click, press DPI short and long", flush=True)
print("PHASE 2 (t=120-180s): hands off, let it idle", flush=True)

nmi = 0
phase = 1
t0 = time.time()
last_hb = t0
while time.time() - t0 < 180:
    if c7 is not None:
        try:
            data = c7.read(8, 50)
        except OSError:
            data = None
        if data:
            print(f"C7 t={time.time() - t0:6.1f}s {binascii.hexlify(bytes(data)).decode()}", flush=True)
    if mi is not None:
        try:
            data = mi.read(8, 50)
        except OSError:
            data = None
        if data:
            nmi += 1
    if time.time() - last_hb >= 15:
        print(f"HB t={int(time.time() - t0):3d}s MI00_total={nmi}", flush=True)
        last_hb = time.time()
    if t0 + 120 <= time.time() and phase != 2:
        phase = 2
        print("PHASE 2 begins: hands off the mouse from now", flush=True)
print("end MI00 total:", nmi)
