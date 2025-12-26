#!/bin/bash
# quick_deploy.sh - 一键部署到 192.168.25.88

set -e

TARGET_HOST="192.168.25.88"
TARGET_USER="root"

echo "======================================"
echo "InchiPTZ 快速部署脚本"
echo "======================================"
echo ""

# 检查是否在 Git Bash/WSL/Linux 环境
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "检测到 Windows 环境（Git Bash）"
elif [[ -f "/proc/version" ]] && grep -qi microsoft /proc/version; then
    echo "检测到 WSL 环境"
else
    echo "检测到 Linux 环境"
fi

echo ""
echo "目标服务器: ${TARGET_USER}@${TARGET_HOST}"
echo ""

# 步骤 1: 测试 SSH 连接
echo "步骤 1/5: 测试 SSH 连接..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes ${TARGET_USER}@${TARGET_HOST} exit 2>/dev/null; then
    echo "警告: 无法使用密钥认证，请确保已配置 SSH 密钥或准备输入密码"
    echo ""
fi

# 步骤 2: 构建 deb 包
echo "步骤 2/5: 构建 deb 包..."
if [ -f "build_deb.sh" ]; then
    bash build_deb.sh
else
    echo "错误: 找不到 build_deb.sh"
    exit 1
fi

if [ ! -f "inchiptz_1.0.1_all.deb" ]; then
    echo "错误: deb 包构建失败"
    exit 1
fi

echo "✓ deb 包构建成功"
echo ""

# 步骤 3: 上传安装包
echo "步骤 3/5: 上传安装包..."
scp inchiptz_1.0.1_all.deb ${TARGET_USER}@${TARGET_HOST}:/tmp/
echo "✓ 上传完成"
echo ""

# 步骤 4: 远程安装
echo "步骤 4/5: 远程安装..."
ssh ${TARGET_USER}@${TARGET_HOST} bash << 'ENDSSH'
    set -e
    
    echo "正在目标服务器上安装..."
    
    # 停止旧服务
    if systemctl is-active --quiet inchiptz 2>/dev/null; then
        echo "  停止旧服务..."
        systemctl stop inchiptz
    fi
    
    # 卸载旧版本
    if dpkg -l | grep -q "^ii.*inchiptz" 2>/dev/null; then
        echo "  卸载旧版本..."
        dpkg -r inchiptz 2>/dev/null || true
    fi
    
    # 安装新版本
    echo "  安装新版本..."
    dpkg -i /tmp/inchiptz_1.0.1_all.deb 2>&1 | grep -v "warning" || true
    
    # 修复依赖
    echo "  修复依赖..."
    apt-get update >/dev/null 2>&1
    apt-get install -f -y >/dev/null 2>&1
    
    # 安装 pip3（如果不存在）
    if ! command -v pip3 &> /dev/null; then
        echo "  安装 pip3..."
        apt-get install -y python3-pip >/dev/null 2>&1
    fi
    
    # 安装 Python 依赖
    echo "  安装 Python 依赖..."
    pip3 install --upgrade pip >/dev/null 2>&1 || true
    if ! pip3 install pymodbus pyserial flask >/dev/null 2>&1; then
        pip3 install pymodbus pyserial flask --break-system-packages >/dev/null 2>&1 || true
    fi
    
    # 验证依赖
    if python3 -c "import flask, serial" 2>/dev/null; then
        echo "  ✓ Python 依赖安装成功"
    else
        echo "  ⚠ Python 依赖可能未完全安装"
    fi
    
    echo "✓ 安装完成"
ENDSSH

echo ""

# 步骤 5: 启动服务并测试
echo "步骤 5/5: 启动服务并测试..."
ssh ${TARGET_USER}@${TARGET_HOST} bash << 'ENDSSH'
    set -e
    
    # 启动服务
    echo "  启动服务..."
    systemctl start inchiptz
    
    # 等待服务启动
    sleep 2
    
    # 检查服务状态
    if systemctl is-active --quiet inchiptz; then
        echo "  ✓ 服务启动成功"
    else
        echo "  ✗ 服务启动失败"
        systemctl status inchiptz --no-pager -l
        exit 1
    fi
    
    # 测试 API
    echo "  测试 API..."
    if curl -s http://localhost:50278/health | grep -q "healthy"; then
        echo "  ✓ API 响应正常"
    else
        echo "  ⚠ API 可能未就绪"
    fi
ENDSSH

echo ""
echo "======================================"
echo "部署成功！"
echo "======================================"
echo ""
echo "服务信息:"
echo "  API 地址: http://192.168.25.88:50278"
echo "  PTZ 设备: 192.168.25.78:502"
echo ""
echo "测试命令:"
echo "  curl http://192.168.25.88:50278/health"
echo "  curl http://192.168.25.88:50278/get_status"
echo ""
echo "管理命令:"
echo "  ssh ${TARGET_USER}@${TARGET_HOST} 'systemctl status inchiptz'"
echo "  ssh ${TARGET_USER}@${TARGET_HOST} 'journalctl -u inchiptz -f'"
echo ""
echo "详细文档: DEPLOY_DEBIAN.md"
echo "======================================"
