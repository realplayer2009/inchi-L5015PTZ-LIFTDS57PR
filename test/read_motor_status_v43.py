"""连续读取串口数据, 解析 V4.3 帧 (0x3E 头) 并打印指定电机 ID 状态。

用法:
  python read_motor_status_v43.py --port COM3 --ids 1 2 --loop
"""
from __future__ import annotations
import argparse
import time
import serial  # type: ignore
from proto_v43 import extract_frames, demo_decode_fields, FRAME_SIZE

def main():
    parser = argparse.ArgumentParser(description='解析 V4.3 协议伺服电机状态帧')
    parser.add_argument('--port', required=True)
    parser.add_argument('--baud', type=int, default=115200)
    parser.add_argument('--timeout', type=float, default=0.1)
    parser.add_argument('--ids', type=int, nargs='+', default=[1,2], help='关心的电机ID列表')
    parser.add_argument('--loop', action='store_true')
    parser.add_argument('--interval', type=float, default=0.2)
    parser.add_argument('--read-bytes', type=int, default=200, help='每次 read() 读取最大字节数')
    args = parser.parse_args()

    ser = serial.Serial(port=args.port, baudrate=args.baud, timeout=args.timeout)
    buf = b''
    try:
        def once():
            nonlocal buf
            chunk = ser.read(args.read_bytes)
            if chunk:
                buf += chunk
                # 防止缓冲过大
                if len(buf) > 5000:
                    buf = buf[-1000:]
            frames = extract_frames(buf)
            if frames:
                # 清理缓冲: 寻找最后一个完整帧起点
                last_start = None
                i2 = 0
                while i2 + FRAME_SIZE <= len(buf):
                    if buf[i2] == 0x3E and len(extract_frames(buf[i2:i2+FRAME_SIZE])) == 1:
                        last_start = i2
                        i2 += FRAME_SIZE
                    else:
                        i2 += 1
                if last_start is not None:
                    buf = buf[last_start + FRAME_SIZE:]
            for mid, data in frames:
                if mid in args.ids:
                    parsed = demo_decode_fields(data)
                    print(f"ID {mid}: angle={parsed.get('angle_deg')} speed={parsed.get('speed_deg_s')} temp={parsed.get('temperature_c')} raw={parsed.get('raw_hex')}" )
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
