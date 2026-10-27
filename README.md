# MCHOSE G3 电量托盘（免驱动）

不装迈丛官方驱动 / M HUB，在 Windows 托盘常驻显示 MCHOSE G3 鼠标的实时电量。

一个约 200 行的 Python 小程序：托盘彩色数字图标 + 充电状态 + 低电提醒 + 开机自启，零安装、零管理员权限。

> 协议是纯手工逆向的：原始款 G3 的接收器（258A:0138，SINO WEALTH 方案）没有任何公开资料，现有开源工具（mchose-linux 等）均不支持该型号。本项目的帧格式说明见[工作原理](#工作原理)一节，全部探测脚本归档在 [`tools/`](tools/)。**本项目为非官方第三方工具，与迈丛（MCHOSE）无关**，详见文末[声明](#声明)。

## 功能

- 每 48 秒自动接收鼠标上报的电量，托盘图标实时显示百分比
- 插线充电 → 蓝色图标 + 闪电角标，悬停显示"充电中"
- 鼠标休眠 / 离线 → 图标置灰，恢复后自动变回
- 电量 ≤20% 弹气泡提醒（不重复刷屏）
- 右键菜单：开机自启（HKCU 注册表，无 UAC）、退出

## 适用设备

| | |
|---|---|
| ✅ 支持 | MCHOSE G3 原始款（2.4G 接收器，USB VID/PID = `258A:0138`，产品名 "Wireless Mouse"，厂商 SINO WEALTH） |
| ❌ 不适用 | G3 V2 / V3 / Ultra 等新款（Realtek `0BDA` 或 `3837` 方案，协议完全不同，可参考 [mchose-linux](https://github.com/alexfrih/mchose-linux)） |
| ❌ 不适用 | 蓝牙模式（蓝牙走标准 GATT 电量服务，Windows 系统自带显示） |

不确定自己的接收器型号？插上后跑一下 `tools/hid_now.py`，看有没有 `258a:0138`。

## 环境要求与安装

- Windows 10 / 11
- Python 3.8+（任意发行版，需含 `pythonw.exe`）

```bat
pip install hidapi pystray pillow
```

## 使用方法

1. 双击 `g3_tray.pyw`（或打包好的 `dist\MCHOSEG3Battery.exe`，见[打包为 EXE](#打包为-exe可选)），托盘出现灰色 `?` 图标
2. 等待第一帧电量，图标最长 **48 秒**内变为数字。这不是卡住：鼠标固件每 48 秒才自发上报一帧电量，脚本纯被动监听，启动后要等鼠标下一次"到点"上报（平均约 24 秒），期间悬停提示"等待电量数据…"
3. 右键托盘图标 → 勾选 **开机自启**，从此开机自动运行，无需再管

### 图标图例

| 图标 | 含义 |
|---|---|
| 🟩 绿色数字 | 正常，电量 ≥45% |
| 🟧 橙色数字 | 21–44%，留意 |
| 🟥 红色数字 | ≤20%，弹气泡提醒 |
| 🟦 蓝色数字 + ⚡ | 充电中 |
| ⬜ 灰色数字 | 鼠标休眠 / 离线 / 关机（仍显示最后读数；超过 120 秒没收到电量帧才置灰，唤醒后随下一次上报、最长 48 秒恢复彩色） |
| ❓ 灰色 ? | 刚启动，尚未收到数据 |

### 运行日志

脚本同目录会生成 `g3_tray.log`，记录接收器连接与每一帧读数，排查问题先看它。日志超过 256 KB 会自动清空重建，不会无限膨胀。

### 卸载

1. 右键托盘图标 → 取消勾选 **开机自启**（或删除注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 下的 `MCHOSEG3Battery` 项）
2. 退出程序，删除整个目录即可，无其他残留

## 打包为 EXE（可选）

不想装 Python 环境，可以打成单个 exe 自用或分发：

1. 双击 `build_exe.bat`（等价于执行 `pyinstaller --noconfirm --clean --onefile --windowed --name MCHOSEG3Battery --icon icon.ico --hidden-import pystray._win32 g3_tray.pyw`）
2. 产物 `dist\MCHOSEG3Battery.exe`，约 28 MB，免安装、双击即用，托盘图标、充电显示、开机自启与脚本版行为一致

exe 模式与脚本版的差异：日志生成在 **exe 同目录**；开机自启注册的是 **exe 本身路径**。改完脚本重新跑一次 `build_exe.bat` 即可，图标可用 `tools/make_exe_icon.py` 重新生成。

## 工作原理

G3 原始款的 2.4G 接收器是 SINO WEALTH（鑫联胜）方案，HID 拓扑如下：

```
258A:0138 (USB Composite Device)
├── MI_00        鼠标（usage 0100:0002，标准移动/按键流）
└── MI_01
    ├── Col01-03 键盘 / 消费类（usage 0100:0006 / 000C:0001）
    ├── Col04    FF00:0001  feature 8B   ← 静态字符串（产品名碎片）
    ├── Col05    FF00:0001  feature 1032B ← 无响应
    ├── Col06    FF01:0001  feature 8B   ← 静态设备信息（06 a0 02 89 f2 e4 8f 00）
    └── Col07    FF02:0002  input 8B     ← ★ 状态通道，电池帧从这里来
```

**鼠标主动上报，插件纯被动监听**，不需要发送任何命令（发送通道实测也全是关闭的：vendor 集合无 output report，256 个 feature report ID 盲扫只有两处静态只读数据）。

### 状态帧格式（Col07 输入流，8 字节）

| 帧格式 | 含义 |
|---|---|
| `09 0a 05 XX 00 00 00 00` | 电量 = XX%（0–100），每 **48 秒**一帧 |
| `09 0a 05 FF 00 00 00 00` | 充电中（固件哨兵值，充电期间不报百分比） |
| `09 0a 02 00 00 00 00 00` | 鼠标进入休眠 |
| `09 0a 03 01 / 02 …` | DPI 键按下 / 释放事件 |

注：G3 的 USB-C 口是纯充电口（无数据线），插线充电不产生新 USB 设备、不切换有线模式，充电状态同样经 2.4G 空口上报。

### 逆向过程（对应 tools/ 脚本）

1. **拔插验证**确认 258A:0138 就是 G3 接收器（`sw_watch.py` 前后对照枚举）
2. **全量盲扫** 256 个 feature report ID（`sw_probe*.py`）——只有两处静态数据，确认没有可用的查询命令
3. **被动监听** Col07 输入流（`sw_watch*.py`）——发现自发电池帧，数出 48 秒周期
4. **充电对照实验**（`sw_watch3.py`）——识别 0xFF 充电哨兵值
5. 刻度验证：充电前 93% → 充电后 92%，±1 属固件估算抖动

### tools/ 目录一览

`tools/` 归档了逆向全程的探测脚本，命名前缀对应阶段：`hid_`/`g3_` = 确认设备是谁，`sw_`（SINO WEALTH）= 摸清协议，编号为迭代轮次。

| 脚本 | 用途 |
|---|---|
| `hid_probe.ps1` | PowerShell 直调 Windows HID API，枚举设备、读厂商/产品字符串与 Capabilities |
| `hid_desc.ps1` | 读 HID 报告描述符，摸清各接口的 usage 与报文长度 |
| `g3_probe.ps1` / `g3_probe_current.ps1` | 尝试 `HidD_GetFeature` / `GetInputReport`，探测有无主动查询通道 |
| `hid_now.py` | 列出当前全部 HID 设备并按 VID 标注厂商，不确定接收器型号就跑它 |
| `g3_hid_probe.py` | 仅枚举 258A 的接口，查看接收器 HID 拓扑 |
| `sw_probe.py` / `2` / `3` | feature report 三轮盲扫：全为静态只读，无查询命令，只能被动监听 |
| `sw_watch.py` / `2` | 被动监听 Col07 输入流：抓到自发电池帧，数出 48 秒周期与休眠事件帧 |
| `sw_watch3.py` | 充电对照实验，确认 `0xFF` 充电哨兵 |
| `make_exe_icon.py` | 生成 exe 图标 `icon.ico`（打包辅助，非逆向） |

## 故障排查

| 现象 | 处理 |
|---|---|
| 刚启动几十秒不出数字 | 正常现象：鼠标每 48 秒才上报一帧，最长等约 48 秒，详见[使用方法](#使用方法) |
| 图标一直是灰色 `?` | 确认鼠标电源已开、接收器插好；跑 `tools/sw_watch.py` 看有没有帧 |
| 找不到托盘图标 | Windows 11 默认收进任务栏 `^` 折叠区，点小箭头找 |
| 充电时不显示实时百分比 | 固件限制（0xFF 哨兵值），拔线后恢复 |
| 双击无反应 | 看同目录 `g3_tray.log`；确认 `pip install hidapi pystray pillow` 已执行 |
| 读数和实际不符 | 电量百分比由固件按电压估算，±2% 内属正常 |

## 已知限制

- 仅支持 2.4G 模式的原始款 G3
- 充电中无法显示实时百分比（固件不报）
- 电量为固件电压估算值，非精确计量
- 休眠/离线是超时判定：置灰要等约 2 分钟（120 秒无帧），恢复最长要等 48 秒

## 项目结构

```
MCHOSE-G3/
├── g3_tray.pyw        主程序：托盘常驻、HID 监听与图标渲染
├── build_exe.bat      一键打包 dist/MCHOSEG3Battery.exe
├── icon.ico           exe 图标（由 tools/make_exe_icon.py 生成）
├── README.md / LICENSE / .gitignore
└── tools/             逆向探测脚本归档，见「tools/ 目录一览」
```

`dist/` 与 `g3_tray.log` 为运行产物，不入库。

## 参考

- [alexfrih/mchose-linux](https://github.com/alexfrih/mchose-linux) —— 迈丛 5253/3837 家族（L7/M7/A7/K7 等）协议文档，明确不覆盖原始 G3
- [Dk000t/MCHOSEWaybarBattery](https://github.com/Dk000t/MCHOSEWaybarBattery) —— 通过网页驱动抓电量的另一思路
- [迈丛官网](https://www.mchose.com.cn/) —— 官方网页驱动（仅支持新款 G3）

## 声明

- 本项目为非官方的第三方小工具，与迈丛（MCHOSE）及其官方驱动 M HUB 无任何关联
- 仅被动读取用户自有设备经 2.4G 主动上报的 HID 数据：不发送指令、不修改固件、不分发任何厂商软件
- 协议帧格式为个人实测观察所得；使用、修改与分发的条件以文末 [MIT 许可证](LICENSE)为准

## 许可证

本项目以 [MIT License](LICENSE) 开源：可自由使用、修改、分发（含商用），唯一要求是在副本中保留原版权声明。软件按"现状"提供，作者不对使用结果作任何担保。
