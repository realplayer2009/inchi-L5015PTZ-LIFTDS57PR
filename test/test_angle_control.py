"""测试 0xA4 角度控制命令

演示如何使用 set_target_angle() 方法设置电机目标角度。
"""
import time
import argparse
from rs485_comm import RS485Comm

def test_single_angle(comm: RS485Comm, motor_id: int, target_deg: float, speed_rpm: int = 100):
    """测试单个角度设置"""
    print(f"\n=== 测试电机 {motor_id} 目标角度 {target_deg}° ===")
    
    # 读取当前角度
    current = comm.read_angle(motor_id)
    if current is not None:
        print(f"当前角度: {current:.2f}°")
    else:
        print("无法读取当前角度")
    
    # 设置目标角度
    print(f"发送控制命令: 目标={target_deg}°, 速度={speed_rpm}RPM")
    result = comm.set_target_angle(motor_id, target_deg, speed_rpm)
    
    if result is None:
        print("❌ 命令发送失败 (无响应)")
        return False
    
    print(f"响应: {result['cmd_echo']}")
    print(f"控制值: {result['angle_control']} (0.01°/LSB)")
    print(f"原始数据: {result['raw_hex']}")
    
    if result['success']:
        print("✓ 命令接受成功")
        return True
    else:
        print(f"❌ 命令回显不匹配 (期望 0xA4, 收到 {result['cmd_echo']})")
        return False

def test_angle_sequence(comm: RS485Comm, motor_id: int, angles: list, speed_rpm: int = 100, delay: float = 2.0):
    """测试一系列角度"""
    print(f"\n=== 角度序列测试 (电机 {motor_id}) ===")
    print(f"测试角度: {angles}")
    print(f"速度: {speed_rpm} RPM, 间隔: {delay}s\n")
    
    success_count = 0
    for angle in angles:
        if test_single_angle(comm, motor_id, angle, speed_rpm):
            success_count += 1
        
        # 等待电机运动
        print(f"等待 {delay}s 让电机运动...")
        time.sleep(delay)
        
        # 读取实际角度
        actual = comm.read_angle(motor_id)
        if actual is not None:
            error = abs(actual - angle)
            print(f"实际角度: {actual:.2f}° (误差: {error:.2f}°)")
        print("-" * 50)
    
    print(f"\n总结: {success_count}/{len(angles)} 命令成功发送")

def main():
    parser = argparse.ArgumentParser(description='测试电机角度控制 (0xA4命令)')
    parser.add_argument('--port', default='COM6', help='串口号 (默认: COM6)')
    parser.add_argument('--motor', type=int, default=1, choices=[1, 2], help='电机ID (1=YAW, 2=PITCH)')
    parser.add_argument('--angle', type=float, help='目标角度 (-180~+180°)')
    parser.add_argument('--speed', type=int, default=100, help='速度限制 RPM (默认: 100)')
    parser.add_argument('--test-sequence', action='store_true', help='运行角度序列测试')
    parser.add_argument('--delay', type=float, default=2.0, help='序列测试间隔秒数 (默认: 2.0)')
    
    args = parser.parse_args()
    
    # 初始化通信
    print(f"打开串口: {args.port}")
    comm = RS485Comm(port=args.port, baudrate=115200, timeout=0.5)
    
    if not comm.available:
        print(f"❌ 无法打开串口 {args.port}")
        return
    
    print("✓ 串口连接成功\n")
    
    try:
        if args.test_sequence:
            # 角度序列测试
            test_angles = [0.0, 45.0, 90.0, -45.0, -90.0, 0.0]
            test_angle_sequence(comm, args.motor, test_angles, args.speed, args.delay)
        elif args.angle is not None:
            # 单个角度测试
            test_single_angle(comm, args.motor, args.angle, args.speed)
        else:
            # 默认：简单测试
            print("=== 简单测试模式 ===")
            print("测试 0°, +45°, -45° 角度")
            for angle in [0.0, 45.0, -45.0]:
                test_single_angle(comm, args.motor, angle, args.speed)
                time.sleep(1.0)
    
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
    finally:
        comm.close()
        print("\n串口已关闭")

if __name__ == '__main__':
    main()
