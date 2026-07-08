#!/bin/bash

# 1. 移除 git 配置和 apt-get 安装，因为容器内已有环境且无权限修改系统
#

# 2. 清理旧的虚拟环境，确保幂等性，防止权限冲突
rm -rf .tbench-testing

# 3. 使用系统自带 Python 创建 venv，避免对 uv 的依赖
python3 -m venv .tbench-testing

# 4. 激活并安装必要的依赖
source .tbench-testing/bin/activate
pip install --upgrade pip
pip install pytest==8.4.1

# 5. 执行测试，显式检查 TEST_DIR 是否设置，防止路径报错
if [ -z "$TEST_DIR" ]; then
    # 默认回退路径，确保脚本不会因为找不到文件而报错
    TEST_DIR="tests"
fi

# 运行 pytest
python3 -m pytest "$TEST_DIR/test_outputs.py" -rA