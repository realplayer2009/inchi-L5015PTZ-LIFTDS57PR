"""PTZ云台控制器：控制YAW（方位）和PITCH（俯仰）两个轴。"""
from __future__ import annotations
import threading
import time
from typing import Optional, Dict, Any
from rs485_comm import RS485Comm

# 功能码定义



class PTZController:
    """PTZ云台控制器，管理YAW和PITCH两个电机轴"""
    
    def __init__(self, port: str = 'COM9', baudrate: int = 115200, 
                 yaw_id: int = 1, pitch_id: int = 2):
        """
        初始化PTZ控制器
        
        Args:
            port: 串口号
            baudrate: 波特率
            yaw_id: YAW电机地址（默认1）
            pitch_id: PITCH电机地址（默认2）
        """
        self.yaw_id = yaw_id
        self.pitch_id = pitch_id
        self._comm = RS485Comm(port=port, baudrate=baudrate)
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_evt = threading.Event()
        self._monitoring = False
        
        # 缓存最新状态
        self._yaw_status: Optional[Dict[str, Any]] = None
        self._pitch_status: Optional[Dict[str, Any]] = None
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
            # 读取YAW状态
            yaw_status = self._comm.read_status(self.yaw_id)
            pitch_status = self._comm.read_status(self.pitch_id)
            
            with self._status_lock:
                self._yaw_status = yaw_status
                self._pitch_status = pitch_status
            
            time.sleep(interval_s)
    
    def get_yaw_status(self) -> Optional[Dict[str, Any]]:
        """获取YAW轴最新状态（缓存）"""
        with self._status_lock:
            return self._yaw_status.copy() if self._yaw_status else None
    
    def get_pitch_status(self) -> Optional[Dict[str, Any]]:
        """获取PITCH轴最新状态（缓存）"""
        with self._status_lock:
            return self._pitch_status.copy() if self._pitch_status else None
    
    def read_yaw_angle(self) -> Optional[float]:
        """
        实时读取YAW轴角度（归一化到±180°）
        
        Returns:
            角度值（度），失败返回None
        """
        status = self._comm.read_status(self.yaw_id)
        return status['angle_deg'] if status else None
    
    def read_pitch_angle(self) -> Optional[float]:
        """
        实时读取PITCH轴角度（归一化到±180°）
        
        Returns:
            角度值（度），失败返回None
        """
        status = self._comm.read_status(self.pitch_id)
        return status['angle_deg'] if status else None
    
    def set_yaw_angle(self, target_deg: float, speed_rpm: int = 100) -> bool:
        """
        设置YAW轴目标角度
        
        Args:
            target_deg: 目标角度（度），范围±180°
            speed_rpm: 旋转速度（RPM）
            
        Returns:
            成功返回True
        """
        result = self._comm.set_target_angle(self.yaw_id, target_deg, speed_rpm)
        return result is not None and result.get('success', False)
    
    def set_pitch_angle(self, target_deg: float, speed_rpm: int = 100) -> bool:
        """
        设置PITCH轴目标角度
        
        Args:
            target_deg: 目标角度（度），范围±180°
            speed_rpm: 旋转速度（RPM）
            
        Returns:
            成功返回True
        """
        result = self._comm.set_target_angle(self.pitch_id, target_deg, speed_rpm)
        return result is not None and result.get('success', False)
    
    def set_ptz_angles(self, yaw_deg: float, pitch_deg: float, speed_rpm: int = 100) -> bool:
        """
        同时设置YAW和PITCH角度
        
        Args:
            yaw_deg: YAW目标角度（度）
            pitch_deg: PITCH目标角度（度）
            speed_rpm: 旋转速度（RPM）
            
        Returns:
            两个轴都成功返回True
        """
        yaw_ok = self.set_yaw_angle(yaw_deg, speed_rpm)
        pitch_ok = self.set_pitch_angle(pitch_deg, speed_rpm)
        return yaw_ok and pitch_ok
    
    def close(self):
        """关闭控制器，释放资源"""
        self.stop_monitoring()
        if self._comm:
            self._comm.close()


# 便捷函数：快速创建PTZ控制器
def create_ptz_controller(port: str = 'COM6', baudrate: int = 115200) -> PTZController:
    """
    创建PTZ云台控制器
    
    Args:
        port: 串口号
        baudrate: 波特率
        
    Returns:
        PTZController实例
    """
    return PTZController(port=port, baudrate=baudrate)


if __name__ == '__main__':
    # 测试代码
    import argparse
    
    parser = argparse.ArgumentParser(description='PTZ云台控制器测试')
    parser.add_argument('--port', default='COM6', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    args = parser.parse_args()
    
    # 创建控制器
    ptz = create_ptz_controller(port=args.port, baudrate=args.baud)
    
    if not ptz.available:
        print(f"无法打开串口 {args.port}")
        exit(1)
    
    print(f"已连接到 {args.port}")
    print("正在读取云台状态...")
    
    # 读取当前角度
    yaw_angle = ptz.read_yaw_angle()
    pitch_angle = ptz.read_pitch_angle()
    
    print(f"YAW角度: {yaw_angle:+.2f}°" if yaw_angle is not None else "YAW: 读取失败")
    print(f"PITCH角度: {pitch_angle:+.2f}°" if pitch_angle is not None else "PITCH: 读取失败")
    
    # 测试设置角度（可选）
    test_control = input("\n是否测试角度控制? (y/n): ").strip().lower()
    if test_control == 'y':
        yaw_target = float(input("输入YAW目标角度 (度): "))
        pitch_target = float(input("输入PITCH目标角度 (度): "))
        
        print(f"\n设置云台到 YAW={yaw_target:+.1f}°, PITCH={pitch_target:+.1f}°...")
        if ptz.set_ptz_angles(yaw_target, pitch_target):
            print("✓ 设置成功")
        else:
            print("✗ 设置失败")
    
    ptz.close()
    print("\n已关闭连接")
