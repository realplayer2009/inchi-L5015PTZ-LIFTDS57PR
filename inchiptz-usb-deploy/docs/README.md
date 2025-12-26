# 双轴云台伺服电机通信 (Python)

本项目通过 **RS485 Modbus** 与两台伺服电机 (01=Yaw, 02=Pitch) 通信，读取角度、速度、温度及状态信息。

## 协议规格 (V4.3)

**帧结构** (总长13字节):
```
Byte0    : 0x3E (帧头)
Byte1    : 电机ID (1=Yaw, 2=Pitch)
Byte2    : 0x08 (数据长度固定8字节)
Byte3-10 : 数据区 (8字节)
Byte11-12: CRC16 (Modbus RTU, 低字节在前)
```

**支持命令**:

### 0x94 - 读取单圈角度
**命令数据区**:
- `Byte0`: 0x94 (命令码)
- `Byte1-7`: 0x00 (填充字节)

**响应数据区**:
- `Byte0`: 0x94 (命令回显)
- `Byte1-5`: 保留字节 (当前为0x00)
- `Byte6-7`: 单圈角度 uint16 (0.01°/LSB, 范围0-35999 → 0.00-359.99°)

### 0xA4 - 设置目标角度 (位置控制)
**命令数据区**:
- `Byte0`: 0xA4 (命令码)
- `Byte1`: 0x00 (保留)
- `Byte2`: 速度限制低字节 (RPM)
- `Byte3`: 速度限制高字节 (RPM)
- `Byte4`: 位置控制低字节 (int16, 0.01°/LSB)
- `Byte5`: 位置控制高字节 (int16, 0.01°/LSB)
- `Byte6`: 多圈位置低字节 (固定0x00)
- `Byte7`: 多圈位置高字节 (固定0x00)

**响应数据区**:
- `Byte0`: 0xA4 (命令回显)
- `Byte1-7`: 响应数据 (具体含义待确认)

**说明**: 位置控制值为 int16 类型,角度范围 -180° ~ +180°,转换为 0.01°/LSB 单位 (-18000 ~ +18000)。速度限制单位为RPM,默认100。

**角度归一化**: 程序自动将超过180°的角度转换为负值表示 (-180° ~ +180°)

## 快速开始

### 安装依赖
```powershell
pip install -r requirements.txt
```

### 1. 图形界面监控（推荐）
```powershell
# 启动Tkinter图形界面
python motor_gui_tk.py --port COM6

# 点击右上角"打开串口并读取"按钮即可开始监控
```

**界面功能：**
- 右上角一键打开串口并自动开始读取
- 实时显示YAW和PITCH归一化角度（-180° ~ +180°）
- 显示原始角度（0° ~ 360°）和原始数值
- 连接状态指示灯
- 三个控制按钮：自动读取角度、开始监控、停止监控

### 2. 命令行持续读取
```powershell
# 持续读取并显示表格
python read_continuous.py --port COM6 --interval 0.5

# 输出示例：
# 时间         | YAW角度      | PITCH角度    | 状态
# 13:28:49     |   +0.18°     |  -53.20°     | OK
```

### 3. 角度控制测试 (0xA4命令)
```powershell
# 设置YAW电机到45°, 速度100RPM
python test_angle_control.py --port COM6 --motor 1 --angle 45.0 --speed 100

# 运行角度序列测试 (0° → 45° → 90° → -45° → -90° → 0°)
python test_angle_control.py --port COM6 --motor 1 --test-sequence --delay 3.0

# 测试PITCH电机
python test_angle_control.py --port COM6 --motor 2 --angle -30.0
```

### 4. 单次读取示例
```powershell
# 单次读取
python example_read_motors.py --port COM6

# 循环读取（详细信息）
python example_read_motors.py --port COM6 --loop --interval 0.5
```

## 返回数据格式

**`read_status()` 返回字典：**
```python
{
    'cmd_echo': '0x94',           # 命令回显
    'angle_raw': 6686,            # 原始数值 (0-35999)
    'angle_0_360': 66.86,         # 原始角度 (0-360°)
    'angle_deg': 66.86,           # 归一化角度 (-180~+180°)
    'reserved_bytes': [0,0,0,0,0],# 保留字节
    'raw_hex': '9400000000001e1a' # 原始帧数据(十六进制)
}
```

**`read_angle()` 直接返回角度值：**
```python
angle = comm.read_angle(motor_id=1)  # 返回 -180.00 ~ +180.00
```

## 文件说明

### 核心模块
- **`rs485_comm.py`**: RS485通信类（协议V4.3）
  - `read_angle(motor_id)`: 读取归一化角度 (0x94命令)
  - `read_status(motor_id)`: 读取完整状态
  - `set_target_angle(motor_id, target_deg, speed_rpm)`: 设置目标角度 (0xA4命令)
  - 自动重试、超时处理、CRC校验

- **`proto_v43.py`**: 协议解析工具
  - 帧解析与CRC验证
  - 字段拆解函数

