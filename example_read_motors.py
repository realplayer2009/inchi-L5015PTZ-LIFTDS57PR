"""使用新 RS485Comm 接口读取双轴电机状态的示例。

运行示例:
    python example_read_motors.py --port COM3
"""
from __future__ import annotations
import argparse
import time
from rs485_comm import RS485Comm

def main():
    parser = argparse.ArgumentParser(description='读取01(Yaw)与02(Pitch)电机状态')
    parser.add_argument('--port', required=True, help='串口号, 如 COM3')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--yaw-id', type=int, default=1, help='Yaw电机ID')
    parser.add_argument('--pitch-id', type=int, default=2, help='Pitch电机ID')
    parser.add_argument('--loop', action='store_true', help='循环读取（持续读取电机参数）')
    parser.add_argument('--interval', type=float, default=0.5, help='循环间隔(秒)')
    args = parser.parse_args()

    comm = RS485Comm(port=args.port, baudrate=args.baud)
    
    if not comm.available:
        print(f"错误: 无法打开串口 {args.port}")
        return

    try:
        def read_once():
            print(f"\n{'='*60}")
            # 读取 Yaw
            yaw_status = comm.read_status(args.yaw_id)
            if yaw_status:
                print(f"[YAW ID={args.yaw_id}]")
                print(f"  归一化角度: {yaw_status['angle_deg']:+.2f}° (原始: {yaw_status['angle_0_360']:.2f}°, 值: {yaw_status['angle_raw']})")
                print(f"  命令回显: {yaw_status['cmd_echo']}")
                print(f"  保留字节: {yaw_status['reserved_bytes']}")
                print(f"  原始数据: {yaw_status['raw_hex']}")
            else:
                print(f"[YAW ID={args.yaw_id}] 读取失败")

            # 读取 Pitch
            pitch_status = comm.read_status(args.pitch_id)
            if pitch_status:
                print(f"\n[PITCH ID={args.pitch_id}]")
                print(f"  归一化角度: {pitch_status['angle_deg']:+.2f}° (原始: {pitch_status['angle_0_360']:.2f}°, 值: {pitch_status['angle_raw']})")
                print(f"  命令回显: {pitch_status['cmd_echo']}")
                print(f"  保留字节: {pitch_status['reserved_bytes']}")
                print(f"  原始数据: {pitch_status['raw_hex']}")
            else:
                print(f"[PITCH ID={args.pitch_id}] 读取失败")

        if args.loop:
            print(f"开始循环读取 (间隔 {args.interval}s, Ctrl+C 退出)...")
            while True:
                read_once()
                time.sleep(args.interval)
        else:
            read_once()
    
    except KeyboardInterrupt:
        print("\n\n用户中断")
    finally:
        comm.close()
        print("串口已关闭")

if __name__ == '__main__':
    main()
