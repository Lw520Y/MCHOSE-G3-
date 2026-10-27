# make_exe_icon.py — 生成打包用的 icon.ico（256/64/48/32/16 五档尺寸）
# 造型与托盘图标同风格：圆角电池 + 绿色电量，输出到仓库根目录 icon.ico
import os

from PIL import Image, ImageDraw

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

GRAY = (70, 70, 70, 255)
GREEN = (67, 160, 71, 255)

# 正极头 + 电池身
d.rounded_rectangle([100, 20, 156, 56], radius=12, fill=GRAY)
d.rounded_rectangle([56, 44, 200, 232], radius=24, outline=GRAY, width=16)
# 电量（约 75%）
d.rounded_rectangle([84, 104, 172, 204], radius=10, fill=GREEN)

out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "icon.ico")
img.save(out, sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
print("saved:", out)
