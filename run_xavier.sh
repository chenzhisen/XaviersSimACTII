#!/bin/bash

# 设置 Python 路径
export PYTHONPATH=$(pwd)

# 创建必要的目录
mkdir -p logs/dev/tech
mkdir -p logs/dev/tweets
mkdir -p data/dev
mkdir -p data/prod

# 设置文件权限
chmod 755 logs -R
chmod 755 data -R

# 运行程序
python3 src/main.py --provider xai