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
