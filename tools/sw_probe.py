import binascii
import time

import hid

VID, PID = 0x258A, 0x0138
FEAT_LEN = {"COL04": 8, "COL05": 1032, "COL06": 8, "COL07": 520}


def find_targets():
    out = []
    for d in hid.enumerate():
        if d["vendor_id"] == VID and d["product_id"] == PID:
            up = d.get("usage_page", 0)
            if up in (0xFF00, 0xFF01, 0xFF02):
                path = str(d["path"]).upper()
                col = "COL0?"
                for k in FEAT_LEN:
                    if k in path:
                        col = k
                        break
                out.append((col, d))
    return out


# 1) wait for receiver to appear (max 90 s)
print("waiting for 258A:0138 receiver (max 90s)...")
deadline = time.time() + 90
targets = []
while time.time() < deadline:
    targets = find_targets()
    if targets:
        break
    time.sleep(1)

if not targets:
    print("TIMEOUT: receiver did not appear within 90s")
    raise SystemExit(1)

print("receiver present, vendor collections:")
for col, d in targets:
    print(f"  {col} usage {d['usage_page']:04x}:{d['usage']:04x} path={d['path']}")

# 2) blind GET_FEATURE scan (pure read-only), report ids 0x00..0x20
summary = {}
for col, d in targets:
    print(f"\n=== {col} blind GET_FEATURE scan ===")
    length = FEAT_LEN.get(col, 8)
    nonzero = 0
    zero_ok = 0
    fail = 0
    try:
        h = hid.device()
        h.open_path(d["path"])
    except Exception as e:
        print("  open failed:", e)
        continue
    for rid in range(0x00, 0x21):
        try:
            data = h.get_feature_report(rid, length)
        except Exception as e:
            print(f"  rid {rid:02x}: EXC {e}")
            fail += 1
            continue
        if data:
            if any(b != 0 for b in data):
                nonzero += 1
                print(f"  rid {rid:02x}: {len(data)}B {binascii.hexlify(bytes(data[:24])).decode()}")
            else:
                zero_ok += 1
        else:
            fail += 1
    h.close()
    summary[col] = (nonzero, zero_ok, fail)
    print(f"  -> nonzero={nonzero} zero-data-ok={zero_ok} failed={fail}")

# 3) passive input listen 4s (user should be moving the mouse)
print("\n=== passive input listen 4s (move the mouse!) ===")
handles = []
for col, d in targets + [("MICE", x) for c, x in []]:
    try:
        h = hid.device()
        h.open_path(d["path"])
        h.set_nonblocking(1)
        handles.append((col, h))
    except Exception:
        pass

# also listen on the mouse core interface MI_00 (usage 0100:0002)
for d in hid.enumerate():
    if d["vendor_id"] == VID and d["product_id"] == PID and d.get("usage") == 0x02 and d.get("usage_page") == 0x01:
        try:
            h = hid.device()
            h.open_path(d["path"])
            h.set_nonblocking(1)
            handles.append(("MI00", h))
        except Exception:
            pass

counts = {}
first = {}
t0 = time.time()
while time.time() - t0 < 4.0:
    for col, h in handles:
        data = h.read(64)
        if data:
            counts[col] = counts.get(col, 0) + 1
            if col not in first:
                first[col] = binascii.hexlify(bytes(data)).decode()
    time.sleep(0.002)

for col, _ in handles:
    print(f"  {col}: {counts.get(col, 0)} frames, first={first.get(col, '-')}")

# 4) one shot: official web-driver battery command as output report, then 1s listen
print("\n=== try G3-web command (00 55 30 A5 0B 2E 01 01 01) via write(), 1s listen ===")
cmd = [0x00, 0x55, 0x30, 0xA5, 0x0B, 0x2E, 0x01, 0x01, 0x01] + [0x00] * 56
for col, d in targets:
    try:
        h = hid.device()
        h.open_path(d["path"])
        n = h.write(cmd)
        print(f"  write on {col}: {n}")
        h.close()
    except Exception as e:
        print(f"  write on {col}: EXC {e}")

t0 = time.time()
seen = {}
while time.time() - t0 < 1.0:
    for col, h in handles:
        data = h.read(64)
        if data:
            hx = binascii.hexlify(bytes(data)).decode()
            if col not in seen:
                seen[col] = hx
            counts[col] = counts.get(col, 0) + 1
for col in sorted(seen):
    print(f"  {col}: {seen[col]}")
print("done")
