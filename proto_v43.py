"""协议 V4.3 帧解析 (已确认数据区 8 字节):

帧结构:
 Byte0   : 0x3E  (帧头)
 Byte1   : ID    (电机地址 1=Yaw, 2=Pitch ...)
 Byte2   : 0x08  (数据长度 = 8)
 Byte3-10: 数据区 8 字节
 Byte11-12: CRC16 (Modbus RTU 多项式 0xA001, 低字节在前)

总长度 13 字节。

字段暂定示例 (需按实际协议替换):
    data[0:2] -> angle int16 (0.01°)
    data[2:4] -> speed int16 (0.1°/s)
    data[4]   -> status bits1
    data[5]   -> fault bits / status bits2
    data[6]   -> temperature °C (uint8)
    data[7]   -> reserved / 扩展
"""
from __future__ import annotations
from typing import Optional, Tuple, List

FRAME_HEADER = 0x3E
CONST_LEN_BYTE = 0x08  # 数据长度=8
FRAME_SIZE = 13        # 1+1+1+8+2
DATA_SIZE = 8

def modbus_crc(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF

def verify_crc(frame: bytes) -> bool:
    if len(frame) != FRAME_SIZE:
        return False
    body = frame[:-2]
    crc_calc = modbus_crc(body)
    crc_lo = frame[-2]
    crc_hi = frame[-1]
    crc_recv = crc_lo | (crc_hi << 8)
    return crc_calc == crc_recv

def parse_frame(frame: bytes) -> Optional[Tuple[int, bytes]]:
    """解析单个完整帧。返回 (id, data8bytes) 或 None"""
    if len(frame) != FRAME_SIZE:
        return None
    if frame[0] != FRAME_HEADER:
        return None
    if frame[2] != CONST_LEN_BYTE:
        return None
    if not verify_crc(frame):
        return None
    addr = frame[1]
    data = frame[3:3+DATA_SIZE]
    return addr, data

def extract_frames(stream: bytes) -> List[Tuple[int, bytes]]:
    """在一段连续字节流中提取所有合法帧。"""
    results: List[Tuple[int, bytes]] = []
    i = 0
    L = len(stream)
    while i + FRAME_SIZE <= L:
        if stream[i] == FRAME_HEADER:
            candidate = stream[i:i+FRAME_SIZE]
            parsed = parse_frame(candidate)
            if parsed:
                results.append(parsed)
                i += FRAME_SIZE
                continue
        i += 1
    return results

def demo_decode_fields(data: bytes) -> dict:
    """V4.3协议字段拆解 (命令0x94响应)。
    
    数据格式:
      data[0]   -> 命令回显 0x94
      data[1:6] -> 保留字节 (待确认具体含义)
      data[6:8] -> 单圈角度 uint16 (0.01°/LSB, 0-35999)
    """
    if len(data) != DATA_SIZE:
        return {'raw': data.hex(), 'error': 'SIZE'}
    
    cmd_echo = data[0]
    reserved = data[1:6]
    angle_raw = int.from_bytes(data[6:8], 'little', signed=False)
    angle_0_360 = angle_raw / 100.0
    # 归一化到 -180 ~ +180
    angle_deg = angle_0_360 - 360.0 if angle_0_360 > 180.0 else angle_0_360
    
    return {
        'cmd_echo': f'0x{cmd_echo:02X}',
        'angle_raw': angle_raw,
        'angle_0_360': angle_0_360,
        'angle_deg': angle_deg,
        'reserved_hex': reserved.hex(),
        'raw_hex': data.hex()
    }
