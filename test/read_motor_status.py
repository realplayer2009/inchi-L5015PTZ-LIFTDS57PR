"""读取 01(Yaw) 与 02(Pitch) 伺服电机状态 (角度/速度/故障) 通过 RS485 Modbus RTU。

可根据协议 PDF 修改寄存器地址与解析逻辑。

运行示例:
    python read_motor_status.py --port COM3 --baud 115200 --loop

按 Ctrl+C 退出循环。
"""
from __future__ import annotations
import argparse
import struct
import time
from typing import Dict, Any, Tuple, Optional

import serial  # type: ignore

# ---------------- 寄存器映射 (根据实际协议调整) -----------------
# 假设: 角度(int16, 单位0.01度), 速度(int16, 单位0.1度/秒), 故障码(uint16, 位标志)
REG_ANGLE = 0x0000
REG_SPEED = 0x0001
REG_FAULT = 0x0002

# 一次性读取连续3个寄存器
READ_COUNT = 3

# ---------------- Modbus RTU CRC16 -----------------
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

def build_read_req(address: int, start_reg: int, count: int) -> bytes:
    p = struct.pack('>B B H H', address & 0xFF, 0x03, start_reg & 0xFFFF, count & 0xFFFF)
    crc = modbus_crc(p)
    return p + struct.pack('<H', crc)

def parse_read_resp(address: int, req_func: int, frame: bytes) -> Optional[bytes]:
    # 最小: addr(1)+func(1)+bytecount(1)+crc(2)
    if len(frame) < 5:
        return None
    # 校验CRC
    data_part = frame[:-2]
    crc_recv = struct.unpack('<H', frame[-2:])[0]
    crc_calc = modbus_crc(data_part)
    if crc_recv != crc_calc:
        return None
    addr = frame[0]
    func = frame[1]
    if addr != (address & 0xFF) or func != req_func:
        return None
    byte_count = frame[2]
    payload = frame[3:3+byte_count]
    if len(payload) != byte_count:
        return None
    return payload

def read_motor(ser: serial.Serial, unit_id: int) -> Dict[str, Any]:
    req = build_read_req(unit_id, REG_ANGLE, READ_COUNT)
    ser.reset_input_buffer()
    ser.write(req)
    ser.flush()
    # 响应最大: addr+func+bytecount+N*2 + crc2
    raw = ser.read(3 + READ_COUNT * 2 + 2)
    payload = parse_read_resp(unit_id, 0x03, raw)
    if payload is None or len(payload) < READ_COUNT * 2:
        return {
            'ok': False,
            'error': 'BAD_FRAME',
        }
    # 解包3个寄存器
    angle_raw, speed_raw, fault_raw = struct.unpack('>hhh', payload[:READ_COUNT*2])
    angle_deg = angle_raw / 100.0
    speed_deg_s = speed_raw / 10.0
    fault_code = fault_raw & 0xFFFF
    return {
        'ok': True,
        'angle_deg': angle_deg,
        'speed_deg_s': speed_deg_s,
        'fault_code': fault_code,
        'fault_bits': decode_fault_bits(fault_code),
    }

def decode_fault_bits(code: int) -> Dict[str, bool]:
    # 根据协议定义位意义，临时示例：
    mapping = {
        'OVER_CURRENT': bool(code & 0x0001),
        'OVER_TEMP': bool(code & 0x0002),
        'ENCODER_FAIL': bool(code & 0x0004),
        'COMM_TIMEOUT': bool(code & 0x0008),
        'RANGE_EXCEEDED': bool(code & 0x0010),
    }
    return mapping

def pretty_print(unit: int, status: Dict[str, Any]) -> None:
    if not status.get('ok'):
        print(f"[ID {unit:02d}] 通信失败: {status.get('error')}")
        return
    bits = status['fault_bits']
    active_faults = [k for k,v in bits.items() if v]
    print(
        f"[ID {unit:02d}] 角度: {status['angle_deg']:.2f}° | 速度: {status['speed_deg_s']:.2f}°/s | 故障码: 0x{status['fault_code']:04X} | 活动故障: {', '.join(active_faults) if active_faults else '无'}"
    )

def main():
    parser = argparse.ArgumentParser(description='读取双轴伺服电机状态 (Modbus RTU)')
    parser.add_argument('--port', required=True, help='串口号, 如 COM3')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--timeout', type=float, default=0.2, help='串口读超时秒')
    parser.add_argument('--loop', action='store_true', help='循环轮询')
    parser.add_argument('--interval', type=float, default=0.5, help='循环间隔秒')
    parser.add_argument('--yaw-id', type=int, default=1, help='Yaw 电机 Modbus 地址')
    parser.add_argument('--pitch-id', type=int, default=2, help='Pitch 电机 Modbus 地址')
    args = parser.parse_args()

    ser = serial.Serial(port=args.port, baudrate=args.baud, timeout=args.timeout)
    try:
        def once():
            y = read_motor(ser, args.yaw_id)
            p = read_motor(ser, args.pitch_id)
            pretty_print(args.yaw_id, y)
            pretty_print(args.pitch_id, p)
        if args.loop:
            while True:
                once()
                time.sleep(args.interval)
        else:
            once()
    finally:
        ser.close()

if __name__ == '__main__':
    main()
