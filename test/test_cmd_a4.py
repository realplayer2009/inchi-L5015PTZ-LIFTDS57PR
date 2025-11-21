"""测试0xA4命令读取电机状态。

运行示例:
    python test_cmd_a4.py --port COM6
    python test_cmd_a4.py --port COM6 --motor-id 1
"""
from __future__ import annotations
import argparse
import sys
from rs485_comm import RS485Comm


def main():
    parser = argparse.ArgumentParser(description='测试0xA4命令')
    parser.add_argument('--port', required=True, help='串口号, 如 COM6')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--motor-id', type=int, default=1, help='电机ID (1=Yaw, 2=Pitch)')
    args = parser.parse_args()

    # 初始化通信
    comm = RS485Comm(port=args.port, baudrate=args.baud)
    
    if not comm.available:
        print(f"错误: 无法打开串口 {args.port}")
        sys.exit(1)

    print(f"已连接到串口: {args.port}")
    print(f"发送0xA4命令到电机ID={args.motor_id}\n")
    
    # 发送0xA4命令
    result = comm.read_status_a4(args.motor_id)
    
    if result:
        print("✓ 读取成功!")
        print(f"命令回显: {result['cmd_echo']}")
        print(f"数据字节: {result['data_bytes']}")
        print(f"原始帧(十六进制): {result['raw_hex']}")
    else:
        print("✗ 读取失败 - 无响应或CRC错误")
    
    comm.close()
    print("\n串口已关闭")


if __name__ == '__main__':
    main()
