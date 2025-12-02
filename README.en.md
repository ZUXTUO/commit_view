# Git Commit History Visualization (git_history)

A lightweight tool that renders Git commit history as a diagram. It generates `git_history.svg`, color-codes the main branch and other branches, uses arrows to show parent-child relationships, and displays commit message, author, date, and code change stats inside each node.

![git_history](./git_history.svg)

## Quick Start
- Install dependencies: `pip install svgwrite gitpython`
- Run at repository root: `python git_viz.py`
- Output file: `git_history.svg`

## Usage
- The generated SVG is placed at the repository root, suitable for viewing in a browser or embedding into documents.
- Run the script in the Git repository root; it will automatically traverse all branches and commits.

— Read this in Chinese: [中文 README](./README.md)

