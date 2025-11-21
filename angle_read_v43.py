"""发送命令 0x94 读取单圈角度 (协议V4.3, 帧头0x3E, 数据区8字节, CRC=Modbus CRC16)。

当前假设 (若与实际协议不符请告知)：
  - 读取角度命令帧：
      Byte0: 0x3E
      Byte1: ID
      Byte2: 0x08 (数据长度=8)
      Byte3-10 数据区：data[0]=0x94(命令码)，其余填0x00
      Byte11-12: CRC16 (低字节在前)
  - 响应帧格式与状态帧相同，数据区的前2字节为角度 int16 (0.01°)。
  - 其余字节保留或为状态位，暂不深入解析。

如果实际格式不同（例如命令码放在第2字节或需要附加参数），请提供正式定义，我会更新。
"""
from __future__ import annotations
import serial  # type: ignore
from typing import Optional, Dict, Any
import time
from proto_v43 import modbus_crc, FRAME_HEADER, CONST_LEN_BYTE, FRAME_SIZE, DATA_SIZE, parse_frame

CMD_READ_SINGLE_TURN = 0x94

def build_cmd_frame(motor_id: int, cmd: int, payload: bytes = b'') -> bytes:
    """构建命令帧。payload 附加在 cmd 后面 (总数据区不超过8字节)"""
    if len(payload) > DATA_SIZE - 1:
        raise ValueError('payload too long')
    data = bytes([cmd]) + payload + bytes([0x00] * (DATA_SIZE - 1 - len(payload)))
    body = bytes([FRAME_HEADER, motor_id & 0xFF, CONST_LEN_BYTE]) + data
    crc = modbus_crc(body)
    return body + bytes([crc & 0xFF, (crc >> 8) & 0xFF])

def decode_angle_from_data(data: bytes) -> Optional[float]:
    """从响应数据中提取角度 (Byte6-7: uint16, 0.01°/LSB)
    返回归一化角度 -180° ~ +180°
    """
    if len(data) != DATA_SIZE:
        return None
    # 最后2字节角度 uint16 (0.01°), 范围0-35999
    raw = int.from_bytes(data[6:8], 'little', signed=False)
    angle = raw / 100.0
    # 归一化到 -180 ~ +180
    if angle > 180.0:
        angle -= 360.0
    return angle

def read_single_turn_angle(ser: serial.Serial, motor_id: int, timeout: float = 0.2) -> Dict[str, Any]:
    frame = build_cmd_frame(motor_id, CMD_READ_SINGLE_TURN)
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    t0 = time.time()
    buf = b''
    while time.time() - t0 < timeout:
        chunk = ser.read(FRAME_SIZE - len(buf))
        if chunk:
            buf += chunk
        if len(buf) >= FRAME_SIZE:
            parsed = parse_frame(buf[:FRAME_SIZE])
            if parsed is None:
                return {'ok': False, 'error': 'BAD_FRAME', 'raw_hex': buf.hex()}
            addr, data = parsed
            if addr != motor_id:
                return {'ok': False, 'error': 'ADDR_MISMATCH', 'raw_hex': buf.hex()}
            angle = decode_angle_from_data(data)
            return {
                'ok': True,
                'angle_deg': angle,
                'raw_data_hex': data.hex(),
                'raw_frame_hex': buf[:FRAME_SIZE].hex()
            }
    return {'ok': False, 'error': 'TIMEOUT'}

def demo_cli():
    import argparse
    parser = argparse.ArgumentParser(description='读取单圈角度 (命令0x94)')
    parser.add_argument('--port', required=True)
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--timeout', type=float, default=0.2)
    parser.add_argument('--id', type=int, default=1)
    args = parser.parse_args()
    ser = serial.Serial(port=args.port, baudrate=args.baud, timeout=0.05)
    try:
        res = read_single_turn_angle(ser, args.id, timeout=args.timeout)
        if res.get('ok'):
            print(f"ID {args.id} angle={res['angle_deg']:.2f}° raw={res['raw_data_hex']}")
        else:
            print(f"读取失败: {res}")
    finally:
        ser.close()

if __name__ == '__main__':
    demo_cli()