### 应用程序
- **`motor_gui_tk.py`**: Tkinter图形界面（推荐）
  - 无需额外依赖（Python内置）
  - 右上角按钮一键打开串口
  - 实时显示双轴角度

- **`read_continuous.py`**: 持续读取命令行工具
  - 表格形式显示实时数据
  - 统计读取次数

- **`example_read_motors.py`**: 详细信息读取示例
  - 显示所有字段
  - 支持循环模式

- **`test_angle_control.py`**: 角度控制测试工具 (0xA4命令)
  - 单角度测试: `--angle 45.0`
  - 序列测试: `--test-sequence`
  - 实时反馈控制效果

- **`angle_read_v43.py`**: 单独角度读取工具
- **`read_motor_status_v43.py`**: 被动监听串口帧流

### 其他文件
- **`controller.py`**: 旧版控制器（待更新到V4.3）
- **`requirements.txt`**: Python依赖（pyserial, PyQt5）

## API 使用示例

```python
from rs485_comm import RS485Comm

# 初始化通信
comm = RS485Comm(port='COM6', baudrate=115200)

# 读取归一化角度 (-180° ~ +180°)
yaw_angle = comm.read_angle(motor_id=1)
pitch_angle = comm.read_angle(motor_id=2)
print(f"YAW: {yaw_angle:.2f}°, PITCH: {pitch_angle:.2f}°")

# 读取完整状态
status = comm.read_status(motor_id=1)
print(f"原始角度: {status['angle_0_360']:.2f}°")
print(f"归一化角度: {status['angle_deg']:.2f}°")
print(f"原始数值: {status['angle_raw']}")

# 设置目标角度 (0xA4命令)
result = comm.set_target_angle(motor_id=1, target_deg=45.0, speed_rpm=100)
if result and result['success']:
    print(f"目标角度设置成功: {result['target_deg']}°")
    print(f"速度限制: {result['speed_rpm']} RPM")
    print(f"控制值: {result['angle_control']}")
else:
    print("设置失败")

# 关闭串口
comm.close()
```

## 技术细节

### 角度归一化
- 原始范围：0-35999 (对应 0.00° ~ 359.99°)
- 归一化后：超过180°自动转换为负值
- 例如：307.99° → -52.01°
- 目的：便于计算最短旋转路径

### 通信参数
- 串口：CH340 (USB-SERIAL)
- 波特率：115200
- CRC：Modbus CRC16 (多项式0xA001, 低字节在前)
- 超时：200ms
- 重试次数：3次

### 硬件连接
- 调试器：Serial CH340
- 电机ID：1=Yaw, 2=Pitch
- 波特率：115200 (可配置)

## 注意事项

1. **串口独占**：同时只能一个程序打开串口
2. **数据字段**：Byte1-5保留字节当前未使用，未来可能扩展
3. **角度范围**：单圈角度0-360°，如需多圈需额外处理
4. **命令支持**：
   - **0x94**: 读取单圈角度 (已实现并测试)
   - **0xA4**: 设置目标角度 (已实现，待硬件测试)
5. **角度控制**：`set_target_angle()` 使用速度限制和位置控制模式，角度范围 -180° ~ +180°

## 常见问题

**Q: 图形界面无法启动？**
A: 确保已安装依赖 `pip install pyserial`，Tkinter是Python内置库无需安装。

**Q: 串口连接失败？**
A: 检查COM端口号是否正确，使用 `Get-WmiObject Win32_PnPEntity` 查看可用串口。

**Q: 角度跳变？**
A: 单圈角度在0°/360°边界会跳变，归一化后在±180°边界跳变属正常。

**Q: 如何添加新命令？**
A: 在 `rs485_comm.py` 中添加新命令常量和对应方法，参考 `CMD_READ_ANGLE = 0x94` 和 `CMD_READ_STATUS_A4 = 0xA4`。

**Q: 0xA4命令的数据格式？**
A: 当前按通用格式解析，返回7个数据字节。具体字段含义需根据实际协议文档在 `read_status_a4()` 方法中调整解析逻辑。

## Ubuntu系统部署（deb包安装）

本项目提供了完整的Ubuntu系统部署方案，通过deb包安装，实现Flask API服务器自动启动和管理。

### 功能特性

- **Flask API服务器**：监听 `127.0.0.1:50278`，提供HTTP接口控制PTZ电机
- **JSON格式交互**：接收和返回JSON格式数据，便于集成
- **角度范围验证**：旋转角度限制-85°~+85°，俯仰角度限制-10°~+85°
- **500ms轮询**：自动轮询电机状态，实时更新角度和温度数据
- **异常处理**：完善的串口断开检测和错误报告机制
- **日志记录**：分离的操作日志和错误日志，带时间戳，自动轮转（1MB限制）
- **systemd服务**：开机自启动，异常自动重启

### 构建deb包

在Ubuntu系统上执行以下命令：

