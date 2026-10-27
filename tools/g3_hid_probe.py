import time
import hid

VID = 0x258A
devs = [d for d in hid.enumerate() if d.get("vendor_id") == VID]
print("devices:", len(devs))
for d in devs:
    print(
        f"path={d['path']!r} vid={d['vendor_id']:04x} pid={d['product_id']:04x} "
        f"iface={d.get('interface_number')} usage={d.get('usage_page'):04x}:{d.get('usage'):04x} "
        f"product={d.get('product_string')!r} mfg={d.get('manufacturer_string')!r} "
        f"release={d.get('release_number')}"
    )

req = bytearray(65)
req[0] = 0x00
req[1:9] = bytes([0x55, 0x30, 0xA5, 0x0B, 0x2E, 0x01, 0x01, 0x01])

for d in devs:
    if d.get("usage_page") != 0xFF01:
        continue
    print("\n--- trying", d["path"], f"usage={d.get('usage_page'):04x}:{d.get('usage'):04x}")
    dev = hid.device()
    try:
        dev.open_path(d["path"])
    except Exception as e:
        print("open failed:", e)
        continue
    try:
        try:
            dev.set_nonblocking(0)
        except Exception:
            pass
        for attempt in range(4):
            try:
                n = dev.write(list(req))
                print(f"write #{attempt}: {n}")
            except Exception as e:
                print(f"write #{attempt} failed: {e}")
            deadline = time.time() + 1.0
            while time.time() < deadline:
                try:
                    data = dev.read(65, timeout_ms=250)
                except Exception as e:
                    print("read failed:", e)
                    data = None
                if data:
                    print("read:", " ".join(f"{b:02x}" for b in data))
                    if len(data) >= 10 and data[0] == 0xAA and data[1] == 0x30:
                        print("FOUND level=", data[8], "charge=", data[9])
                        raise SystemExit
            time.sleep(0.1)
    finally:
        try:
            dev.close()
        except Exception:
            pass
