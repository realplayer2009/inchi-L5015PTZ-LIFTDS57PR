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
