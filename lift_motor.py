"""升降电机控制器：控制03地址的升降电机。"""
from __future__ import annotations
import threading
import time
from typing import Optional, Dict, Any
from rs485_comm import RS485Comm




class LiftMotorController:
    """升降电机控制器"""
    
    def __init__(self, port: str = 'COM6', baudrate: int = 115200, motor_id: int = 3):
        """
        初始化升降电机控制器
        
        Args:
            port: 串口号
            baudrate: 波特率
            motor_id: 电机地址（默认3）
        """
        self.motor_id = motor_id
        self._comm = RS485Comm(port=port, baudrate=baudrate)
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._monitoring = False
        
        # 缓存最新状态
        self._motor_status: Optional[Dict[str, Any]] = None
        self._status_lock = threading.Lock()
    
    @property
    def available(self) -> bool:
        """串口是否可用"""
        return self._comm.available
    
    def start_monitoring(self, interval_ms: int = 500):
        """
        启动后台监控线程，定期读取电机状态
        
        Args:
            interval_ms: 轮询间隔（毫秒）
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_evt.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_loop, 
            args=(interval_ms / 1000.0,),
            daemon=True
        )
        self._poll_thread.start()
    
    def stop_monitoring(self):
        """停止后台监控线程"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_evt.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None
    
    def _poll_loop(self, interval_s: float):
        """轮询循环（在后台线程中运行）"""
        while not self._stop_evt.is_set():
            # 读取电机状态
            motor_status = self._comm.read_status(self.motor_id)
            
            with self._status_lock:
                self._motor_status = motor_status
            
            time.sleep(interval_s)
    
    def get_status(self) -> Optional[Dict[str, Any]]:
        """获取电机最新状态（缓存）"""
        with self._status_lock:
            return self._motor_status.copy() if self._motor_status else None
    
    def read_position(self) -> Optional[float]:
        """
        实时读取电机位置角度（归一化到±180°）
        
        Returns:
            角度值（度），失败返回None
        """
        status = self._comm.read_status(self.motor_id)
        return status['angle_deg'] if status else None
    
    def read_raw_position(self) -> Optional[float]:
        """
        实时读取电机原始位置角度（0-360°）
        
        Returns:
            角度值（度），失败返回None
        """
        status = self._comm.read_status(self.motor_id)
        return status['angle_0_360'] if status else None
    
    def set_position(self, target_deg: float, speed_rpm: int = 100) -> bool:
        """
        设置电机目标位置
        
        Args:
            target_deg: 目标角度（度），范围±180°
            speed_rpm: 旋转速度（RPM）
            
        Returns:
            成功返回True
        """
        result = self._comm.set_target_angle(self.motor_id, target_deg, speed_rpm)
        return result is not None and result.get('success', False)
    
    def move_up(self, angle_deg: float = 10.0, speed_rpm: int = 100) -> bool:
        """
        向上移动指定角度
        
        Args:
            angle_deg: 移动角度（度），正数表示向上
            speed_rpm: 旋转速度（RPM）
            
        Returns:
            成功返回True
        """
        current_pos = self.read_position()
        if current_pos is None:
            return False
        
        target_pos = current_pos + abs(angle_deg)
        return self.set_position(target_pos, speed_rpm)
    
    def move_down(self, angle_deg: float = 10.0, speed_rpm: int = 100) -> bool:
        """
        向下移动指定角度
        
        Args:
            angle_deg: 移动角度（度），正数表示向下
            speed_rpm: 旋转速度（RPM）
            
        Returns:
            成功返回True
        """
        current_pos = self.read_position()
        if current_pos is None:
            return False
        
        target_pos = current_pos - abs(angle_deg)
        return self.set_position(target_pos, speed_rpm)
    
    def stop(self) -> bool:
        """
        停止电机运动（设置为当前位置）
        
        Returns:
            成功返回True
        """
        current_pos = self.read_position()
        if current_pos is None:
            return False
        
        return self.set_position(current_pos, speed_rpm=0)
    
    def close(self):
        """关闭控制器，释放资源"""
        self.stop_monitoring()
        if self._comm:
            self._comm.close()


# 便捷函数：快速创建升降电机控制器
def create_lift_controller(port: str = 'COM6', baudrate: int = 115200, 
                          motor_id: int = 3) -> LiftMotorController:
    """
    创建升降电机控制器
    
    Args:
        port: 串口号
        baudrate: 波特率
        motor_id: 电机地址（默认3）
        
    Returns:
        LiftMotorController实例
    """
    return LiftMotorController(port=port, baudrate=baudrate, motor_id=motor_id)


if __name__ == '__main__':
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description='升降电机控制器测试')
    parser.add_argument('--port', default='COM6', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    parser.add_argument('--id', type=int, default=3, help='电机地址')
    args = parser.parse_args()
    
    # 创建控制器
    lift = create_lift_controller(port=args.port, baudrate=args.baud, motor_id=args.id)
    
    if not lift.available:
        print(f"无法打开串口 {args.port}")
        exit(1)
    
    print(f"已连接到 {args.port}，电机地址: {args.id}")
    print("正在读取电机状态...")
    
    # 读取当前位置
    position = lift.read_position()
    raw_position = lift.read_raw_position()
    
    if position is not None:
        print(f"归一化位置: {position:+.2f}°")
        print(f"原始位置: {raw_position:.2f}° (0-360)")
    else:
        print("位置读取失败")
    
    # 测试控制（可选）
    test_control = input("\n是否测试位置控制? (y/n): ").strip().lower()
    if test_control == 'y':
        while True:
            print("\n操作选项:")
            print("1. 设置目标位置")
            print("2. 向上移动")
            print("3. 向下移动")
            print("4. 停止")
            print("5. 退出")
            
            choice = input("选择操作 (1-5): ").strip()
            
            if choice == '1':
                target = float(input("输入目标位置 (度): "))
                speed = int(input("输入速度 (RPM, 默认100): ") or "100")
                if lift.set_position(target, speed):
                    print(f"✓ 已设置目标位置: {target:+.1f}°")
                else:
                    print("✗ 设置失败")
            
            elif choice == '2':
                angle = float(input("向上移动角度 (度, 默认10): ") or "10")
                speed = int(input("输入速度 (RPM, 默认100): ") or "100")
                if lift.move_up(angle, speed):
                    print(f"✓ 向上移动 {angle:.1f}°")
                else:
                    print("✗ 移动失败")
            
            elif choice == '3':
                angle = float(input("向下移动角度 (度, 默认10): ") or "10")
                speed = int(input("输入速度 (RPM, 默认100): ") or "100")
                if lift.move_down(angle, speed):
                    print(f"✓ 向下移动 {angle:.1f}°")
                else:
                    print("✗ 移动失败")
            
            elif choice == '4':
                if lift.stop():
                    print("✓ 电机已停止")
                else:
                    print("✗ 停止失败")
            
            elif choice == '5':
                break
            
            # 读取更新后的位置
            time.sleep(0.5)
            position = lift.read_position()
            if position is not None:
                print(f"当前位置: {position:+.2f}°")
    
    lift.close()
    print("\n已关闭连接")
