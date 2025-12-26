"""RS485 通信层：协议V4.3 (帧头0x3E, 数据区8字节, Modbus CRC)。
支持命令发送、响应解析、重试与超时。
"""
from __future__ import annotations
import time
import threading
from typing import Optional, Dict, Any
import serial  # type: ignore
from pymodbus.client import ModbusSerialClient, ModbusTcpClient
import socket

# 协议常量
FRAME_HEADER = 0x3E
DATA_LENGTH = 0x08
FRAME_SIZE = 13
DATA_SIZE = 8

# 命令码
CMD_READ_ANGLE = 0x94
CMD_READ_STATUS_A4 = 0xA4
CMD_CLOSE = 0x80
CMD_STOP = 0x81
CMD_BROADCAST = 0xCD  # 广播地址，用于同时控制多个电机

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
        self._tcp_mode = False
        self._tcp_sock = None
        # 支持TCP RTU: 传入格式 host:port 例如 192.168.25.78:502
        if port and (":" in port):
            host, port_str = port.split(":", 1)
            try:
                tcp_port = int(port_str)
                self._tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._tcp_sock.settimeout(timeout)
                self._tcp_sock.connect((host, tcp_port))
                self._available = True
                self._tcp_mode = True
            except Exception:
                self._tcp_sock = None
                self._available = False
        else:
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
                    if self._tcp_mode and self._tcp_sock:
                        self._tcp_sock.sendall(frame)
                        t0 = time.time()
                        buf = b''
                        while time.time() - t0 < timeout:
                            remaining = FRAME_SIZE - len(buf)
                            if remaining > 0:
                                chunk = self._tcp_sock.recv(remaining)
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
                    else:
                        self._ser.reset_input_buffer()
                        self._ser.write(frame)
                        self._ser.flush()
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
          Byte1: 保留数据 (reserved; verify protocol for meaning)
          Byte2-5: 保留数据
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
        """读取电机状态（角度+温度+其他数据），返回字典或None
        
        响应数据格式 (8字节):
          Byte0: 0x94 (命令回显)
          Byte1: 电机温度 int8_t (1℃/LSB)
          Byte2-5: 预留数据区
          Byte6-7: 单圈角度 uint16 (0.01°/LSB, 0-35999 => 0-359.99°)
        """
        data = self.transact(motor_id, CMD_READ_ANGLE)
        if data is None or len(data) != DATA_SIZE:
            return None
        
        cmd_echo = data[0]
        # Byte1: 电机温度 (int8_t, 1℃/LSB)
        temperature = int.from_bytes([data[1]], 'little', signed=True)
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
            'temperature': temperature,
            'reserved_bytes': [reserved_2, reserved_3, reserved_4, reserved_5],
            'raw_hex': data.hex()
        }

    def set_target_angle(self, motor_id: int, target_deg: float, speed_rpm: int = 100) -> Optional[Dict[str, Any]]:
        """设置电机目标角度（命令0xA4）
        
        参数:
            motor_id: 电机ID (1=Yaw, 2=Pitch)
            target_deg: 目标角度(度)，范围 -180° ~ +180° 或 0° ~ 360°
            speed_rpm: 速度限制(RPM)，默认100
        
        命令数据格式 (8字节):
          Byte0: 0xA4 (命令码)
          Byte1: 0x00 (保留)
          Byte2: 速度限制低字节 (RPM)
          Byte3: 速度限制高字节
          Byte4: 位置控制字节0 (int32_t低字节, 0.01°/LSB)
          Byte5: 位置控制字节1
          Byte6: 位置控制字节2
          Byte7: 位置控制字节3 (int32_t高字节)
          
        示例: 10° = 1000 LSB = 0x000003E8 -> [0xE8, 0x03, 0x00, 0x00]
        
        响应数据格式 (8字节):
          Byte0: 0xA4 (命令回显)
          Byte1: 电机温度 int8_t (1℃/LSB)
          Byte2-7: 其他状态数据
        
        返回: 响应字典或None
        """
        # 归一化角度到 -180 ~ +180
        if target_deg > 180.0:
            target_deg -= 360.0
        elif target_deg < -180.0:
            target_deg += 360.0
        
        # 转换为 0.01°/LSB 的 int32
        angle_control = int(target_deg * 100)
        # 检查是否在 int32_t 范围内
        if not (-2147483648 <= angle_control <= 2147483647):
            raise ValueError(f"angle_control {angle_control} out of int32_t range")
        
        # 构建payload (注意: Byte1=0x00保留字节)
        speed_low = speed_rpm & 0xFF
        speed_high = (speed_rpm >> 8) & 0xFF
        
        # 位置控制 int32_t (4字节, little-endian)
        angle_bytes = angle_control.to_bytes(4, byteorder='little', signed=True)
        
        payload = bytes([
            0x00,              # Byte1: 保留字节
            speed_low,         # Byte2: 速度限制低字节
            speed_high,        # Byte3: 速度限制高字节
            angle_bytes[0],    # Byte4: 位置控制字节0 (低字节)
            angle_bytes[1],    # Byte5: 位置控制字节1
            angle_bytes[2],    # Byte6: 位置控制字节2
            angle_bytes[3]     # Byte7: 位置控制字节3 (高字节)
        ])
        
        data = self.transact(motor_id, CMD_READ_STATUS_A4, payload)
        if data is None or len(data) != DATA_SIZE:
            return None
        
        cmd_echo = data[0]
        # Byte1: 电机温度 (int8_t, 1℃/LSB)
        temperature = int.from_bytes([data[1]], 'little', signed=True)
        
        return {
            'cmd_echo': f'0x{cmd_echo:02X}',
            'success': cmd_echo == CMD_READ_STATUS_A4,
            'target_deg': target_deg,
            'speed_rpm': speed_rpm,
            'angle_control': angle_control,
            'temperature': temperature,
            'raw_hex': data.hex()
        }

    def close_motor(self, motor_id: int) -> Optional[Dict[str, Any]]:
        """发送电机关闭指令 (命令0x80)
        
        参数:
            motor_id: 电机ID
            
        命令数据格式 (8字节):
          Byte0: 0x80 (命令码)
          Byte1-7: 0x00 (保留)
          
        响应数据格式 (8字节):
          Byte0: 0x80 (命令回显)
          Byte1-7: 其他数据 (不解析温度)
        
        返回: 响应字典或None
        """
        # 发送关闭命令，payload 为空（全0）
        data = self.transact(motor_id, CMD_CLOSE)
        if data is None or len(data) != DATA_SIZE:
            return None
        
        cmd_echo = data[0]
        
        return {
            'cmd_echo': f'0x{cmd_echo:02X}',
            'success': cmd_echo == CMD_CLOSE,
            'raw_hex': data.hex()
        }
    
    def stop_motor(self, motor_id: int) -> Optional[Dict[str, Any]]:
        """发送电机停止指令 (命令0x81)
        
        参数:
            motor_id: 电机ID
            
        命令数据格式 (8字节):
          Byte0: 0x81 (命令码)
          Byte1-7: 0x00 (保留)
          
        响应数据格式 (8字节):
          Byte0: 0x81 (命令回显)
          Byte1-7: 其他数据
        
        返回: 响应字典或None
        """
        # 发送停止命令，payload 为空（全0）
        data = self.transact(motor_id, CMD_STOP)
        if data is None or len(data) != DATA_SIZE:
            return None
        
        cmd_echo = data[0]
        
        return {
            'cmd_echo': f'0x{cmd_echo:02X}',
            'success': cmd_echo == CMD_STOP,
            'raw_hex': data.hex()
        }
    
    def broadcast_shutdown(self) -> bool:
        """广播关闭所有电机 (命令0xCD, 数据0x80)
        
        命令格式:
          帧头: 0x3E
          ID: 0xCD (广播地址)
          数据长度: 0x08
          数据区: 0x80 00 00 00 00 00 00 00 (8字节)
          CRC: 2字节
        
        返回: 成功返回True，广播指令无响应
        """
        # 构建广播帧：0x3E 0xCD 0x08 0x80 00 00 00 00 00 00 00 + CRC
        # motor_id=0xCD, cmd=0x80, payload为空（会自动填充7个0x00）
        frame = self._build_frame(CMD_BROADCAST, CMD_CLOSE, b'')
        
        with self._lock:
            if not self._available:
                return False
            try:
                if self._tcp_mode and self._tcp_sock:
                    self._tcp_sock.sendall(frame)
                else:
                    self._ser.write(frame)
                    self._ser.flush()
                # 广播指令无响应，稍等后返回
                time.sleep(0.05)
            except Exception as e:
                # 忽略异常，认为已发出
                pass
            return True
    
    def broadcast_stop(self) -> bool:
        """广播停止所有电机 (命令0xCD, 数据0x81)
        
        命令格式:
          帧头: 0x3E
          ID: 0xCD (广播地址)
          数据长度: 0x08
          数据区: 0x81 00 00 00 00 00 00 00 (8字节)
          CRC: 2字节
        
        返回: 成功返回True，广播指令无响应
        """
        # 构建广播帧：0x3E 0xCD 0x08 0x81 00 00 00 00 00 00 00 + CRC
        # motor_id=0xCD, cmd=0x81, payload为空（会自动填充7个0x00）
        frame = self._build_frame(CMD_BROADCAST, CMD_STOP, b'')
        
        with self._lock:
            if not self._available:
                return False
            try:
                if self._tcp_mode and self._tcp_sock:
                    self._tcp_sock.sendall(frame)
                else:
                    self._ser.write(frame)
                    self._ser.flush()
                # 广播指令无响应，稍等后返回
                time.sleep(0.05)
                return True
            except Exception:
                return False

    def close(self):
        """关闭串口或TCP连接"""
        if self._tcp_mode and self._tcp_sock:
            try:
                self._tcp_sock.close()
            except Exception:
                pass
            self._tcp_sock = None
        elif hasattr(self, '_ser') and self._ser:
            self._ser.close()
