# g3_tray.pyw — MCHOSE G3 (原始款, 接收器 258A:0138) 免驱动托盘电量
# 协议（本机实测逆向）：COL07 (usage FF02:0002) 输入流
#   09 0a 05 XX ... = 电量 XX%，每 48 秒自发一帧
#   09 0a 02 00 ... = 鼠标休眠事件
#   09 0a 03 01/02  = DPI 键事件（忽略）
import os
import sys
import time
import threading
import logging

import hid
import pystray
from PIL import Image, ImageDraw, ImageFont

VID, PID = 0x258A, 0x0138
STALE_AFTER = 120  # 秒，超过没收到电池帧 -> 图标置灰
LOW_BATTERY = 20

# 打包成 exe 后 __file__ 指向临时解包目录，日志/自启须跟着 exe 本体走
if getattr(sys, "frozen", False):
    SCRIPT = os.path.abspath(sys.executable)
else:
    SCRIPT = os.path.abspath(__file__)
LOG = os.path.join(os.path.dirname(SCRIPT), "g3_tray.log")

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

_state = {"pct": None, "ts": 0.0, "stale": False, "charging": False, "low_sent": False}
_lock = threading.Lock()
_icon = None


def load_font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_icon(pct, stale=False, charging=False):
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if charging:
        color = (30, 136, 229, 255)
        text = str(pct) if pct is not None else "C"
    elif pct is None:
        color, text = (120, 120, 120, 200), "?"
    elif stale:
        color, text = (150, 150, 150, 150), str(pct)
    elif pct <= LOW_BATTERY:
        color, text = (235, 60, 60, 255), str(pct)
    elif pct <= 45:
        color, text = (245, 166, 35, 255), str(pct)
    else:
        color, text = (67, 160, 71, 255), str(pct)
    d.rounded_rectangle([0, 0, 15, 15], radius=4, fill=color)
    text = str(text)
    f = load_font(10 if len(text) <= 2 else 8)
    try:
        w = d.textlength(text, font=f)
        bbox = f.getbbox(text)
        h = bbox[3] - bbox[1]
    except Exception:
        bbox = (0, 0, 10, 9)
        w, h = 10, 9
    # 减去 bbox[0]/bbox[1]，让"字形墨迹"而不是"字模原点"落在正中
    x = int((16 - w) / 2 - bbox[0])
    y = int((16 - h) / 2 - bbox[1])
    d.text((x, y), text, font=f, fill=(255, 255, 255, 255))
    if charging:
        # 右下角小闪电
        d.polygon([(11, 8), (8, 8), (12, 3), (10, 7), (13, 7)], fill=(255, 235, 59, 255))
    return img


def refresh():
    with _lock:
        pct, stale, charging = _state["pct"], _state["stale"], _state["charging"]
    if _icon is None:
        return
    _icon.icon = make_icon(pct, stale, charging)
    if charging:
        shown = f"{pct}%" if pct is not None else "…"
        _icon.title = f"MCHOSE G3 · 充电中（{shown}）· 2.4G"
    elif pct is None:
        _icon.title = "MCHOSE G3 · 等待电量数据…（请确认鼠标电源已开）"
    else:
        suffix = " · 休眠/离线" if stale else ""
        _icon.title = f"MCHOSE G3 · {pct}%{suffix} · 2.4G"
    with _lock:
        low = pct is not None and not stale and not charging and pct <= LOW_BATTERY
        if low and not _state["low_sent"]:
            _state["low_sent"] = True
            try:
                _icon.notify(f"电量只剩 {pct}%，该充电了", "MCHOSE G3")
            except Exception:
                pass
        elif (pct is not None and pct > LOW_BATTERY + 1) or charging:
            _state["low_sent"] = False


def find_col07():
    try:
        for d in hid.enumerate():
            if d["vendor_id"] == VID and d["product_id"] == PID and d.get("usage_page") == 0xFF02:
                return d["path"]
    except Exception:
        pass
    return None


def reader_loop():
    logging.info("reader start")
    while True:
        path = find_col07()
        if path is None:
            with _lock:
                _state["stale"] = True
                need = _state["pct"] is not None and not _state["stale"]
            if need:
                refresh()
            time.sleep(2)
            continue
        try:
            h = hid.device()
            h.open_path(path)
        except Exception as e:
            logging.warning("open fail: %s", e)
            time.sleep(2)
            continue
        logging.info("opened COL07")
        try:
            while True:
                try:
                    data = h.read(8, 1000)
                except OSError:
                    logging.info("read OSError -> reenumerate")
                    break
                now = time.time()
                if data and len(data) >= 4 and data[0] == 0x09:
                    if data[2] == 0x05:
                        val = data[3]
                        with _lock:
                            _state["ts"] = now
                            _state["stale"] = False
                            if val == 0xFF:
                                _state["charging"] = True
                            elif 0 <= val <= 100:
                                _state["charging"] = False
                                _state["pct"] = val
                        logging.info("battery frame val=%d", val)
                        refresh()
                    # 0x02 休眠 / 0x03 DPI 键：忽略
                elif _state["pct"] is not None and now - _state["ts"] > STALE_AFTER:
                    with _lock:
                        was = _state["stale"]
                        _state["stale"] = True
                    if not was:
                        logging.info("no frame for %ds -> stale", STALE_AFTER)
                        refresh()
        except Exception as e:
            logging.warning("loop exc: %s", e)
        try:
            h.close()
        except Exception:
            pass
        time.sleep(2)


# ---- 开机自启（HKCU Run）----
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "MCHOSEG3Battery"


def autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def set_autostart(enable):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enable:
            if getattr(sys, "frozen", False):
                cmd = f'"{SCRIPT}"'
            else:
                pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
                if not os.path.exists(pythonw):
                    pythonw = sys.executable
                cmd = f'"{pythonw}" "{SCRIPT}"'
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except FileNotFoundError:
                pass


def on_exit(icon, item):
    icon.stop()


def main():
    global _icon
    if os.path.exists(LOG) and os.path.getsize(LOG) > 256 * 1024:
        try:
            os.remove(LOG)
        except OSError:
            pass
    menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: "MCHOSE G3 · "
            + ("充电中" if _state["charging"] else (f"{_state['pct']}%" if _state["pct"] is not None else "…")),
            action=None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("开机自启", lambda: set_autostart(not autostart_enabled()),
                         checked=lambda item: autostart_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", on_exit),
    )
    _icon = pystray.Icon("MCHOSEG3", icon=make_icon(None),
                         title="MCHOSE G3 · 等待电量数据…", menu=menu)
    threading.Thread(target=reader_loop, daemon=True).start()
    _icon.run()


if __name__ == "__main__":
    main()
