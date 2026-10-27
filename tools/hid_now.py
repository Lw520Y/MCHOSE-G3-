import hid

devs = hid.enumerate()
print("total HID interfaces:", len(devs))
watch = {
    0x258A: "SINO-WEALTH",
    0x3554: "HOLTEK",
    0x0C45: "SONIX",
    0x0BDA: "REALTEK",
    0xA8A5: "MCHOSE-G7",
    0x2023: "MCHOSE-A5",
    0x5253: "MCHOSE-52",
    0x3837: "MCHOSE-3837",
}
for d in devs:
    v, p = d["vendor_id"], d["product_id"]
    tag = watch.get(v, "")
    up, u = d.get("usage_page", 0), d.get("usage", 0)
    if tag or up in (0xFF00, 0xFF01, 0xFF02):
        ps = d.get("product_string") or "-"
        print(f"{v:04x}:{p:04x} {tag:<12} usage {up:04x}:{u:04x} product={ps}")
print("done")
