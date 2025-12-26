#!/bin/bash
# install.sh - U 盘安装脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "InchiPTZ 服务安装程序"
echo "版本: 1.0.1"
echo "======================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    echo "使用方法: sudo ./install.sh"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "步骤 1/7: 检查系统环境..."
# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3${NC}"
    echo "请先安装: sudo apt-get install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python 版本: $PYTHON_VERSION"

echo ""
echo "步骤 2/7: 停止旧服务（如果存在）..."
if systemctl is-active --quiet inchiptz 2>/dev/null; then
    echo "  停止旧服务..."
    systemctl stop inchiptz
    echo -e "${GREEN}✓${NC} 旧服务已停止"
else
    echo "  未发现运行中的服务"
fi

echo ""
echo "步骤 3/7: 创建安装目录..."
mkdir -p /usr/share/inchiptz
mkdir -p /var/log/inchiptz
echo -e "${GREEN}✓${NC} 目录创建完成"

echo ""
echo "步骤 4/7: 复制应用程序文件..."
cp "$SCRIPT_DIR/app/"*.py /usr/share/inchiptz/
chmod 755 /usr/share/inchiptz/api_server.py
chmod 644 /usr/share/inchiptz/*.py
echo -e "${GREEN}✓${NC} 应用程序文件已复制"

echo ""
echo "步骤 5/7: 安装 systemd 服务..."
cp "$SCRIPT_DIR/config/inchiptz.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable inchiptz.service
echo -e "${GREEN}✓${NC} 服务已注册"

echo ""
echo "步骤 6/7: 安装 Python 依赖..."
# 检查 pip
if ! command -v pip3 &> /dev/null; then
    echo "  安装 pip3..."
    apt-get update > /dev/null 2>&1
    apt-get install -y python3-pip > /dev/null 2>&1
fi

# 升级 pip
echo "  升级 pip..."
pip3 install --upgrade pip > /dev/null 2>&1 || true

# 安装依赖
echo "  安装依赖包..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    # 尝试从 requirements.txt 安装
    if pip3 install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 依赖安装成功"
    elif pip3 install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} 依赖安装成功（使用 --break-system-packages）"
    else
        echo -e "${YELLOW}⚠${NC} 尝试逐个安装依赖..."
        pip3 install flask pyserial pymodbus > /dev/null 2>&1 || \
        pip3 install flask pyserial pymodbus --break-system-packages > /dev/null 2>&1 || \
        echo -e "${YELLOW}⚠${NC} 部分依赖可能需要手动安装"
    fi
else
    # 直接安装
    pip3 install flask pyserial pymodbus > /dev/null 2>&1 || \
    pip3 install flask pyserial pymodbus --break-system-packages > /dev/null 2>&1
    echo -e "${GREEN}✓${NC} 依赖安装完成"
fi

# 验证依赖
if python3 -c "import flask, serial" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} 依赖验证通过"
else
    echo -e "${YELLOW}⚠${NC} 警告: 部分依赖未安装，请手动运行:"
    echo "  sudo pip3 install flask pyserial pymodbus"
fi

echo ""
echo "步骤 7/7: 配置日志..."
touch /var/log/inchiptz/operation.log
touch /var/log/inchiptz/error.log
chmod 644 /var/log/inchiptz/*.log
echo -e "${GREEN}✓${NC} 日志配置完成"

echo ""
echo "======================================"
echo -e "${GREEN}安装完成！${NC}"
echo "======================================"
echo ""
echo "服务配置:"
echo "  通信地址: 192.168.25.78:502 (TCP)"
echo "  API 监听: 0.0.0.0:50278"
echo "  应用目录: /usr/share/inchiptz"
echo "  日志目录: /var/log/inchiptz"
echo ""
echo "管理命令:"
echo "  启动服务: sudo systemctl start inchiptz"
echo "  停止服务: sudo systemctl stop inchiptz"
echo "  查看状态: sudo systemctl status inchiptz"
echo "  查看日志: sudo journalctl -u inchiptz -f"
echo ""
echo "测试命令:"
echo "  curl http://localhost:50278/health"
echo ""
echo "是否现在启动服务? [y/N]"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "启动服务..."
    systemctl start inchiptz
    sleep 2
    if systemctl is-active --quiet inchiptz; then
        echo -e "${GREEN}✓${NC} 服务启动成功！"
        echo ""
        echo "测试 API:"
        if command -v curl &> /dev/null; then
            curl -s http://localhost:50278/health || echo "API 未就绪，请稍后测试"
        fi
    else
        echo -e "${RED}✗${NC} 服务启动失败，请查看日志:"
        echo "  sudo journalctl -u inchiptz -n 50"
    fi
else
    echo "稍后手动启动服务: sudo systemctl start inchiptz"
fi

echo ""
echo "安装完成！详细文档请查看 docs/ 目录"
