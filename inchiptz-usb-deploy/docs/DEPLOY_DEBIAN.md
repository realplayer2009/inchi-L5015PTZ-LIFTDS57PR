# InchiPTZ 部署指南 - Debian/Ubuntu 18.04

## 系统要求

- Debian 9/10/11 或 Ubuntu 18.04/20.04/22.04
- Python 3.6+
- 网络连接到目标服务器 192.168.25.88
- 网络连接到 PTZ 设备 192.168.25.78:502

## 部署架构

```
[客户端] -----> [192.168.25.88:50278] -----> [192.168.25.78:502]
                 (API 服务器)                  (PTZ 设备)
```

## 方式一：自动部署（推荐）

### 在 Linux/WSL/Git Bash 环境下

```bash
# 1. 进入项目目录
cd /r/githubw/inchiPTZ  # Windows 路径
# 或
cd ~/inchiPTZ          # Linux 路径

# 2. 构建 deb 包
bash build_deb.sh

# 3. 自动部署
bash deploy.sh
```

## 方式二：手动部署

### 步骤 1: 准备构建环境

在开发机器（Windows/Linux）上：

```bash
# 克隆项目
git clone <repository-url>
cd inchiPTZ

# 确保脚本有执行权限
chmod +x build_deb.sh deploy.sh
```

### 步骤 2: 构建安装包

```bash
bash build_deb.sh
```

输出: `inchiptz_1.0.1_all.deb`

### 步骤 3: 传输到目标服务器

```bash
# 上传 deb 包
scp inchiptz_1.0.1_all.deb root@192.168.25.88:/tmp/

# 或使用密码认证
scp inchiptz_1.0.1_all.deb root@192.168.25.88:/tmp/
```

### 步骤 4: 登录目标服务器

```bash
ssh root@192.168.25.88
```

### 步骤 5: 安装前准备（在目标服务器上）

```bash
# 更新软件源
sudo apt-get update

# 安装基础依赖
sudo apt-get install -y python3 python3-pip

# 检查 Python 版本（需要 3.6+）
python3 --version
```

### 步骤 6: 停止旧服务（如果存在）

```bash
# 检查服务是否存在
systemctl status inchiptz

# 如果存在，停止并卸载
sudo systemctl stop inchiptz
sudo systemctl disable inchiptz
sudo dpkg -r inchiptz
```

### 步骤 7: 安装新版本

```bash
# 安装 deb 包
sudo dpkg -i /tmp/inchiptz_1.0.1_all.deb

# 修复可能的依赖问题
sudo apt-get install -f -y
```

### 步骤 8: 手动安装 Python 依赖（如果自动安装失败）

```bash
# 方法 1: 使用 pip3
sudo pip3 install pymodbus pyserial flask

# 方法 2: 如果方法 1 失败（Python 3.11+）
sudo pip3 install pymodbus pyserial flask --break-system-packages

# 方法 3: 使用 apt（某些包可能版本较旧）
sudo apt-get install -y python3-serial python3-flask

# 验证安装
python3 -c "import flask, serial; print('依赖安装成功')"
```

### 步骤 9: 配置服务（可选）

如需修改配置，编辑服务文件：

```bash
sudo nano /etc/systemd/system/inchiptz.service
```

默认配置项：
```ini
ExecStart=/usr/bin/python3 /usr/share/inchiptz/api_server.py \
    --port 192.168.25.78:502 \    # PTZ 设备 TCP 地址
    --yaw-id 1 \                   # YAW 电机 ID
    --pitch-id 2 \                 # PITCH 电机 ID
    --host 0.0.0.0 \               # API 监听地址（所有接口）
    --port-num 50278               # API 端口
```

修改后重新加载：
```bash
sudo systemctl daemon-reload
```

### 步骤 10: 启动服务

```bash
# 启动服务
sudo systemctl start inchiptz

# 设置开机自启动
sudo systemctl enable inchiptz

# 查看状态
sudo systemctl status inchiptz
```

## 验证安装

### 1. 检查服务状态

```bash
sudo systemctl status inchiptz
```

应该看到 "active (running)" 状态。

### 2. 检查日志

```bash
# 实时查看日志
sudo journalctl -u inchiptz -f

# 查看最近日志
sudo journalctl -u inchiptz -n 50

# 查看应用日志
tail -f /var/log/inchiptz/operation.log
```

### 3. 测试 API（在目标服务器上）

```bash
# 健康检查
curl http://localhost:50278/health

# 预期输出:
# {"healthy":true,"serial_connected":true}

# 获取状态
curl http://localhost:50278/get_status

# 预期输出:
# {"success":true,"yaw_angle":0.0,"pitch_angle":0.0,"yaw_temperature":25,"pitch_temperature":25}

# 设置位置
curl -X POST http://localhost:50278/set_position \
  -H 'Content-Type: application/json' \
  -d '{"yaw": 30.0, "pitch": 45.0}'

# 预期输出:
# {"success":true}
```

