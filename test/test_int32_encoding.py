"""测试位置控制编码"""

# 测试不同角度的int32编码
test_angles = [10, -10, 45, -45, 90, -90, 180, -180]

print("角度 -> LSB -> 字节序列 (Little-Endian)")
print("-" * 60)

for angle in test_angles:
    lsb = int(angle * 100)
    angle_bytes = lsb.to_bytes(4, byteorder='little', signed=True)
    hex_str = " ".join(f"{b:02X}" for b in angle_bytes)
    print(f"{angle:+6.1f}° -> {lsb:+6d} LSB -> {hex_str}")

print("\n特殊测试:")
print(f" 10° = 1000 LSB = 0x{1000:08X}")
lsb_10 = 1000
b = lsb_10.to_bytes(4, 'little', signed=True)
print(f"  编码: {' '.join(f'{x:02X}' for x in b)}")
print(f"  期望: E8 03 00 00")
print(f"  匹配: {'✓' if b == bytes([0xE8, 0x03, 0x00, 0x00]) else '✗'}")
