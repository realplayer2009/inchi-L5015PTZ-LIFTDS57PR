# 电机控制器说明

## 控制器架构

项目包含两个独立的电机控制器：

### 1. PTZ云台控制器 (`ptz_controller.py`)

用于控制云台的YAW（方位）和PITCH（俯仰）两个轴。

- **YAW电机**: 地址ID = 1
- **PITCH电机**: 地址ID = 2

#### 主要功能

```python
from ptz_controller import create_ptz_controller

# 创建PTZ控制器
ptz = create_ptz_controller(port='COM6', baudrate=115200)

# 读取当前角度
yaw_angle = ptz.read_yaw_angle()        # 读取YAW角度
pitch_angle = ptz.read_pitch_angle()    # 读取PITCH角度

# 设置目标角度
ptz.set_yaw_angle(45.0, speed_rpm=100)      # 设置YAW到45°
ptz.set_pitch_angle(-30.0, speed_rpm=100)   # 设置PITCH到-30°

# 同时设置两个轴
ptz.set_ptz_angles(yaw_deg=45.0, pitch_deg=-30.0, speed_rpm=100)

# 启动后台监控（自动轮询电机状态）
ptz.start_monitoring(interval_ms=500)

# 获取缓存状态（无需等待通信）
yaw_status = ptz.get_yaw_status()
pitch_status = ptz.get_pitch_status()

# 关闭控制器
ptz.close()
```

#### 运行测试

```bash
python ptz_controller.py --port COM6
```

### 2. 升降电机控制器 (`lift_motor.py`)

用于控制升降电机（默认地址03）。

- **升降电机**: 地址ID = 3（可配置）

#### 主要功能

```python
from lift_motor import create_lift_controller

# 创建升降电机控制器
lift = create_lift_controller(port='COM6', baudrate=115200, motor_id=3)

# 读取当前位置
position = lift.read_position()           # 归一化位置 (±180°)
raw_position = lift.read_raw_position()   # 原始位置 (0-360°)

# 设置目标位置
lift.set_position(90.0, speed_rpm=100)

# 相对移动
lift.move_up(angle_deg=10.0, speed_rpm=100)    # 向上移动10°
lift.move_down(angle_deg=10.0, speed_rpm=100)  # 向下移动10°

# 停止电机
lift.stop()

# 启动后台监控
lift.start_monitoring(interval_ms=500)

# 获取缓存状态
status = lift.get_status()

# 关闭控制器
lift.close()
```

#### 运行测试

```bash
python lift_motor.py --port COM6 --id 3
```

## 控制器对比

| 特性 | PTZ云台控制器 | 升降电机控制器 |
|------|--------------|----------------|
| 电机数量 | 2个 (YAW + PITCH) | 1个 |
| 电机地址 | ID=1, ID=2 | ID=3 (可配置) |
| 主要用途 | 云台方位和俯仰控制 | 升降高度控制 |
| 角度控制 | 分别或同时控制两轴 | 单轴控制 |
| 相对移动 | 不支持 | 支持 (move_up/move_down) |

## 底层通信

两个控制器都基于 `rs485_comm.py` 模块进行RS485通信：

- **功能码 0xA3**: 读取电机状态（角度、温度等）
- **功能码 0xA4**: 设置目标角度

## GUI界面

使用 `motor_gui_tk.py` 提供图形界面监控和控制电机：

```bash
python motor_gui_tk.py --port COM6
```

GUI支持：
- 实时显示YAW和PITCH电机角度
- 设置目标角度
- 查看电机温度
- 自动连续读取

## 项目结构

```
inchiPTZ/
├── ptz_controller.py      # PTZ云台控制器 (YAW+PITCH)
├── lift_motor.py          # 升降电机控制器 (ID=3)
├── rs485_comm.py          # RS485通信底层
├── proto_v43.py           # 协议处理
├── motor_gui_tk.py        # Tkinter图形界面
└── test/                  # 测试和调试文件
    ├── test_angle_control.py
    ├── example_read_motors.py
    └── ...
```

## 注意事项

1. **电机地址**: 
   - PTZ控制器固定使用ID=1(YAW)和ID=2(PITCH)
   - 升降电机默认ID=3，可通过参数修改

2. **串口配置**:
   - 默认波特率: 115200
   - 默认串口: COM6
   - 可通过参数修改

3. **角度范围**:
   - 归一化角度: -180° ~ +180°
   - 原始角度: 0° ~ 360°

4. **线程安全**:
   - 两个控制器都支持后台监控线程
   - 状态读取使用锁保护，线程安全