### 4. 远程测试（从其他机器）

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

### 5. Windows PowerShell 测试

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

## 故障排查

### 问题 1: 服务无法启动

**检查日志:**
```bash
sudo journalctl -u inchiptz -n 50 --no-pager
```

**常见原因:**
1. Python 依赖未安装
2. TCP 连接失败
3. 端口被占用

**解决方法:**
```bash
# 检查 Python 依赖
python3 -c "import flask, serial, pymodbus"

# 检查端口占用
sudo netstat -tunlp | grep 50278

# 测试 TCP 连接
telnet 192.168.25.78 502
```

### 问题 2: 无法连接 PTZ 设备

**检查网络连通性:**
```bash
ping 192.168.25.78
telnet 192.168.25.78 502
```

**检查服务日志:**
```bash
tail -f /var/log/inchiptz/error.log
```

### 问题 3: 远程无法访问 API

**检查防火墙:**
```bash
# Ubuntu/Debian
sudo ufw status
sudo ufw allow 50278/tcp

# 或使用 iptables
sudo iptables -A INPUT -p tcp --dport 50278 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

**检查服务监听地址:**
```bash
sudo netstat -tunlp | grep 50278
# 应该看到 0.0.0.0:50278 而不是 127.0.0.1:50278
```

### 问题 4: Python 依赖安装失败

**对于 Ubuntu 18.04/Debian 9:**
```bash
# 升级 pip
sudo python3 -m pip install --upgrade pip

# 安装依赖
sudo python3 -m pip install pymodbus pyserial flask
```

**对于 Python 3.11+（Debian 12/Ubuntu 22.04+）:**
```bash
sudo pip3 install pymodbus pyserial flask --break-system-packages
```

**使用虚拟环境（推荐）:**
```bash
sudo apt-get install -y python3-venv
python3 -m venv /opt/inchiptz-venv
source /opt/inchiptz-venv/bin/activate
pip install pymodbus pyserial flask

# 修改 service 文件使用虚拟环境
sudo nano /etc/systemd/system/inchiptz.service
# 修改 ExecStart 为:
# ExecStart=/opt/inchiptz-venv/bin/python3 /usr/share/inchiptz/api_server.py ...
```

### 问题 5: 查看详细错误信息

```bash
# 实时查看所有日志
sudo journalctl -u inchiptz -f

# 查看应用日志
tail -f /var/log/inchiptz/operation.log
tail -f /var/log/inchiptz/error.log

# 手动运行服务查看错误
sudo systemctl stop inchiptz
cd /usr/share/inchiptz
sudo python3 api_server.py --port 192.168.25.78:502
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

# 查看实时日志
sudo journalctl -u inchiptz -f

# 查看最近日志
sudo journalctl -u inchiptz -n 100
```

## 更新服务

```bash
# 1. 停止服务
sudo systemctl stop inchiptz

# 2. 上传新版本 deb 包
scp inchiptz_1.0.1_all.deb root@192.168.25.88:/tmp/

# 3. 安装新版本
sudo dpkg -i /tmp/inchiptz_1.0.1_all.deb

# 4. 启动服务
sudo systemctl start inchiptz

# 5. 查看状态
sudo systemctl status inchiptz
```

## 卸载服务

```bash
# 1. 停止并禁用服务
sudo systemctl stop inchiptz
sudo systemctl disable inchiptz

# 2. 卸载软件包
sudo dpkg -r inchiptz

# 3. 清理日志（可选）
sudo rm -rf /var/log/inchiptz

# 4. 清理应用文件（可选）
sudo rm -rf /usr/share/inchiptz
```

## 配置参数说明

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | `192.168.25.78:502` | PTZ 设备地址（TCP 或串口）|
| `--yaw-id` | `1` | YAW 电机 ID |
| `--pitch-id` | `2` | PITCH 电机 ID |
| `--host` | `0.0.0.0` | API 监听地址 |
| `--port-num` | `50278` | API 监听端口 |

### 角度限制

- **YAW（旋转）**: -85° ~ +85°
- **PITCH（俯仰）**: -10° ~ +85°

## 性能优化

### 调整轮询间隔

编辑 `ptz_controller.py` 中的监控间隔（默认 500ms）：

```python
ptz_controller.start_monitoring(interval_ms=500)
```

### 日志轮转

日志文件已配置自动轮转（1MB，保留 3 个备份）。

## 安全建议

1. **限制 API 访问**：如不需要外部访问，将 `--host` 改为 `127.0.0.1`
2. **配置防火墙**：仅允许可信 IP 访问端口 50278
3. **使用反向代理**：建议通过 Nginx 添加认证
4. **定期更新**：保持系统和 Python 包更新

## 技术支持

如遇问题，请提供：
1. 系统信息：`cat /etc/os-release`
2. Python 版本：`python3 --version`
3. 服务日志：`sudo journalctl -u inchiptz -n 100 --no-pager`
4. 错误日志：`cat /var/log/inchiptz/error.log`
