"""详细显示0xA4命令的发送帧"""
from rs485_comm import RS485Comm

def show_command_frame(motor_id, target_deg, speed_rpm):
    """显示命令帧的详细构造"""
    print(f"\n=== 目标角度: {target_deg:+.1f}°, 速度: {speed_rpm} RPM ===")
    
    # 归一化角度
    normalized = target_deg
    if normalized > 180.0:
        normalized -= 360.0
    elif normalized < -180.0:
        normalized += 360.0
    
    # 转换为LSB
    angle_control = int(normalized * 100)
    print(f"归一化角度: {normalized:+.1f}°")
    print(f"控制值: {angle_control} LSB (0x{angle_control & 0xFFFFFFFF:08X})")
    
    # 构造字节
    speed_low = speed_rpm & 0xFF
    speed_high = (speed_rpm >> 8) & 0xFF
    angle_bytes = angle_control.to_bytes(4, byteorder='little', signed=True)
    
    print(f"\n命令数据区 (8字节):")
    print(f"  Byte0: 0xA4 (命令码)")
    print(f"  Byte1: 0x00 (保留)")
    print(f"  Byte2: 0x{speed_low:02X} (速度低字节 = {speed_low})")
    print(f"  Byte3: 0x{speed_high:02X} (速度高字节 = {speed_high})")
    print(f"  Byte4: 0x{angle_bytes[0]:02X} (位置字节0)")
    print(f"  Byte5: 0x{angle_bytes[1]:02X} (位置字节1)")
    print(f"  Byte6: 0x{angle_bytes[2]:02X} (位置字节2)")
    print(f"  Byte7: 0x{angle_bytes[3]:02X} (位置字节3)")
    
    payload = bytes([
        0x00,
        speed_low,
        speed_high,
        angle_bytes[0],
        angle_bytes[1],
        angle_bytes[2],
        angle_bytes[3]
    ])
    
    data_area = bytes([0xA4]) + payload
    print(f"\n完整数据区: {' '.join(f'{b:02X}' for b in data_area)}")

# 测试示例
test_cases = [
    (10, 100),
    (-10, 100),
    (45, 100),
    (-45, 100),
    (350, 100),  # 应该归一化为-10°
]

for angle, speed in test_cases:
    show_command_frame(1, angle, speed)
