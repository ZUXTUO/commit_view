# Git 提交历史可视化（git_history）
[English README](./README.en.md)

一个将 Git 提交历史以图形方式展示的轻量工具。运行后生成 `git_history.svg`，用颜色区分主分支与其他分支，箭头连线体现父子提交关系，节点含提交信息、作者、日期与代码变更统计。

![git_history](./git_history.svg)

## 快速开始
- 安装依赖：`pip install svgwrite gitpython`
- 在仓库根目录运行：`python git_viz.py`
- 生成文件：`git_history.svg`

## 使用说明
- 生成的 SVG 位于仓库根目录，适合浏览器或文档内嵌查看。
- 在 Git 仓库根目录执行即可，脚本会自动遍历所有分支与提交。
