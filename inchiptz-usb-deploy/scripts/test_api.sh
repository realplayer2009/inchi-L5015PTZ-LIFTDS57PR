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
