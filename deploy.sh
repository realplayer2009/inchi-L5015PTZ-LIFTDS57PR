#!/bin/bash
# deploy.sh - 部署脚本，将服务部署到目标服务器 192.168.25.88

set -e

TARGET_HOST="192.168.25.88"
TARGET_USER="root"
PACKAGE_NAME="inchiptz_1.0.1_all.deb"

echo "======================================"
echo "InchiPTZ 服务部署脚本"
echo "目标服务器: ${TARGET_USER}@${TARGET_HOST}"
echo "======================================"

# 检查deb包是否存在
if [ ! -f "$PACKAGE_NAME" ]; then
    echo "错误: 找不到 $PACKAGE_NAME"
    echo "请先运行 ./build_deb.sh 构建安装包"
    exit 1
fi

echo ""
echo "步骤 1: 上传安装包到目标服务器..."
scp "$PACKAGE_NAME" "${TARGET_USER}@${TARGET_HOST}:/tmp/"

echo ""
echo "步骤 2: 在目标服务器上安装..."
ssh "${TARGET_USER}@${TARGET_HOST}" << 'ENDSSH'
    echo "正在安装 InchiPTZ 服务..."
    
    # 停止旧服务（如果存在）
    if systemctl is-active --quiet inchiptz; then
        echo "停止旧服务..."
        systemctl stop inchiptz
    fi
    
    # 卸载旧版本（如果存在）
    if dpkg -l | grep -q inchiptz; then
        echo "卸载旧版本..."
        dpkg -r inchiptz || true
    fi
    
    # 安装新版本
    echo "安装新版本..."
    dpkg -i /tmp/inchiptz_1.0.1_all.deb
    
    # 修复依赖
    echo "修复依赖..."
    apt-get update
    apt-get install -f -y
    
    # 确保 pip 已安装
    if ! command -v pip3 &> /dev/null; then
        echo "安装 pip3..."
        apt-get install -y python3-pip
    fi
    
    # 安装 Python 依赖
    echo "安装 Python 依赖..."
    pip3 install --upgrade pip setuptools wheel 2>/dev/null || true
    pip3 install pymodbus pyserial flask 2>/dev/null || \
    pip3 install pymodbus pyserial flask --break-system-packages 2>/dev/null || \
    python3 -m pip install pymodbus pyserial flask
    
    # 启动服务
    echo "启动服务..."
    systemctl start inchiptz
    
    # 等待服务启动
    sleep 2
    
    # 显示服务状态
    echo ""
    echo "======================================"
    echo "服务状态:"
    systemctl status inchiptz --no-pager
    
    echo ""
    echo "======================================"
    echo "部署完成！"
    echo "======================================"
    echo ""
    echo "API 地址: http://192.168.25.88:50278"
    echo ""
    echo "测试命令:"
    echo '  curl http://192.168.25.88:50278/health'
    echo '  curl http://192.168.25.88:50278/get_status'
    echo ""
    echo "查看日志:"
    echo "  sudo journalctl -u inchiptz -f"
    echo "  tail -f /var/log/inchiptz/operation.log"
    echo ""
ENDSSH

echo ""
echo "======================================"
echo "部署完成！"
echo "======================================"
echo ""
echo "可以通过以下方式访问服务:"
echo "  健康检查: curl http://192.168.25.88:50278/health"
echo "  获取状态: curl http://192.168.25.88:50278/get_status"
echo "  设置位置: curl -X POST http://192.168.25.88:50278/set_position -H 'Content-Type: application/json' -d '{\"yaw\":60,\"pitch\":60}'"
echo ""
