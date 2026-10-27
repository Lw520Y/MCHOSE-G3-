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
                p = str(d["path"]).upper()
                col = next((k for k in FEAT_LEN if k in p), "COL0?")
                out.append((col, d))
    return out


targets = find_targets()
print("collections:", [(c, f"{d['usage_page']:04x}:{d['usage']:04x}") for c, d in targets])

good = {}
for col, d in targets:
    length = FEAT_LEN.get(col, 8)
    hits = []
    try:
        h = hid.device()
        h.open_path(d["path"])
    except Exception as e:
        print(f"{col}: open fail {e}")
        continue
    for rid in range(0x00, 0x21):
        try:
            data = h.get_feature_report(rid, length)
        except Exception:
            continue
        if data:
            hits.append(rid)
            hx = binascii.hexlify(bytes(data[:32])).decode()
            tag = "DATA" if any(b != 0 for b in data) else "ZERO"
            print(f"{col} rid {rid:02x}: {tag} {hx}")
    h.close()
    good[col] = hits
print("GOOD:", good)

for col, d in targets:
    length = FEAT_LEN.get(col, 8)
    for rid in good.get(col, []):
        try:
            h = hid.device()
            h.open_path(d["path"])
        except Exception as e:
            print(f"{col} rid {rid:02x}: reopen fail {e}")
            break
        print(f"--- {col} rid {rid:02x} repeated reads (5x, 0.4s gap) ---")
        for i in range(5):
            try:
                data = h.get_feature_report(rid, length)
                print(f"  #{i}: {binascii.hexlify(bytes(data[:32])).decode() if data else 'FAIL'}")
            except Exception as e:
                print(f"  #{i}: EXC {e}")
            time.sleep(0.4)
        h.close()

print("=== passive input listen 5s ===")
handles = []
for col, d in targets:
    try:
        h = hid.device()
        h.open_path(d["path"])
        h.set_nonblocking(1)
        handles.append([col, h, True])
    except Exception:
        pass
mi00 = None
for d in hid.enumerate():
    if d["vendor_id"] == VID and d["product_id"] == PID and d.get("usage_page") == 0x01 and d.get("usage") == 0x02:
        mi00 = d
        try:
            h = hid.device()
            h.open_path(d["path"])
            h.set_nonblocking(1)
            handles.append(["MI00", h, True])
        except Exception:
            pass

counts, first = {}, {}
t0 = time.time()
while time.time() - t0 < 5.0:
    for ent in handles:
        col, h, alive = ent
        if not alive:
            continue
        try:
            data = h.read(64)
        except OSError:
            ent[2] = False
            continue
        if data:
            counts[col] = counts.get(col, 0) + 1
            first.setdefault(col, binascii.hexlify(bytes(data)).decode())
    time.sleep(0.002)
for col, h, alive in handles:
    print(f"  {col}: {counts.get(col, 0)} frames first={first.get(col, '-')} alive={alive}")

print("=== G3-web cmd write attempt ===")
cmd = [0x00, 0x55, 0x30, 0xA5, 0x0B, 0x2E, 0x01, 0x01, 0x01] + [0x00] * 56
write_targets = list(targets) + (["MI00", mi00] if mi00 else [])
for col, d in write_targets:
    try:
        h = hid.device()
        h.open_path(d["path"])
        print(f"  write {col}: {h.write(cmd)}")
        h.close()
    except Exception as e:
        print(f"  write {col}: EXC {e}")
t0 = time.time()
seen = {}
while time.time() - t0 < 1.5:
    for col, h, alive in handles:
        if not alive:
            continue
        try:
            data = h.read(64)
        except OSError:
            continue
        if data:
            seen.setdefault(col, binascii.hexlify(bytes(data)).decode())
for k in sorted(seen):
    print(f"  resp {k}: {seen[k]}")
print("done")
