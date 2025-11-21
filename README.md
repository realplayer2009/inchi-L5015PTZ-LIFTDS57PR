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

**数据区字段** (暂定示例):
- `Byte0-1`: 角度 int16 (单位0.01°)
- `Byte2-3`: 速度 int16 (单位0.1°/s)
- `Byte4`: 状态位1
- `Byte5`: 状态位2
- `Byte6`: 温度 (°C, uint8)
- `Byte7`: 保留

**读取角度命令**: `0x94`

## 角度范围
- Yaw: -90° ~ +90°
- Pitch: -10° ~ +80°

## 返回格式 (示例)
```python
{
  "yaw": {
    "raw_deg": 12.34,          # 编码器原始角(度)
    "corrected_deg": 12.10,    # 应用零点与归一后角(度)
    "rad": 0.211,              # 弧度
    "in_range": True,          # 是否在软限位内
    "faults": []               # 轴级故障标志列表
  },
  "pitch": {
    "raw_deg": 5.02,
    "corrected_deg": 4.90,
    "rad": 0.0855,
    "in_range": True,
    "faults": []
  },
  "status": {
    "timestamp": 123456.789,   # 单调时钟(s)
    "comm_ok": True,
    "controller_faults": [],   # 全局故障(通信/范围/编码器等)
    "age_ms": 120              # 距离最近一次成功轮询的时间
  }
}
```

## 快速开始
```bash
pip install -r requirements.txt
python app.py
```

## 目录结构
- `config.py` 配置与参数
- `crc16.py` CRC16算法 (Modbus)
- `protocol_spec.md` 协议说明
- `rs485_comm.py` 物理/帧通信与重试
- `gimbal_axis.py` 轴抽象与角度处理
- `safety.py` 安全与故障管理
- `controller.py` 控制器与后台轮询线程
- `api.py` 外部API封装
- `app.py` 示例运行入口

## 扩展建议
- 多圈支持：累计跨零计数
- IMU融合：姿态滤波增强动态稳定
- 异步事件：角度变化阈值触发回调

## 协议概要
详见 `protocol_spec.md`。

## 许可证
内部项目示例，未附加外部许可证。
