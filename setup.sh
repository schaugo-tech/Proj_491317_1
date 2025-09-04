#!/bin/bash

# 安装系统依赖
apt-get update
apt-get install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxrender1 libxext6

# 创建streamlit配置目录
mkdir -p ~/.streamlit/

# 写入配置
echo "\
[server]\n\
headless = true\n\
port = \$PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
