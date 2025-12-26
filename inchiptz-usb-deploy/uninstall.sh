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
