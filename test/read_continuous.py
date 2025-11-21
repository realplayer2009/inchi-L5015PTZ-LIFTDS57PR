"""持续读取电机参数命令行工具（简化版）。

功能：
- 连续读取YAW和PITCH电机角度
- 实时显示归一化角度(-180~+180°)
- 按Ctrl+C退出

运行示例:
    python read_continuous.py --port COM6
    python read_continuous.py --port COM6 --interval 0.5
    python read_continuous.py --port COM6 --yaw-id 1 --pitch-id 2
"""
from __future__ import annotations
import argparse
import time
import sys
from rs485_comm import RS485Comm


def main():
    parser = argparse.ArgumentParser(description='持续读取电机参数')
    parser.add_argument('--port', required=True, help='串口号, 如 COM6')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--yaw-id', type=int, default=1, help='Yaw电机ID')
    parser.add_argument('--pitch-id', type=int, default=2, help='Pitch电机ID')
    parser.add_argument('--interval', type=float, default=0.5, help='读取间隔(秒)')
    args = parser.parse_args()

    # 初始化通信
    comm = RS485Comm(port=args.port, baudrate=args.baud)
    
    if not comm.available:
        print(f"错误: 无法打开串口 {args.port}")
        sys.exit(1)

    print(f"已连接到串口: {args.port}")
    print(f"读取间隔: {args.interval}s")
    print(f"按 Ctrl+C 退出\n")
    print(f"{'时间':<12} | {'YAW角度':<12} | {'PITCH角度':<12} | 状态")
    print("-" * 65)

    try:
        count = 0
        while True:
            count += 1
            timestamp = time.strftime("%H:%M:%S")
            
            # 读取YAW
            yaw_angle = comm.read_angle(args.yaw_id)
            yaw_str = f"{yaw_angle:+7.2f}°" if yaw_angle is not None else "失败"
            
            # 读取PITCH
            pitch_angle = comm.read_angle(args.pitch_id)
            pitch_str = f"{pitch_angle:+7.2f}°" if pitch_angle is not None else "失败"
            
            # 状态
            status = "OK" if (yaw_angle is not None and pitch_angle is not None) else "ERROR"
            
            # 输出
            print(f"{timestamp:<12} | {yaw_str:<12} | {pitch_str:<12} | {status}")
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\n\n用户中断，正在退出...")
    finally:
        comm.close()
        print(f"串口已关闭。共读取 {count} 次。")


if __name__ == '__main__':
    main()
