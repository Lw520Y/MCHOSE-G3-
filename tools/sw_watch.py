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
print("watching: mi00:", bool(mi), "col07:", bool(c7), flush=True)

nmi = nc7 = 0
special_printed = 0
special = {}
t0 = time.time()
last = t0
while time.time() - t0 < 90:
    for h, which in ((mi, "MI"), (c7, "C7")):
        if h is None:
            continue
        try:
            data = h.read(8, 100)
        except OSError:
            time.sleep(0.05)
            continue
        if data:
            if which == "MI":
                nmi += 1
                if data[0] != 0x01 and special_printed < 10:
                    kx = binascii.hexlify(bytes(data)).decode()
                    special[kx] = special.get(kx, 0) + 1
                    special_printed += 1
                    print("SPECIAL MI", kx, flush=True)
            else:
                nc7 += 1
                if special_printed < 10:
                    kx = binascii.hexlify(bytes(data)).decode()
                    special["C7 " + kx] = special.get("C7 " + kx, 0) + 1
                    special_printed += 1
                    print("SPECIAL C7", kx, flush=True)
    if time.time() - last >= 5:
        print(f"t={int(time.time() - t0):3d}s  MI00={nmi}  COL07={nc7}", flush=True)
        last = time.time()

print("total:", {"MI00": nmi, "COL07": nc7})
for kx, n in special.items():
    print(kx, "x", n)
