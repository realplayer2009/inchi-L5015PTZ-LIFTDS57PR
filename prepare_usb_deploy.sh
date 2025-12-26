#!/bin/bash
# prepare_usb_deploy.sh - 准备 U 盘部署包

set -e

DEPLOY_DIR="inchiptz-usb-deploy"
VERSION="1.0.1"

echo "======================================"
echo "准备 InchiPTZ U 盘部署包"
echo "版本: ${VERSION}"
echo "======================================"
echo ""

# 清理旧部署目录
if [ -d "$DEPLOY_DIR" ]; then
    echo "清理旧部署目录..."
    rm -rf "$DEPLOY_DIR"
fi

# 创建部署目录结构
echo "创建部署目录..."
mkdir -p "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR/app"
mkdir -p "$DEPLOY_DIR/config"
mkdir -p "$DEPLOY_DIR/scripts"
mkdir -p "$DEPLOY_DIR/docs"

# 复制应用程序文件
echo "复制应用程序文件..."
cp api_server.py "$DEPLOY_DIR/app/"
cp ptz_controller.py "$DEPLOY_DIR/app/"
cp rs485_comm.py "$DEPLOY_DIR/app/"
cp lift_motor.py "$DEPLOY_DIR/app/"
cp proto_v43.py "$DEPLOY_DIR/app/"

# 复制配置文件
echo "复制配置文件..."
cp debian/inchiptz.service "$DEPLOY_DIR/config/"

# 复制文档
echo "复制文档..."
cp DEPLOY_DEBIAN.md "$DEPLOY_DIR/docs/" 2>/dev/null || true
cp PACKAGE_DEPLOY.md "$DEPLOY_DIR/docs/" 2>/dev/null || true
cp 部署总结.md "$DEPLOY_DIR/docs/" 2>/dev/null || true
cp README.md "$DEPLOY_DIR/docs/" 2>/dev/null || true

# 创建 requirements.txt
echo "创建依赖列表..."
cat > "$DEPLOY_DIR/requirements.txt" << 'EOF'
flask>=2.0.0
pyserial>=3.5
pymodbus>=3.0.0
EOF

# 创建安装脚本
echo "创建安装脚本..."
cat > "$DEPLOY_DIR/install.sh" << 'EOFINSTALL'
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
EOFINSTALL

chmod +x "$DEPLOY_DIR/install.sh"

# 创建卸载脚本
echo "创建卸载脚本..."
cat > "$DEPLOY_DIR/uninstall.sh" << 'EOFUNINSTALL'
#!/bin/bash
# uninstall.sh - 卸载脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "======================================"
echo "InchiPTZ 服务卸载程序"
echo "======================================"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

echo -e "${YELLOW}警告: 这将卸载 InchiPTZ 服务并删除所有相关文件${NC}"
echo "是否继续? [y/N]"
read -r response
if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    echo "取消卸载"
    exit 0
fi

echo ""
echo "步骤 1/4: 停止服务..."
if systemctl is-active --quiet inchiptz 2>/dev/null; then
    systemctl stop inchiptz
    echo -e "${GREEN}✓${NC} 服务已停止"
fi

echo ""
echo "步骤 2/4: 禁用服务..."
if systemctl is-enabled --quiet inchiptz 2>/dev/null; then
    systemctl disable inchiptz
    echo -e "${GREEN}✓${NC} 服务已禁用"
fi

echo ""
echo "步骤 3/4: 删除文件..."
rm -f /etc/systemd/system/inchiptz.service
rm -rf /usr/share/inchiptz
systemctl daemon-reload
echo -e "${GREEN}✓${NC} 文件已删除"

echo ""
echo "步骤 4/4: 清理日志..."
echo "是否删除日志文件? [y/N]"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
    rm -rf /var/log/inchiptz
    echo -e "${GREEN}✓${NC} 日志已删除"
else
    echo "保留日志: /var/log/inchiptz"
fi

echo ""
echo "======================================"
echo -e "${GREEN}卸载完成！${NC}"
echo "======================================"
EOFUNINSTALL

chmod +x "$DEPLOY_DIR/uninstall.sh"

