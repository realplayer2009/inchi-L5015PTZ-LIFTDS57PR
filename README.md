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

**数据区字段** (命令0x94响应):
- `Byte0`: 0x94 (命令回显)
- `Byte1-5`: 保留字节 (当前为0x00)
- `Byte6-7`: 单圈角度 uint16 (0.01°/LSB, 范围0-35999 → 0.00-359.99°)

**读取角度命令**: `0x94`

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

### 3. 单次读取示例
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
  - `read_angle(motor_id)`: 读取归一化角度
  - `read_status(motor_id)`: 读取完整状态
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
4. **命令扩展**：当前仅实现0x94读取命令，可按需添加控制命令

## 常见问题

**Q: 图形界面无法启动？**
A: 确保已安装依赖 `pip install pyserial`，Tkinter是Python内置库无需安装。

**Q: 串口连接失败？**
A: 检查COM端口号是否正确，使用 `Get-WmiObject Win32_PnPEntity` 查看可用串口。

**Q: 角度跳变？**
A: 单圈角度在0°/360°边界会跳变，归一化后在±180°边界跳变属正常。

**Q: 如何添加新命令？**
A: 在 `rs485_comm.py` 中添加新命令常量和对应方法，参考 `CMD_READ_ANGLE = 0x94`。

## 许可证
内部项目示例，未附加外部许可证。
