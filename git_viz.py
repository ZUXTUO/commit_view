#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import svgwrite
from git import Repo
from collections import defaultdict
import datetime
import random
import colorsys

# ===========================================================
# 工具函数
# ===========================================================
# random_color: 为分支生成随机的柔和颜色，用于区分不同分支线路与节点
# shorten: 将提交信息过长的文本进行截断，避免节点文本溢出

def random_color():
    h = random.random()
    s = 0.85
    v = 0.95
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return svgwrite.utils.rgb(int(r * 255), int(g * 255), int(b * 255))

def shorten(text, maxlen=40):
    return text if len(text) <= maxlen else text[:maxlen] + "..."

def get_intersect(x1, y1, x2, y2, w, h):
    """
    计算从 (x1, y1) 到 (x2, y2) 的线段与以 (x1, y1) 为中心、宽高为 w, h 的矩形的交点。
    返回交点坐标 (ix, iy)。
    """
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        return x1, y1
        
    # 矩形半宽半高
    hw = w / 2.0
    hh = h / 2.0
    
    # 计算斜率与矩形对角线斜率的比较
    # 矩形边界：x = +/- hw, y = +/- hh
    # 射线参数方程：x = x1 + t*dx, y = y1 + t*dy
    # 我们需要找到最小的正 t，使得点在矩形边界上
    
    t_min = float('inf')
    
    if dx != 0:
        t_x = hw / abs(dx)
        t_min = min(t_min, t_x)
        
    if dy != 0:
        t_y = hh / abs(dy)
        t_min = min(t_min, t_y)
        
    return x1 + dx * t_min, y1 + dy * t_min

# ===========================================================
# 读取 Git 仓库
# ===========================================================
# 从当前工作目录加载 Git 仓库，确保不是“空仓库（bare）”

repo = Repo(os.getcwd())
assert not repo.bare, "不是一个 Git 仓库！"

commits = list(repo.iter_commits("--all"))
print(f"[1/6] 已加载 Git 仓库，共找到 {len(commits)} 个提交")

# 将提交按时间升序排列（最早的在前），用于蛇形布局的顺序遍历
commits.sort(key=lambda c: c.committed_datetime)

# 建立提交到分支名的映射（commit -> branch），用于为边与节点着色
branch_map = {}
for b in repo.branches:
    for c in repo.iter_commits(b.name):
        branch_map[c.hexsha] = b.name

# 分支颜色字典：每个分支一个随机颜色，提升可读性
branch_colors = defaultdict(random_color)

branch_names = [b.name for b in repo.branches]
try:
    MAIN_BRANCH = repo.active_branch.name
except Exception:
    MAIN_BRANCH = 'main' if 'main' in branch_names else (
        'master' if 'master' in branch_names else (
            repo.head.reference.name if hasattr(repo.head, 'reference') else None
        )
    )

# ===========================================================
# 构建提交图的邻接关系（父子关系）
# ===========================================================
# child_map: 提交 -> 其父提交列表
# parent_map: 提交 -> 其子提交列表

child_map = defaultdict(list)    # sha -> [parents]
parent_map = defaultdict(list)   # sha -> [children]

for c in commits:
    sha = c.hexsha

    for p in c.parents:
        parent_map[p.hexsha].append(sha)
        child_map[sha].append(p.hexsha)

# ===========================================================
# 布局计算（蛇形换行布局）
# ===========================================================
# 采用左右来回的蛇形方式进行排布：
# - 在一行内向右移动直到到达右边界，然后换行并向左移动；
# - 到达左边界时再换行并向右移动。
# 为防止节点越出图像范围，设置左右边界并在换行时重置 x 坐标。

NODE_W = 350     # 节点宽度
NODE_H = 80      # 节点高度
H_MARGIN = 100   # 节点水平间距（增加间距以显示连线）
V_MARGIN = 50    # 节点垂直间距

NODE_COLOR_MAIN = "#102a6e"
NODE_COLOR_BRANCH = "#5b2a86"
EDGE_COLOR = "#c8a2ff"