```bash
# 给构建脚本添加执行权限
chmod +x build_deb.sh

# 构建deb包
./build_deb.sh
```

构建完成后会生成 `inchiptz_1.0.0_all.deb` 文件。

### 安装deb包

```bash
# 安装deb包
sudo dpkg -i inchiptz_1.0.0_all.deb

# 如果出现依赖问题，运行
sudo apt-get install -f
```

### 服务管理

```bash
# 启动服务
sudo systemctl start inchiptz

# 停止服务
sudo systemctl stop inchiptz

# 查看服务状态
sudo systemctl status inchiptz

# 查看实时日志
sudo journalctl -u inchiptz -f

# 禁用开机自启动
sudo systemctl disable inchiptz

# 启用开机自启动
sudo systemctl enable inchiptz
```

### 查看日志

```bash
# 查看操作日志
cat /var/log/inchiptz/operation.log

# 查看错误日志
cat /var/log/inchiptz/error.log

# 实时跟踪日志
tail -f /var/log/inchiptz/operation.log
tail -f /var/log/inchiptz/error.log
```

### API使用说明

#### 1. 设置PTZ位置

**接口**: `POST http://127.0.0.1:50278/set_position`

**请求格式**（JSON）:
```json
{
  "yaw": 45.2,
  "pitch": -12.5
}
```

**成功响应**:
```json
{
  "success": true
}
```

**失败响应**:
```json
{
  "success": false,
  "error": "旋转角度超出范围，允许范围：-85° 到 +85°",
  "code": 400
}
```

**curl示例**:
```bash
curl -X POST http://127.0.0.1:50278/set_position \
  -H "Content-Type: application/json" \
  -d '{"yaw": 30.5, "pitch": 20.0}'
```

#### 2. 获取PTZ状态

**接口**: `GET http://127.0.0.1:50278/get_status`

**成功响应**:
```json
{
  "success": true,
  "yaw_angle": 45.2,
  "pitch_angle": -12.5,
  "yaw_temperature": 38,
  "pitch_temperature": 40
}
```

**失败响应**:
```json
{
  "success": false,
  "error": "串口通信失败，请检查设备连接",
  "code": 500
}
```

**curl示例**:
```bash
curl http://127.0.0.1:50278/get_status
```

#### 3. 健康检查

**接口**: `GET http://127.0.0.1:50278/health`

**响应**:
```json
{
  "healthy": true,
  "serial_connected": true
}
```

**curl示例**:
```bash
curl http://127.0.0.1:50278/health
```

### 角度范围限制

- **旋转（YAW）**: -85° 到 +85°
- **俯仰（PITCH）**: -10° 到 +85°

超出范围的角度请求将返回400错误，并在错误日志中记录。

### 错误代码说明

| 错误码 | 说明 |
|-------|------|
| 400 | 参数错误（缺少参数、格式错误、角度超出范围） |
| 500 | 服务器错误（串口通信失败、电机控制失败） |

### 串口设备配置

默认串口设备路径为 `/dev/ttyUSB0`（RJ45转串口设备）。如需修改，编辑systemd服务文件：

```bash
sudo nano /etc/systemd/system/inchiptz.service
```

修改 `ExecStart` 行中的 `--port` 参数，例如：

```ini
ExecStart=/usr/bin/python3 /usr/share/inchiptz/api_server.py --port /dev/ttyS0 ...
```

修改后重新加载并重启服务：

```bash
sudo systemctl daemon-reload
sudo systemctl restart inchiptz
```

### 串口权限配置

确保用户在 `dialout` 组中，以便访问串口设备：

```bash
# 添加当前用户到dialout组
sudo usermod -a -G dialout $USER

# 注销并重新登录以使更改生效
```

### 卸载

```bash
# 卸载deb包
sudo dpkg -r inchiptz

# 清理日志文件（可选）
sudo rm -rf /var/log/inchiptz
```

### Python直接运行（无需安装deb包）

如果不想安装deb包，也可以直接运行API服务器：

```bash
# 安装依赖
pip install flask pyserial

# 创建日志目录
sudo mkdir -p /var/log/inchiptz
sudo chmod 755 /var/log/inchiptz

# 运行API服务器
python3 api_server.py --port /dev/ttyUSB0 --yaw-id 1 --pitch-id 2
```

### 故障排查

**Q: 服务无法启动？**
A: 检查串口设备是否存在：`ls -l /dev/ttyUSB*`，确认用户在dialout组中：`groups`

**Q: API返回串口通信失败？**
A: 检查串口设备连接，查看错误日志：`cat /var/log/inchiptz/error.log`

**Q: 如何查看详细的通信日志？**
A: 查看操作日志：`cat /var/log/inchiptz/operation.log`，包含所有API调用记录

**Q: 日志文件过大？**
A: 日志文件自动轮转，单个文件最大1MB，保留3个备份文件

## 许可证
内部项目示例，未附加外部许可证。
