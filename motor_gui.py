"""Qt界面显示YAW和PITCH电机角度实时数据。

依赖:
    pip install PyQt5

运行:
    python motor_gui.py --port COM6
"""
from __future__ import annotations
import sys
import argparse
from typing import Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QGroupBox, QGridLayout
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from rs485_comm import RS485Comm


class MotorMonitorGUI(QMainWindow):
    def __init__(self, port: str, baudrate: int = 115200):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.comm: Optional[RS485Comm] = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        
        self.init_ui()
        self.connect_motor()
        
    def init_ui(self):
        self.setWindowTitle('双轴电机监控')
        self.setGeometry(100, 100, 600, 400)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 连接状态
        status_layout = QHBoxLayout()
        self.status_label = QLabel(f'串口: {self.port}')
        self.status_label.setStyleSheet('color: gray; font-size: 12px;')
        self.conn_indicator = QLabel('●')
        self.conn_indicator.setStyleSheet('color: red; font-size: 20px;')
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.conn_indicator)
        status_layout.addStretch()
        main_layout.addLayout(status_layout)
        
        # YAW 电机组
        yaw_group = self.create_motor_group('YAW (ID=1)')
        self.yaw_angle_label = yaw_group['angle']
        self.yaw_raw_label = yaw_group['raw']
        self.yaw_original_label = yaw_group['original']
        self.yaw_status_label = yaw_group['status']
        main_layout.addWidget(yaw_group['widget'])
        
        # PITCH 电机组
        pitch_group = self.create_motor_group('PITCH (ID=2)')
        self.pitch_angle_label = pitch_group['angle']
        self.pitch_raw_label = pitch_group['raw']
        self.pitch_original_label = pitch_group['original']
        self.pitch_status_label = pitch_group['status']
        main_layout.addWidget(pitch_group['widget'])
        
        # 控制按钮
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton('开始监控')
        self.start_btn.clicked.connect(self.start_monitoring)
        self.stop_btn = QPushButton('停止监控')
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        main_layout.addStretch()
        
    def create_motor_group(self, title: str) -> dict:
        """创建电机数据显示组"""
        group = QGroupBox(title)
        layout = QGridLayout()
        
        # 归一化角度 (-180~+180)
        angle_title = QLabel('归一化角度:')
        angle_title.setStyleSheet('font-weight: bold;')
        angle_value = QLabel('--')
        angle_value.setFont(QFont('Arial', 24, QFont.Bold))
        angle_value.setStyleSheet('color: #2196F3;')
        angle_unit = QLabel('°')
        angle_unit.setFont(QFont('Arial', 18))
        
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(angle_value)
        angle_layout.addWidget(angle_unit)
        angle_layout.addStretch()
        
        layout.addWidget(angle_title, 0, 0)
        layout.addLayout(angle_layout, 0, 1)
        
        # 原始角度 (0~360)
        original_label = QLabel('原始角度:')
        original_value = QLabel('--')
        layout.addWidget(original_label, 1, 0)
        layout.addWidget(original_value, 1, 1)
        
        # 原始值
        raw_label = QLabel('原始数值:')
        raw_value = QLabel('--')
        layout.addWidget(raw_label, 2, 0)
        layout.addWidget(raw_value, 2, 1)
        
        # 状态
        status_label = QLabel('状态:')
        status_value = QLabel('未连接')
        status_value.setStyleSheet('color: gray;')
        layout.addWidget(status_label, 3, 0)
        layout.addWidget(status_value, 3, 1)
        
        group.setLayout(layout)
        
        return {
            'widget': group,
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
                self.conn_indicator.setStyleSheet('color: green; font-size: 20px;')
                self.status_label.setText(f'串口: {self.port} (已连接)')
            else:
                self.conn_indicator.setStyleSheet('color: red; font-size: 20px;')
                self.status_label.setText(f'串口: {self.port} (连接失败)')
        except Exception as e:
            self.conn_indicator.setStyleSheet('color: red; font-size: 20px;')
            self.status_label.setText(f'错误: {str(e)}')
    
    def start_monitoring(self):
        """开始监控"""
        if self.comm and self.comm.available:
            self.timer.start(500)  # 500ms 更新一次
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.yaw_status_label.setText('正在读取...')
            self.yaw_status_label.setStyleSheet('color: orange;')
            self.pitch_status_label.setText('正在读取...')
            self.pitch_status_label.setStyleSheet('color: orange;')
    
    def stop_monitoring(self):
        """停止监控"""
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.yaw_status_label.setText('已停止')
        self.yaw_status_label.setStyleSheet('color: gray;')
        self.pitch_status_label.setText('已停止')
        self.pitch_status_label.setStyleSheet('color: gray;')
    
    def update_data(self):
        """更新电机数据"""
        if not self.comm or not self.comm.available:
            return
        
        # 读取 YAW
        yaw_status = self.comm.read_status(1)
        if yaw_status:
            angle_sign = '+' if yaw_status['angle_deg'] >= 0 else ''
            self.yaw_angle_label.setText(f"{angle_sign}{yaw_status['angle_deg']:.2f}")
            self.yaw_original_label.setText(f"{yaw_status['angle_0_360']:.2f}°")
            self.yaw_raw_label.setText(f"{yaw_status['angle_raw']}")
            self.yaw_status_label.setText('正常')
            self.yaw_status_label.setStyleSheet('color: green;')
        else:
            self.yaw_status_label.setText('读取失败')
            self.yaw_status_label.setStyleSheet('color: red;')
        
        # 读取 PITCH
        pitch_status = self.comm.read_status(2)
        if pitch_status:
            angle_sign = '+' if pitch_status['angle_deg'] >= 0 else ''
            self.pitch_angle_label.setText(f"{angle_sign}{pitch_status['angle_deg']:.2f}")
            self.pitch_original_label.setText(f"{pitch_status['angle_0_360']:.2f}°")
            self.pitch_raw_label.setText(f"{pitch_status['angle_raw']}")
            self.pitch_status_label.setText('正常')
            self.pitch_status_label.setStyleSheet('color: green;')
        else:
            self.pitch_status_label.setText('读取失败')
            self.pitch_status_label.setStyleSheet('color: red;')
    
    def closeEvent(self, event):
        """关闭窗口时清理资源"""
        self.timer.stop()
        if self.comm:
            self.comm.close()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description='电机监控GUI')
    parser.add_argument('--port', default='COM6', help='串口号')
    parser.add_argument('--baud', type=int, default=115200, help='波特率')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    window = MotorMonitorGUI(port=args.port, baudrate=args.baud)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