# 创建 README
echo "创建 README..."
cat > "$DEPLOY_DIR/README.txt" << 'EOFREADME'
================================================================================
InchiPTZ 云台控制服务 - U 盘部署包
版本: 1.0.1
================================================================================

目录结构:
  app/              - 应用程序文件
  config/           - 配置文件
  scripts/          - 辅助脚本
  docs/             - 文档
  install.sh        - 安装脚本
  uninstall.sh      - 卸载脚本
  requirements.txt  - Python 依赖列表
  README.txt        - 本文件

================================================================================
快速安装（推荐）
================================================================================

1. 将整个文件夹复制到目标服务器（192.168.25.88）
   例如: /tmp/inchiptz-usb-deploy/

2. 进入目录:
   cd /tmp/inchiptz-usb-deploy/

3. 运行安装脚本:
   sudo ./install.sh

4. 测试服务:
   curl http://localhost:50278/health

================================================================================
手动安装
================================================================================

如果自动安装失败，可以手动执行以下步骤:

1. 创建目录:
   sudo mkdir -p /usr/share/inchiptz
   sudo mkdir -p /var/log/inchiptz

2. 复制文件:
   sudo cp app/*.py /usr/share/inchiptz/
   sudo chmod 755 /usr/share/inchiptz/api_server.py

3. 安装 Python 依赖:
   sudo pip3 install flask pyserial pymodbus

4. 安装服务:
   sudo cp config/inchiptz.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable inchiptz
   sudo systemctl start inchiptz

5. 检查状态:
   sudo systemctl status inchiptz

================================================================================
服务配置
================================================================================

通信地址: 192.168.25.78:502 (TCP Modbus)
API 监听: 0.0.0.0:50278
YAW 电机: ID 1
PITCH 电机: ID 2

如需修改配置，编辑:
  /etc/systemd/system/inchiptz.service

修改后重新加载:
  sudo systemctl daemon-reload
  sudo systemctl restart inchiptz

================================================================================
管理命令
================================================================================

启动服务:  sudo systemctl start inchiptz
停止服务:  sudo systemctl stop inchiptz
重启服务:  sudo systemctl restart inchiptz
查看状态:  sudo systemctl status inchiptz
查看日志:  sudo journalctl -u inchiptz -f

================================================================================
API 测试
================================================================================

健康检查:
  curl http://localhost:50278/health

获取状态:
  curl http://localhost:50278/get_status

设置位置:
  curl -X POST http://localhost:50278/set_position \
    -H 'Content-Type: application/json' \
    -d '{"yaw": 60.0, "pitch": 60.0}'

================================================================================
系统要求
================================================================================

- Debian 9+ / Ubuntu 18.04+
- Python 3.6+
- 网络访问: 192.168.25.78:502

================================================================================
卸载
================================================================================

运行卸载脚本:
  sudo ./uninstall.sh

或手动卸载:
  sudo systemctl stop inchiptz
  sudo systemctl disable inchiptz
  sudo rm -f /etc/systemd/system/inchiptz.service
  sudo rm -rf /usr/share/inchiptz
  sudo rm -rf /var/log/inchiptz  # 可选

================================================================================
故障排查
================================================================================

问题 1: 服务无法启动
解决: 查看日志
  sudo journalctl -u inchiptz -n 50

问题 2: Python 依赖缺失
解决: 手动安装
  sudo pip3 install flask pyserial pymodbus

问题 3: 无法连接 PTZ 设备
解决: 测试网络
  ping 192.168.25.78
  telnet 192.168.25.78 502

问题 4: API 无响应
解决: 检查端口
  sudo netstat -tunlp | grep 50278

更多帮助请查看 docs/ 目录中的详细文档。

================================================================================
EOFREADME

# 创建测试脚本
cat > "$DEPLOY_DIR/scripts/test_api.sh" << 'EOFTEST'
#!/bin/bash
# test_api.sh - API 测试脚本

echo "======================================"
echo "InchiPTZ API 测试"
echo "======================================"
echo ""

HOST="localhost:50278"

echo "测试 1: 健康检查"
echo "URL: http://$HOST/health"
curl -s "http://$HOST/health" | python3 -m json.tool 2>/dev/null || curl -s "http://$HOST/health"
echo ""
echo ""

echo "测试 2: 获取状态"
echo "URL: http://$HOST/get_status"
curl -s "http://$HOST/get_status" | python3 -m json.tool 2>/dev/null || curl -s "http://$HOST/get_status"
echo ""
echo ""

echo "测试 3: 设置位置 (yaw=30°, pitch=45°)"
echo "URL: http://$HOST/set_position"
curl -s -X POST "http://$HOST/set_position" \
  -H 'Content-Type: application/json' \
  -d '{"yaw": 30.0, "pitch": 45.0}' | python3 -m json.tool 2>/dev/null || \
curl -s -X POST "http://$HOST/set_position" \
  -H 'Content-Type: application/json' \
  -d '{"yaw": 30.0, "pitch": 45.0}'
echo ""
echo ""

echo "等待 2 秒..."
sleep 2

echo "测试 4: 再次获取状态"
curl -s "http://$HOST/get_status" | python3 -m json.tool 2>/dev/null || curl -s "http://$HOST/get_status"
echo ""
echo ""

echo "======================================"
echo "测试完成"
echo "======================================"
EOFTEST

chmod +x "$DEPLOY_DIR/scripts/test_api.sh"

# 创建快速检查脚本
cat > "$DEPLOY_DIR/scripts/check_service.sh" << 'EOFCHECK'
#!/bin/bash
# check_service.sh - 服务检查脚本

echo "======================================"
echo "InchiPTZ 服务状态检查"
echo "======================================"
echo ""

echo "1. 服务状态:"
systemctl is-active inchiptz && echo "  ✓ 运行中" || echo "  ✗ 未运行"
echo ""

echo "2. 服务详情:"
systemctl status inchiptz --no-pager -l
echo ""

echo "3. 最近日志 (最后 10 条):"
journalctl -u inchiptz -n 10 --no-pager
echo ""

echo "4. 端口监听:"
netstat -tunlp 2>/dev/null | grep 50278 || ss -tunlp 2>/dev/null | grep 50278 || echo "  未找到监听端口"
echo ""

echo "5. Python 依赖:"
python3 -c "import flask; print('  ✓ flask')" 2>/dev/null || echo "  ✗ flask"
python3 -c "import serial; print('  ✓ pyserial')" 2>/dev/null || echo "  ✗ pyserial"
python3 -c "import pymodbus; print('  ✓ pymodbus')" 2>/dev/null || echo "  ✗ pymodbus"
echo ""

echo "======================================"
EOFCHECK

chmod +x "$DEPLOY_DIR/scripts/check_service.sh"

# 打包
echo ""
echo "创建压缩包..."
tar -czf "${DEPLOY_DIR}.tar.gz" "$DEPLOY_DIR"

# 创建 zip（Windows 兼容）
if command -v zip &> /dev/null; then
    zip -r -q "${DEPLOY_DIR}.zip" "$DEPLOY_DIR"
    echo "✓ 创建 ${DEPLOY_DIR}.zip"
fi

echo "✓ 创建 ${DEPLOY_DIR}.tar.gz"

# 显示信息
echo ""
echo "======================================"
echo "部署包准备完成！"
echo "======================================"
echo ""
echo "生成的文件:"
echo "  目录: $DEPLOY_DIR/"
echo "  压缩包: ${DEPLOY_DIR}.tar.gz"
if [ -f "${DEPLOY_DIR}.zip" ]; then
    echo "  压缩包: ${DEPLOY_DIR}.zip"
fi
echo ""
echo "U 盘部署步骤:"
echo "  1. 复制 $DEPLOY_DIR/ 或 ${DEPLOY_DIR}.tar.gz 到 U 盘"
echo "  2. 在目标服务器解压: tar -xzf ${DEPLOY_DIR}.tar.gz"
echo "  3. 进入目录: cd $DEPLOY_DIR"
echo "  4. 运行安装: sudo ./install.sh"
echo ""
echo "目录内容:"
ls -lh "$DEPLOY_DIR/"
echo ""
