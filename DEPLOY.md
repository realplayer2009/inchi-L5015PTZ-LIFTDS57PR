# InchiPTZ 服务部署指南

## 部署目标
- 目标服务器: `192.168.25.88`
- PTZ 设备地址: `192.168.25.78:502` (TCP Modbus)
- API 监听地址: `0.0.0.0:50278`

## 快速部署（自动）

### 1. 在 Windows 上构建包（使用 WSL 或 Git Bash）

```bash
# 进入项目目录
cd /r/githubw/inchiPTZ

# 构建 deb 包
bash build_deb.sh

# 部署到目标服务器
bash deploy.sh
```

## 手动部署步骤

### 1. 构建安装包

```bash
bash build_deb.sh
```

这将生成: `inchiptz_1.0.1_all.deb`

### 2. 上传到目标服务器

```bash
scp inchiptz_1.0.1_all.deb root@192.168.25.88:/tmp/
```

### 3. SSH 登录到目标服务器

```bash
ssh root@192.168.25.88
```

### 4. 在目标服务器上安装

```bash
# 停止旧服务（如果存在）
sudo systemctl stop inchiptz

# 卸载旧版本（如果存在）
sudo dpkg -r inchiptz

# 安装新版本
sudo dpkg -i /tmp/inchiptz_1.0.1_all.deb

# 修复依赖
sudo apt-get update
sudo apt-get install -f -y

# 安装 Python 依赖
sudo pip3 install pymodbus pyserial flask
```

### 5. 配置服务（可选）

编辑服务配置文件（如需修改参数）:
```bash
sudo nano /etc/systemd/system/inchiptz.service
```

默认配置:
- `--port 192.168.25.78:502` - PTZ 设备 TCP 地址
- `--yaw-id 1` - YAW 电机 ID
- `--pitch-id 2` - PITCH 电机 ID
- `--host 0.0.0.0` - API 监听所有网络接口
- `--port-num 50278` - API 端口

修改后重新加载:
```bash
sudo systemctl daemon-reload
```

### 6. 启动服务

```bash
# 启动服务
sudo systemctl start inchiptz

# 查看状态
sudo systemctl status inchiptz

# 设置开机自启动
sudo systemctl enable inchiptz
```

## 测试服务

### 从目标服务器本地测试

```bash
# 健康检查
curl http://localhost:50278/health

# 获取当前状态
curl http://localhost:50278/get_status

# 设置位置
curl -X POST http://localhost:50278/set_position \
  -H 'Content-Type: application/json' \
  -d '{"yaw": 60.0, "pitch": 60.0}'
```

### 从其他机器测试

```bash
# 健康检查
curl http://192.168.25.88:50278/health

# 获取状态
curl http://192.168.25.88:50278/get_status

# 设置位置
curl -X POST http://192.168.25.88:50278/set_position \
  -H 'Content-Type: application/json' \
  -d '{"yaw": 30.0, "pitch": 45.0}'
```

### 从 Windows PowerShell 测试

```powershell
# 健康检查
Invoke-RestMethod -Uri "http://192.168.25.88:50278/health" -Method Get

# 获取状态
Invoke-RestMethod -Uri "http://192.168.25.88:50278/get_status" -Method Get

# 设置位置
$body = @{yaw=60.0; pitch=60.0} | ConvertTo-Json
Invoke-RestMethod -Uri "http://192.168.25.88:50278/set_position" -Method Post -Body $body -ContentType "application/json"
```

## 日志查看

```bash
# 实时查看 systemd 日志
sudo journalctl -u inchiptz -f

# 查看操作日志
tail -f /var/log/inchiptz/operation.log

# 查看错误日志
tail -f /var/log/inchiptz/error.log
```

## 服务管理

```bash
# 启动服务
sudo systemctl start inchiptz

# 停止服务
sudo systemctl stop inchiptz

# 重启服务
sudo systemctl restart inchiptz

# 查看状态
sudo systemctl status inchiptz

# 启用开机自启动
sudo systemctl enable inchiptz

# 禁用开机自启动
sudo systemctl disable inchiptz
```

## 卸载

```bash
# 停止服务
sudo systemctl stop inchiptz

# 禁用服务
sudo systemctl disable inchiptz

# 卸载包
sudo dpkg -r inchiptz

# 清理日志（可选）
sudo rm -rf /var/log/inchiptz
```

## 故障排查

### 服务无法启动

1. 检查日志:
```bash
sudo journalctl -u inchiptz -n 50
```

2. 检查 TCP 连接:
```bash
telnet 192.168.25.78 502
```

3. 检查网络:
```bash
ping 192.168.25.78
```

### API 无响应

1. 检查服务状态:
```bash
sudo systemctl status inchiptz
```

2. 检查端口监听:
```bash
sudo netstat -tunlp | grep 50278
```

3. 检查防火墙:
```bash
sudo ufw status
sudo ufw allow 50278/tcp
```

### 无法连接 PTZ 设备

1. 测试网络连通性:
```bash
ping 192.168.25.78
```

2. 测试端口连接:
```bash
telnet 192.168.25.78 502
```

3. 查看详细日志:
```bash
tail -f /var/log/inchiptz/error.log
```

## API 文档

### POST /set_position
设置 PTZ 位置

**请求:**
```json
{
  "yaw": 60.0,
  "pitch": 45.0
}
```

**响应:**
```json
{
  "success": true
}
```

**错误响应:**
```json
{
  "success": false,
  "error": "错误信息",
  "code": 400
}
```

**角度限制:**
- YAW: -85° ~ +85°
- PITCH: -10° ~ +85°

### GET /get_status
获取 PTZ 当前状态

**响应:**
```json
{
  "success": true,
  "yaw_angle": 59.99,
  "pitch_angle": 60.0,
  "yaw_temperature": 28,
  "pitch_temperature": 30
}
```

### GET /health
健康检查

**响应:**
```json
{
  "healthy": true,
  "serial_connected": true
}
```

## 系统要求

- Ubuntu/Debian Linux
- Python 3.6+
- 网络连接到 PTZ 设备 (192.168.25.78:502)
- 端口 50278 未被占用

## 依赖包

- python3
- python3-pip
- python3-serial
- python3-flask
- pymodbus

## 支持

如有问题，请查看日志或联系技术支持。