LEFT_BOUND = 100         # 左边界（起始 x）
TOP_BOUND = 100          # 上边界（起始 y）
WRAP_WIDTH = 1500        # 换行宽度
RIGHT_BOUND = LEFT_BOUND + WRAP_WIDTH  # 右边界

direction = 1            # 1 表示向右，-1 表示向左
x = LEFT_BOUND
y = TOP_BOUND

positions = {}   # sha -> (x, y)
max_x = 100      # 记录内容区域的最大 x（用于计算画布大小）
max_y = 100      # 记录内容区域的最大 y（用于计算画布大小）

print("[2/6] 正在计算节点布局...")
total_commits = len(commits)
log_step = max(10, total_commits // 10)

for index, c in enumerate(commits):
    if (index + 1) % log_step == 0 or (index + 1) == total_commits:
        print(f"    - 布局计算进度: {index + 1}/{total_commits}")
    sha = c.hexsha

    positions[sha] = (x, y)
    # 使用节点右下角来计算最大范围，避免节点被裁剪出图像之外
    max_x = max(max_x, x + NODE_W)
    max_y = max(max_y, y + NODE_H)

    # 蛇形移动与换行逻辑
    if direction == 1:
        x += NODE_W + H_MARGIN
        if x > RIGHT_BOUND:
            direction = -1
            y += NODE_H + V_MARGIN
            x = RIGHT_BOUND
    else:
        x -= NODE_W + H_MARGIN
        if x < LEFT_BOUND:
            direction = 1
            y += NODE_H + V_MARGIN
            x = LEFT_BOUND

# ===========================================================
# 创建 SVG 画布
# ===========================================================

CANVAS_W = max_x + 500
CANVAS_H = max_y + 500

print(f"[3/6] 正在创建 SVG 画布 ({CANVAS_W}x{CANVAS_H})...")
dwg = svgwrite.Drawing("git_history.svg",
                       size=(CANVAS_W, CANVAS_H),
                       profile='full')

# 视觉效果定义
bg_grad = dwg.linearGradient(start=(0, 0), end=(0, 1), id="bgGrad")
bg_grad.add_stop_color(0, "#0a0f1e")
bg_grad.add_stop_color(1, "#000000")
dwg.defs.add(bg_grad)

# 银河渐变与旋转动效（仅作用于背景图层，不影响文字与节点）
galaxy_grad = dwg.radialGradient(id="galaxyGrad", cx="50%", cy="50%", r="65%")
galaxy_grad.add_stop_color(0, "#193b8c")
galaxy_grad.add_stop_color(0.5, "#6a1e9a")
galaxy_grad.add_stop_color(1, "#000000")
dwg.defs.add(galaxy_grad)

dwg.defs.add(dwg.style(
    ".flow-line{stroke-dasharray:10 20;stroke-linecap:round;animation:flow 1s linear infinite}"
    "@keyframes flow{to{stroke-dashoffset:-30}}"
))

# 箭头定义（用于指示由父提交指向子提交的方向）
arrow = dwg.marker(id="arrowHead", insert=(10, 5), size=(10, 10), orient="auto")
arrow.add(dwg.path(d="M0,0 L10,5 L0,10 L3,5 Z", fill=EDGE_COLOR))
dwg.defs.add(arrow)

# 背景（深色主题）
dwg.add(dwg.rect(insert=(0, 0),
                 size=(CANVAS_W, CANVAS_H),
                 fill="url(#bgGrad)"))

# 星光点缀
for _ in range(200):
    sx = random.uniform(0, CANVAS_W)
    sy = random.uniform(0, CANVAS_H)
    r = random.uniform(0.4, 1.6)
    dwg.add(dwg.circle(center=(sx, sy), r=r, fill="#FFFFFF", opacity=random.uniform(0.2, 0.6)))

# 银河主体（在画布中心，低不透明度，随时间旋转）
cx = CANVAS_W / 2
cy = CANVAS_H / 2
galaxy = dwg.g(id="galaxy", transform=f"translate({cx},{cy})")
galaxy.add(dwg.ellipse(center=(0, 0),
                       r=(CANVAS_W * 0.35, CANVAS_H * 0.18),
                       fill="url(#galaxyGrad)",
                       opacity=0.25))
for scale, color in [(0.22, "#a0c4ff"), (0.30, "#b794f6"), (0.38, "#7dd3fc")]:
    galaxy.add(dwg.circle(center=(0, 0),
                          r=min(CANVAS_W, CANVAS_H) * scale * 0.5,
                          fill="none",
                          stroke=color,
                          stroke_width=1.2,
                          opacity=0.6))
dwg.add(galaxy)

# ===========================================================
# 分层绘制：连线 -> 节点背景 -> 节点文字
# ===========================================================

# 1. 绘制连线（在最底层，带光晕）
# 连线绘制在节点之前，这样从节点中心出发的连线会被节点背景自然覆盖，
# 从而无需复杂的交点计算即可实现完美的视觉连接（特别是水平连线）。
CURVE_MARGIN = 150  # 转弯曲线的控制点距离
CENTER_X_THRESHOLD = (LEFT_BOUND + RIGHT_BOUND) / 2 + NODE_W / 2

print("[4/6] 正在绘制连线...")
for index, c in enumerate(commits):
    if (index + 1) % log_step == 0 or (index + 1) == total_commits:
        print(f"    - 连线绘制进度: {index + 1}/{total_commits}")
    sha = c.hexsha
    x1, y1 = positions[sha]
    cx1 = x1 + NODE_W/2
    cy1 = y1 + NODE_H/2

    for parent_sha in child_map[sha]:
        if parent_sha not in positions:
            continue

        x2, y2 = positions[parent_sha]
        cx2 = x2 + NODE_W/2
        cy2 = y2 + NODE_H/2
        
        # 连线路由逻辑
        is_same_row = abs(y1 - y2) < 10
        is_vertical_aligned = abs(x1 - x2) < 10
        
        if is_same_row:
            # 水平直线：从父节点中心 -> 子节点边缘
            # 强制使用水平坐标，避免浮点误差
            start_pt = (cx2, cy2)
            if x1 > x2: # 子节点在右侧
                end_pt = (x1, cy1) # 连接到子节点左边缘
            else: # 子节点在左侧
                end_pt = (x1 + NODE_W, cy1) # 连接到子节点右边缘
                
            # 绘制连线：实线底色（确保结构清晰）+ 动态流光（视觉效果）
            dwg.add(dwg.line(start=start_pt, end=end_pt, 
                             stroke=EDGE_COLOR, stroke_width=4, opacity=0.6,
                             marker_end="url(#arrowHead)"))
            
            dwg.add(dwg.line(start=start_pt, end=end_pt, 
                             stroke="#ffffff", stroke_width=2, opacity=0.8,
                             class_="flow-line"))

        elif is_vertical_aligned:
            # 转角情况：使用贝塞尔曲线连接外侧
            if cx2 > CENTER_X_THRESHOLD: # 右侧转弯
                start_pt = (x2 + NODE_W, cy2)
                end_pt = (x1 + NODE_W, cy1)
                cp1 = (x2 + NODE_W + CURVE_MARGIN, cy2)
                cp2 = (x1 + NODE_W + CURVE_MARGIN, cy1)
            else: # 左侧转弯
                start_pt = (x2, cy2)
                end_pt = (x1, cy1)
                cp1 = (x2 - CURVE_MARGIN, cy2)
                cp2 = (x1 - CURVE_MARGIN, cy1)
                
            path_d = f"M{start_pt[0]},{start_pt[1]} C{cp1[0]},{cp1[1]} {cp2[0]},{cp2[1]} {end_pt[0]},{end_pt[1]}"
            
            dwg.add(dwg.path(d=path_d, fill="none", stroke=EDGE_COLOR, stroke_width=4, opacity=0.6, marker_end="url(#arrowHead)"))
            dwg.add(dwg.path(d=path_d, fill="none", stroke="#ffffff", stroke_width=2, opacity=0.8, class_="flow-line"))

        else:
            # 其他情况（如跨行跳转）：中心 -> 边缘（使用 get_intersect 计算子节点交点）
            start_pt = (cx2, cy2)
            ex, ey = get_intersect(cx1, cy1, cx2, cy2, NODE_W, NODE_H)
            end_pt = (ex, ey)
            
            dwg.add(dwg.line(start=start_pt, end=end_pt, stroke=EDGE_COLOR, stroke_width=4, opacity=0.6, marker_end="url(#arrowHead)"))
            dwg.add(dwg.line(start=start_pt, end=end_pt, stroke="#ffffff", stroke_width=2, opacity=0.8, class_="flow-line"))

# 2. 绘制节点背景（矩形）
print("[5/6] 正在绘制节点与文本...")
for index, c in enumerate(commits):
    if (index + 1) % log_step == 0 or (index + 1) == total_commits:
        print(f"    - 节点绘制进度: {index + 1}/{total_commits}")
    sha = c.hexsha
    insert_x, insert_y = positions[sha]
    branch_name = branch_map.get(sha)
    
    # 节点颜色逻辑
    n_in = len(c.parents)          # 入度：父节点数量（指向此节点的线）
    n_out = len(parent_map[sha])   # 出度：子节点数量（从此节点指出的线）

    if n_in >= 5:
        fill_color = "#000000"     # >=5条线：黑色
    elif n_in == 4:
        fill_color = "#8B0000"     # 4条线：血红色
    elif n_in == 3:
        fill_color = "#FF7F50"     # 3条线：浅橘红色
    elif n_in == 2:
        fill_color = "#006400"     # 2条线：深绿色
    elif n_out == 0:
        fill_color = "#9370DB"     # 无向外箭头（无子节点）：淡紫色
    else:
        # 默认逻辑：区分主分支与其他分支
        fill_color = NODE_COLOR_MAIN if branch_name == MAIN_BRANCH else NODE_COLOR_BRANCH
    
    dwg.add(
        dwg.rect(
            insert=(insert_x, insert_y),
            size=(NODE_W, NODE_H),
            rx=12, ry=12,
            fill=fill_color,
            opacity=0.8,
            stroke="white",
            stroke_width=2
        )
    )

# 3. 绘制节点文字
for c in commits:
    sha = c.hexsha
    msg = shorten(c.message.strip().replace("\n", " "), 40)
    author = c.author.name
    date = datetime.datetime.fromtimestamp(c.committed_date).strftime("%Y-%m-%d %H:%M")
    stats = c.stats.total

    insert_x, insert_y = positions[sha]

    # Commit summary text
    dwg.add(dwg.text(
        msg,
        insert=(insert_x + 10, insert_y + 25),
        fill="white",
        font_size="16px",
        font_family="Consolas, Microsoft YaHei, SimHei"
    ))

    dwg.add(dwg.text(
        f"作者：{author} | 日期：{date}",
        insert=(insert_x + 10, insert_y + 45),
        fill="white",
        font_size="12px",
        font_family="Consolas, Microsoft YaHei, SimHei"
    ))

    # 代码变更统计（插入为绿色，删除为红色）
    stats_text = dwg.text(
        "",
        insert=(insert_x + 10, insert_y + 65),
        font_size="12px",
        font_family="Consolas, Microsoft YaHei, SimHei"
    )
    stats_text.add(dwg.tspan("代码变更：", fill="white"))
    stats_text.add(dwg.tspan(f"+{stats['insertions']} / ", fill="#00FFAA"))
    stats_text.add(dwg.tspan(f"-{stats['deletions']}", fill="#FF5555"))
    dwg.add(stats_text)


# ===========================================================
# 保存 SVG 文件
# ===========================================================

print("[6/6] 正在保存 SVG 文件...")
dwg.save()
print("SVG 已保存为 git_history.svg")
