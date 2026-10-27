import binascii
import time

import hid

VID, PID = 0x258A, 0x0138
LENS = {"COL04": 8, "COL05": 1032, "COL06": 8, "COL07": 520}


def targets():
    out = []
    for d in hid.enumerate():
        if d["vendor_id"] == VID and d["product_id"] == PID:
            up = d.get("usage_page", 0)
            if up in (0xFF00, 0xFF01, 0xFF02):
                p = str(d["path"]).upper()
                col = next((k for k in LENS if k in p), None)
                if col:
                    out.append((col, d))
    return out


def mi00_dev():
    for d in hid.enumerate():
        if d["vendor_id"] == VID and d["product_id"] == PID and d.get("usage_page") == 1 and d.get("usage") == 2:
            return d
    return None


ts = targets()
m0 = mi00_dev()
print("vendor:", [(c, f"{d['usage_page']:04x}:{d['usage']:04x}") for c, d in ts], "mi00:", bool(m0))

# 1) extended blind scan, all 256 report ids
print("=== extended GET_FEATURE scan 0x00-0xFF ===")
for col, d in ts:
    L = LENS[col]
    try:
        h = hid.device()
        h.open_path(d["path"])
    except Exception as e:
        print(col, "open fail", e)
        continue
    hits = []
    for rid in range(0x100):
        try:
            data = h.get_feature_report(rid, L)
        except Exception:
            continue
        if data:
            hits.append(rid)
            if any(b != 0 for b in data):
                print(f"  {col} rid {rid:02x}: {binascii.hexlify(bytes(data[:24])).decode()}")
    h.close()
    print(f"  {col} responding ids: {[hex(r) for r in hits]}")

# 2) MI00 stream capture 12s (blocking reads)
print("=== MI00 stream 12s: user should MOVE + CLICK + press DPI button ===")
if m0:
    h = None
    try:
        h = hid.device()
        h.open_path(m0["path"])
    except Exception as e:
        print("  mi00 open fail", e)
    if h:
        byid = {}
        special = {}
        t0 = time.time()
        while time.time() - t0 < 12:
            try:
                data = h.read(8, 100)
            except OSError:
                time.sleep(0.2)
                continue
            if data:
                rid = data[0]
                byid[rid] = byid.get(rid, 0) + 1
                if rid != 0x01:
                    kx = binascii.hexlify(bytes(data)).decode()
                    special[kx] = special.get(kx, 0) + 1
        h.close()
        print("  frames by report id:", {hex(k): v for k, v in sorted(byid.items())})
        print(f"  non-movement frames: {len(special)} distinct")
        for kx, n in list(special.items())[:30]:
            print(f"  {kx} x{n}")

# 3) set/get feature command probes (read-intent commands only)
print("=== set/get feature command probes ===")
inv = lambda bs: bytes(b ^ 0xFF for b in bs)


def probe(cd, rid, payload, getlen):
    col, d = cd
    out = []
    try:
        h = hid.device()
        h.open_path(d["path"])
    except Exception as e:
        return f"open fail {e}"
    try:
        n = h.send_feature_report(bytes(payload))
        out.append(f"set={n}")
    except Exception as e:
        out.append(f"setEXC {e}")
    try:
        data = h.get_feature_report(rid, getlen)
        out.append("get=" + (binascii.hexlify(bytes(data[:24])).decode() if data else "none"))
    except Exception as e:
        out.append(f"getEXC {e}")
    h.close()
    return " ".join(out)


byc = {c: (c, d) for c, d in ts}
cmd06 = bytes([0x06, 0x87, 0x00, 0x00, 0x01, 0x00, 0x02, 0x00])

if "COL06" in byc:
    print("COL06 0a<-0a 06 zeros:", probe(byc["COL06"], 0x0A, [0x0A, 0x06] + [0] * 6, 8))
    print("COL06 0a<-0a 07 zeros:", probe(byc["COL06"], 0x0A, [0x0A, 0x07] + [0] * 6, 8))
    print("COL06 0a<-0a 00 zeros:", probe(byc["COL06"], 0x0A, [0x0A] + [0] * 7, 8))
if "COL04" in byc:
    print("COL04 06<-06 87...:", probe(byc["COL04"], 0x06, list(cmd06), 8))
    print("COL04 05<-06 87...:", probe(byc["COL04"], 0x05, list(cmd06), 8))
for name in ("COL05", "COL07"):
    if name not in byc:
        continue
    cd = byc[name]
    L = LENS[name]
    p11i = bytes([0x11]) + inv(cmd06 + bytes(12))
    p12i = bytes([0x12]) + inv(cmd06 + bytes(55))
    p12p = bytes([0x12]) + cmd06 + bytes(55)
    print(f"{name} 11<-inv06 20B:", probe(cd, 0x11, list(p11i), L))
    print(f"{name} 12<-inv06 64B:", probe(cd, 0x12, list(p12i), L))
    print(f"{name} 12<-plain06 64B:", probe(cd, 0x12, list(p12p), L))

print("done")
