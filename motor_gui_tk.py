"""Tkinter界面显示YAW和PITCH电机角度实时数据。

Tkinter是Python内置GUI库，无需额外安装。

运行:
    python motor_gui_tk.py --port COM6
"""
from __future__ import annotations
import sys
import argparse
import tkinter as tk
from tkinter import ttk
from typing import Optional
from rs485_comm import RS485Comm


class MotorMonitorApp:
    def __init__(self, root: tk.Tk, port: str, baudrate: int = 115200):
        self.root = root
        self.port = port
        self.baudrate = baudrate
        self.comm: Optional[RS485Comm] = None
        self.monitoring = False
        
        self.root.title('双轴电机监控')
        self.root.geometry('550x450')
        self.root.resizable(False, False)
        
        self.init_ui()
        self.connect_motor()
        
    def init_ui(self):
        """初始化UI"""
        # 标题
        title_frame = tk.Frame(self.root, bg='#2196F3', height=50)
        title_frame.pack(fill=tk.X)
        title_label = tk.Label(
            title_frame, 
            text='双轴电机实时监控', 
            font=('Arial', 16, 'bold'),
            bg='#2196F3',
            fg='white'
        )
        title_label.pack(pady=10)
        
        # 连接状态栏
        status_frame = tk.Frame(self.root, bg='#f5f5f5', height=40)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.conn_indicator = tk.Label(
            status_frame,
            text='●',
            font=('Arial', 20),
            fg='red',
            bg='#f5f5f5'
        )
        self.conn_indicator.pack(side=tk.LEFT, padx=10)
        
        self.status_label = tk.Label(
            status_frame,
            text=f'串口: {self.port}',
            font=('Arial', 10),
            bg='#f5f5f5'
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # 主内容区
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # YAW 电机
        yaw_frame = tk.LabelFrame(content_frame, text='YAW 电机 (ID=1)', font=('Arial', 11, 'bold'))
        yaw_frame.pack(fill=tk.X, pady=5)
        self.yaw_widgets = self.create_motor_display(yaw_frame)
        
        # PITCH 电机
        pitch_frame = tk.LabelFrame(content_frame, text='PITCH 电机 (ID=2)', font=('Arial', 11, 'bold'))
        pitch_frame.pack(fill=tk.X, pady=5)
        self.pitch_widgets = self.create_motor_display(pitch_frame)
        
        # 控制按钮
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.start_btn = tk.Button(
            button_frame,
            text='开始监控',
            command=self.start_monitoring,
            font=('Arial', 11),
            bg='#4CAF50',
            fg='white',
            width=12,
            height=2
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            button_frame,
            text='停止监控',
            command=self.stop_monitoring,
            font=('Arial', 11),
            bg='#f44336',
            fg='white',
            width=12,
            height=2,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
    def create_motor_display(self, parent: tk.Frame) -> dict:
        """创建电机数据显示组件"""
        # 归一化角度（大字体显示）
        angle_frame = tk.Frame(parent)
        angle_frame.pack(pady=10)
        
        tk.Label(angle_frame, text='归一化角度:', font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        angle_value = tk.Label(
            angle_frame,
            text='--',
            font=('Arial', 28, 'bold'),
            fg='#2196F3'
        )
        angle_value.pack(side=tk.LEFT, padx=5)
        tk.Label(angle_frame, text='°', font=('Arial', 18)).pack(side=tk.LEFT)
        
        # 详细信息
        info_frame = tk.Frame(parent)
        info_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # 原始角度
        orig_frame = tk.Frame(info_frame)
        orig_frame.pack(fill=tk.X, pady=2)
        tk.Label(orig_frame, text='原始角度:', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        original_value = tk.Label(orig_frame, text='--', font=('Arial', 9, 'bold'))
        original_value.pack(side=tk.LEFT)
        
        # 原始数值
        raw_frame = tk.Frame(info_frame)
        raw_frame.pack(fill=tk.X, pady=2)
        tk.Label(raw_frame, text='原始数值:', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        raw_value = tk.Label(raw_frame, text='--', font=('Arial', 9, 'bold'))
        raw_value.pack(side=tk.LEFT)
        
        # 状态
        status_frame = tk.Frame(info_frame)
        status_frame.pack(fill=tk.X, pady=2)
        tk.Label(status_frame, text='状态:', font=('Arial', 9), width=12, anchor='w').pack(side=tk.LEFT)
        status_value = tk.Label(status_frame, text='未连接', font=('Arial', 9), fg='gray')
        status_value.pack(side=tk.LEFT)
        
        return {
            'angle': angle_value,
            'original': original_value,
            'raw': raw_value,
            'status': status_value
        }
    
    def connect_motor(self):
        """连接电机"""
        try:
            self.comm = RS485Comm(port=self.port, baudrate=self.baudrate)
            if self.comm.available:
                self.conn_indicator.config(fg='green')
                self.status_label.config(text=f'串口: {self.port} (已连接)')
            else:
                self.conn_indicator.config(fg='red')
                self.status_label.config(text=f'串口: {self.port} (连接失败)')
        except Exception as e:
            self.conn_indicator.config(fg='red')
            self.status_label.config(text=f'错误: {str(e)}')
    
    def start_monitoring(self):
        """开始监控"""
        if self.comm and self.comm.available:
            self.monitoring = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.yaw_widgets['status'].config(text='正在读取...', fg='orange')
            self.pitch_widgets['status'].config(text='正在读取...', fg='orange')
            self.update_data()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.yaw_widgets['status'].config(text='已停止', fg='gray')
        self.pitch_widgets['status'].config(text='已停止', fg='gray')
    
    def update_data(self):
        """更新电机数据"""
        if not self.monitoring or not self.comm or not self.comm.available:
            return
        
        # 读取 YAW
        yaw_status = self.comm.read_status(1)
        if yaw_status:
            angle_text = f"{yaw_status['angle_deg']:+.2f}"
            self.yaw_widgets['angle'].config(text=angle_text)
            self.yaw_widgets['original'].config(text=f"{yaw_status['angle_0_360']:.2f}°")
            self.yaw_widgets['raw'].config(text=f"{yaw_status['angle_raw']}")
            self.yaw_widgets['status'].config(text='正常', fg='green')
        else:
            self.yaw_widgets['status'].config(text='读取失败', fg='red')
        
        # 读取 PITCH
        pitch_status = self.comm.read_status(2)
        if pitch_status:
            angle_text = f"{pitch_status['angle_deg']:+.2f}"
            self.pitch_widgets['angle'].config(text=angle_text)
            self.pitch_widgets['original'].config(text=f"{pitch_status['angle_0_360']:.2f}°")
            self.pitch_widgets['raw'].config(text=f"{pitch_status['angle_raw']}")
            self.pitch_widgets['status'].config(text='正常', fg='green')
        else:
            self.pitch_widgets['status'].config(text='读取失败', fg='red')
        
        # 500ms后再次更新
        if self.monitoring:
            self.root.after(500, self.update_data)
    
    def on_close(self):
        """关闭窗口"""
        self.monitoring = False
        if self.comm:
            self.comm.close()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description='电机监控GUI (Tkinter)')
    parser.add_argument('--port', default='COM6', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    args = parser.parse_args()
    
    root = tk.Tk()
    app = MotorMonitorApp(root, port=args.port, baudrate=args.baud)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
