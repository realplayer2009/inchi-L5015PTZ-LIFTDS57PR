# InchiPTZ 服务打包和部署说明

## 概述

将 PTZ 云台控制服务打包为 Debian/Ubuntu deb 包，并部署到目标服务器 192.168.25.88。

## 部署架构

```
┌─────────────┐      HTTP API       ┌──────────────────┐      TCP       ┌─────────────┐
│   客户端    │ ───────────────────> │  192.168.25.88   │ ──────────────> │ PTZ 设备    │
│  (任意机器) │   Port: 50278        │  (API 服务器)    │  Port: 502     │ 192.168.25  │
└─────────────┘                      └──────────────────┘                 │    .78      │
                                                                          └─────────────┘
```

## 快速开始

### 方法 1: 一键部署（推荐）

```bash
# 在 Git Bash/WSL/Linux 环境下运行
cd /r/githubw/inchiPTZ  # Windows
# 或
cd ~/inchiPTZ          # Linux

# 给脚本添加执行权限
chmod +x quick_deploy.sh

# 一键部署
./quick_deploy.sh
```

### 方法 2: 分步部署

```bash
# 1. 构建 deb 包
bash build_deb.sh

# 2. 部署到服务器
bash deploy.sh
```

## 手动部署

详见 [DEPLOY_DEBIAN.md](DEPLOY_DEBIAN.md)

## 生成的文件

- `inchiptz_1.0.1_all.deb` - Debian/Ubuntu 安装包

## 安装包内容

```
/usr/share/inchiptz/          # 应用程序目录
├── api_server.py             # Flask API 服务器
├── ptz_controller.py         # PTZ 控制器
├── rs485_comm.py             # 通信层（TCP/串口）
├── lift_motor.py             # 电机控制
└── proto_v43.py              # 协议定义

/etc/systemd/system/          # systemd 服务
└── inchiptz.service          # 服务配置文件

/var/log/inchiptz/            # 日志目录
├── operation.log             # 操作日志
└── error.log                 # 错误日志
```

## 服务配置

### 默认配置

- **PTZ 设备地址**: 192.168.25.78:502 (TCP)
- **API 监听地址**: 0.0.0.0:50278 (所有接口)
- **YAW 电机 ID**: 1
- **PITCH 电机 ID**: 2
- **轮询间隔**: 500ms

### 修改配置

编辑服务文件：
```bash
ssh root@192.168.25.88
sudo nano /etc/systemd/system/inchiptz.service
```

修改参数后重新加载：
```bash
sudo systemctl daemon-reload
sudo systemctl restart inchiptz
```

## API 接口

### 1. 健康检查
```bash
GET http://192.168.25.88:50278/health

响应:
{
  "healthy": true,
  "serial_connected": true
}
```

### 2. 获取状态
```bash
GET http://192.168.25.88:50278/get_status

响应:
{
  "success": true,
  "yaw_angle": 60.0,
  "pitch_angle": 45.0,
  "yaw_temperature": 28,
  "pitch_temperature": 30
}
```

### 3. 设置位置
```bash
POST http://192.168.25.88:50278/set_position
Content-Type: application/json

{
  "yaw": 60.0,
  "pitch": 45.0
}

响应:
{
  "success": true
}
```

## 测试命令

### Linux/Mac
```bash
# 健康检查
curl http://192.168.25.88:50278/health

# 获取状态
curl http://192.168.25.88:50278/get_status

# 设置位置
curl -X POST http://192.168.25.88:50278/set_position \
  -H 'Content-Type: application/json' \
  -d '{"yaw": 60.0, "pitch": 60.0}'
```

### Windows PowerShell
```powershell
# 健康检查
Invoke-RestMethod -Uri "http://192.168.25.88:50278/health"

# 获取状态
Invoke-RestMethod -Uri "http://192.168.25.88:50278/get_status"

# 设置位置
$body = @{yaw=60.0; pitch=60.0} | ConvertTo-Json
Invoke-RestMethod -Uri "http://192.168.25.88:50278/set_position" `
  -Method Post -Body $body -ContentType "application/json"
```

## 服务管理

```bash
# SSH 登录到目标服务器
ssh root@192.168.25.88

# 查看服务状态
sudo systemctl status inchiptz

# 启动服务
sudo systemctl start inchiptz

# 停止服务
sudo systemctl stop inchiptz

# 重启服务
sudo systemctl restart inchiptz

# 查看日志
sudo journalctl -u inchiptz -f

# 查看操作日志
tail -f /var/log/inchiptz/operation.log

# 查看错误日志
tail -f /var/log/inchiptz/error.log
```

## 故障排查

### 服务无法启动

```bash
# 查看详细日志
ssh root@192.168.25.88 'journalctl -u inchiptz -n 50 --no-pager'

# 手动运行查看错误
ssh root@192.168.25.88
cd /usr/share/inchiptz
sudo python3 api_server.py --port 192.168.25.78:502
```

### API 无响应

```bash
# 检查端口监听
ssh root@192.168.25.88 'netstat -tunlp | grep 50278'

# 检查防火墙
ssh root@192.168.25.88 'ufw status'
```

### 无法连接 PTZ 设备

```bash
# 测试网络连通性
ssh root@192.168.25.88 'ping -c 2 192.168.25.78'

# 测试端口连接
ssh root@192.168.25.88 'telnet 192.168.25.78 502'
```

## 系统要求

- **目标系统**: Debian 9+ / Ubuntu 18.04+
- **Python**: 3.6+
- **依赖包**: python3-pip, python3-serial, python3-flask, pymodbus

## 文件清单

- `build_deb.sh` - 构建脚本
- `deploy.sh` - 部署脚本
- `quick_deploy.sh` - 一键部署脚本
- `DEPLOY_DEBIAN.md` - 详细部署文档
- `debian/` - deb 包配置文件
  - `control` - 包信息
  - `inchiptz.service` - systemd 服务
  - `postinst` - 安装后脚本
  - `prerm` - 卸载前脚本

## 更新日志

### v1.0.1 (2025-12-25)
- ✨ 支持 TCP 通信模式（192.168.25.78:502）
- ✨ API 监听所有网络接口（0.0.0.0）
- 🔧 优化 Python 依赖安装流程
- 📝 添加详细的部署文档
- 🚀 添加一键部署脚本

### v1.0.0
- 初始版本
- 串口通信支持
- Flask API 服务

## 许可证

[Your License]

## 技术支持

如有问题，请查看 [DEPLOY_DEBIAN.md](DEPLOY_DEBIAN.md) 中的故障排查部分。
