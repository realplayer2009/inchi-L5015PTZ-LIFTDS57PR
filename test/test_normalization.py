"""测试角度归一化逻辑"""

# 测试不同角度值的归一化
test_angles = [0, 10, 90, 180, 270, 350, 359.99]

print("原始角度 -> 归一化角度")
print("-" * 30)

for angle_0_360 in test_angles:
    # 当前代码的归一化逻辑
    angle_deg = angle_0_360 - 360.0 if angle_0_360 > 180.0 else angle_0_360
    print(f"{angle_0_360:7.2f}° -> {angle_deg:+7.2f}°")

print("\n特殊测试:")
print(f"350° -> {350 - 360 if 350 > 180 else 350:+.2f}° (期望: -10°)")
print(f"170° -> {170 - 360 if 170 > 180 else 170:+.2f}° (期望: +170°)")
print(f"190° -> {190 - 360 if 190 > 180 else 190:+.2f}° (期望: -170°)")
