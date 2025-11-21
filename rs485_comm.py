"""RS485 通信层：协议V4.3 (帧头0x3E, 数据区8字节, Modbus CRC)。
支持命令发送、响应解析、重试与超时。
"""
from __future__ import annotations
import time
import threading
from typing import Optional, Dict, Any
import serial  # type: ignore

# 协议常量
FRAME_HEADER = 0x3E
DATA_LENGTH = 0x08
FRAME_SIZE = 13
DATA_SIZE = 8

# 命令码
CMD_READ_ANGLE = 0x94

def modbus_crc(data: bytes) -> int:
    """Modbus CRC16 计算"""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF

class RS485Comm:
    """RS485 通信类，使用协议V4.3 (0x3E帧头)"""
    
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 0.2, max_retries: int = 3):
        self._lock = threading.Lock()
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._max_retries = max_retries
        try:
            self._ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout
            )
            self._available = True
        except Exception:
            self._ser = None
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def _build_frame(self, motor_id: int, cmd: int, payload: bytes = b'') -> bytes:
        """构建命令帧。payload附加在cmd后，数据区总长度8字节"""
        if len(payload) > DATA_SIZE - 1:
            raise ValueError('payload too long')
        data = bytes([cmd]) + payload + bytes([0x00] * (DATA_SIZE - 1 - len(payload)))
        body = bytes([FRAME_HEADER, motor_id & 0xFF, DATA_LENGTH]) + data
        crc = modbus_crc(body)
        return body + bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    def _parse_frame(self, frame: bytes) -> Optional[tuple[int, bytes]]:
        """解析响应帧。返回 (motor_id, data8bytes) 或 None"""
        if len(frame) != FRAME_SIZE:
            return None
        if frame[0] != FRAME_HEADER:
            return None
        if frame[2] != DATA_LENGTH:
            return None
        # 验证CRC
        body = frame[:-2]
        crc_calc = modbus_crc(body)
        crc_lo = frame[-2]
        crc_hi = frame[-1]
        crc_recv = crc_lo | (crc_hi << 8)
        if crc_calc != crc_recv:
            return None
        motor_id = frame[1]
        data = frame[3:3+DATA_SIZE]
        return motor_id, data

    def transact(self, motor_id: int, cmd: int, payload: bytes = b'', timeout: float = None) -> Optional[bytes]:
        """发送命令并等待响应，返回数据区8字节或None"""
        if timeout is None:
            timeout = self._timeout
        frame = self._build_frame(motor_id, cmd, payload)
        
        for attempt in range(self._max_retries + 1):
            with self._lock:
                if not self._available:
                    return None
                try:
                    self._ser.reset_input_buffer()
                    self._ser.write(frame)
                    self._ser.flush()
                    
                    # 等待完整响应帧
                    t0 = time.time()
                    buf = b''
                    while time.time() - t0 < timeout:
                        remaining = FRAME_SIZE - len(buf)
                        if remaining > 0:
                            chunk = self._ser.read(remaining)
                            if chunk:
                                buf += chunk
                        if len(buf) >= FRAME_SIZE:
                            break
                        time.sleep(0.001)
                    
                    if len(buf) < FRAME_SIZE:
                        if attempt == self._max_retries:
                            return None
                        time.sleep(0.01)
                        continue
                        
                except Exception:
                    if attempt == self._max_retries:
                        return None
                    time.sleep(0.01)
                    continue
            
            parsed = self._parse_frame(buf[:FRAME_SIZE])
            if parsed is None:
                if attempt == self._max_retries:
                    return None
                time.sleep(0.01)
                continue
            
            resp_id, data = parsed
            if resp_id != motor_id:
                if attempt == self._max_retries:
                    return None
                time.sleep(0.01)
                continue
            
            return data
        
        return None

    def read_angle(self, motor_id: int) -> Optional[float]:
        """读取单圈角度 (命令0x94)，返回角度值(度)或None
        
        响应数据格式:
          Byte0: 0x94 (命令回显)
          Byte1-5: 保留数据
          Byte6-7: 角度 uint16 (0.01°/LSB, 范围0-35999)
        
        返回值: -180.00° ~ +180.00° (超过180°转换为负角度)
        """
        data = self.transact(motor_id, CMD_READ_ANGLE)
        if data is None or len(data) < 8:
            return None
        # 最后2字节为角度 uint16 (0.01°)
        raw = int.from_bytes(data[6:8], 'little', signed=False)
        angle = raw / 100.0
        # 归一化到 -180 ~ +180
        if angle > 180.0:
            angle -= 360.0
        return angle

    def read_status(self, motor_id: int) -> Optional[Dict[str, Any]]:
        """读取电机状态（角度+其他数据），返回字典或None
        
        响应数据格式 (8字节):
          Byte0: 0x94 (命令回显)
          Byte1-5: 预留数据区 (具体含义待确认)
          Byte6-7: 单圈角度 uint16 (0.01°/LSB, 0-35999 => 0-359.99°)
        """
        data = self.transact(motor_id, CMD_READ_ANGLE)
        if data is None or len(data) != DATA_SIZE:
            return None
        
        cmd_echo = data[0]
        reserved_1 = data[1]
        reserved_2 = data[2]
        reserved_3 = data[3]
        reserved_4 = data[4]
        reserved_5 = data[5]
        angle_raw = int.from_bytes(data[6:8], 'little', signed=False)
        angle_0_360 = angle_raw / 100.0
        # 归一化到 -180 ~ +180
        angle_deg = angle_0_360 - 360.0 if angle_0_360 > 180.0 else angle_0_360
        
        return {
            'cmd_echo': f'0x{cmd_echo:02X}',
            'angle_raw': angle_raw,
            'angle_0_360': angle_0_360,
            'angle_deg': angle_deg,
            'reserved_bytes': [reserved_1, reserved_2, reserved_3, reserved_4, reserved_5],
            'raw_hex': data.hex()
        }

    def close(self):
        """关闭串口"""
        if self._ser:
            self._ser.close()
