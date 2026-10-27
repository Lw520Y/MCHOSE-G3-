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


c7 = open_by(lambda d: d.get("usage_page") == 0xFF02)
print("col07:", bool(c7), flush=True)
t0 = time.time()
counts = {}
while time.time() - t0 < 180:
    if c7 is None:
        time.sleep(1)
        c7 = open_by(lambda d: d.get("usage_page") == 0xFF02)
        continue
    try:
        data = c7.read(8, 100)
    except OSError:
        print("read OSError -> reopen", flush=True)
        c7 = None
        continue
    if data:
        kx = binascii.hexlify(bytes(data)).decode()
        counts[kx] = counts.get(kx, 0) + 1
        print(f"t={time.time() - t0:6.1f}s {kx}", flush=True)
print("counts:")
for kx, n in sorted(counts.items()):
    print(f"  {kx} x{n}")
