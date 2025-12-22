#!/usr/bin/env python3
"""
Flask API Server for PTZ Motor Control
监听地址: 127.0.0.1:50278
功能: 接收JSON格式的旋转/俯仰坐标设置，返回2台电机的角度和温度
"""

import sys
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify
from ptz_controller import PTZController
import serial

# Flask应用初始化
app = Flask(__name__)

# 日志目录配置
LOG_DIR = '/var/log/inchiptz'
OPERATION_LOG = f'{LOG_DIR}/operation.log'
ERROR_LOG = f'{LOG_DIR}/error.log'

# 角度限制配置
YAW_MIN = -85.0
YAW_MAX = 85.0
PITCH_MIN = -10.0
PITCH_MAX = 85.0

# 全局PTZ控制器
ptz_controller = None
serial_error_flag = False


def setup_logging():
    """配置日志记录器，分离操作日志和错误日志，限制1M大小"""
    # 创建日志格式（带时间戳）
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # 配置操作日志（INFO级别）
    operation_handler = RotatingFileHandler(
        OPERATION_LOG,
        maxBytes=1048576,  # 1MB
        backupCount=3,
        encoding='utf-8'
    )
    operation_handler.setLevel(logging.INFO)
    operation_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 配置错误日志（ERROR级别）
    error_handler = RotatingFileHandler(
        ERROR_LOG,
        maxBytes=1048576,  # 1MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # 配置根日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(operation_handler)
    logger.addHandler(error_handler)
    
    # 同时输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)


def validate_angle(yaw, pitch):
    """
    验证角度范围
    :param yaw: 旋转角度
    :param pitch: 俯仰角度
    :return: (is_valid, error_message)
    """
    if not isinstance(yaw, (int, float)):
        return False, "旋转角度必须是数字"
    if not isinstance(pitch, (int, float)):
        return False, "俯仰角度必须是数字"
    
    if yaw < YAW_MIN or yaw > YAW_MAX:
        return False, f"旋转角度超出范围，允许范围：{YAW_MIN}° 到 {YAW_MAX}°"
    
    if pitch < PITCH_MIN or pitch > PITCH_MAX:
        return False, f"俯仰角度超出范围，允许范围：{PITCH_MIN}° 到 {PITCH_MAX}°"
    
    return True, None


@app.route('/set_position', methods=['POST'])
def set_position():
    """
    设置PTZ位置
    接收JSON: {"yaw": 45.2, "pitch": -12.5}
    返回JSON: {"success": true} 或 {"success": false, "error": "错误信息", "code": 错误码}
    """
    global serial_error_flag
    
    try:
        # 检查串口状态
        if serial_error_flag:
            error_msg = "串口通信失败，请检查设备连接"
            logging.error(f"设置位置失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 500}), 500
        
        # 解析JSON数据
        if not request.is_json:
            error_msg = "请求必须是JSON格式"
            logging.error(f"设置位置失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 400}), 400
        
        data = request.get_json()
        
        # 检查必需参数
        if 'yaw' not in data or 'pitch' not in data:
            error_msg = "缺少必需参数：yaw 和 pitch"
            logging.error(f"设置位置失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 400}), 400
        
        yaw = data['yaw']
        pitch = data['pitch']
        
        # 验证角度范围
        is_valid, error_msg = validate_angle(yaw, pitch)
        if not is_valid:
            logging.error(f"设置位置失败: {error_msg}, yaw={yaw}, pitch={pitch}")
            return jsonify({"success": False, "error": error_msg, "code": 400}), 400
        
        # 设置电机角度
        yaw_result = ptz_controller.set_yaw_angle(yaw)
        pitch_result = ptz_controller.set_pitch_angle(pitch)
        
        if not yaw_result or not pitch_result:
            error_msg = "电机控制命令发送失败"
            logging.error(f"设置位置失败: {error_msg}, yaw={yaw}, pitch={pitch}")
            return jsonify({"success": False, "error": error_msg, "code": 500}), 500
        
        logging.info(f"设置位置成功: yaw={yaw}°, pitch={pitch}°")
        return jsonify({"success": True})
    
    except serial.SerialException as e:
        serial_error_flag = True
        error_msg = f"串口通信异常: {str(e)}"
        logging.error(f"设置位置失败: {error_msg}")
        return jsonify({"success": False, "error": "串口通信失败，请检查设备连接", "code": 500}), 500
    
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        logging.error(f"设置位置失败: {error_msg}")
        return jsonify({"success": False, "error": "服务器内部错误", "code": 500}), 500


@app.route('/get_status', methods=['GET'])
def get_status():
    """
    获取PTZ状态
    返回JSON: {
        "success": true,
        "yaw_angle": 45.2,
        "pitch_angle": -12.5,
        "yaw_temperature": 38,
        "pitch_temperature": 40
    }
    """
    global serial_error_flag
    
    try:
        # 检查串口状态
        if serial_error_flag:
            error_msg = "串口通信失败，请检查设备连接"
            logging.error(f"获取状态失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 500}), 500
        
        # 从缓存获取状态（由500ms轮询线程更新）
        yaw_status = ptz_controller.get_yaw_status()
        pitch_status = ptz_controller.get_pitch_status()
        
        if yaw_status is None or pitch_status is None:
            error_msg = "无法读取电机状态数据"
            logging.error(f"获取状态失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 500}), 500
        
        # 构造响应数据
        response = {
            "success": True,
            "yaw_angle": yaw_status.get('angle_deg', 0.0),
            "pitch_angle": pitch_status.get('angle_deg', 0.0),
            "yaw_temperature": yaw_status.get('temperature', 0),
            "pitch_temperature": pitch_status.get('temperature', 0)
        }
        
        logging.info(f"获取状态成功: yaw={response['yaw_angle']}°, pitch={response['pitch_angle']}°, "
                    f"yaw_temp={response['yaw_temperature']}℃, pitch_temp={response['pitch_temperature']}℃")
        
        return jsonify(response)
    
    except serial.SerialException as e:
        serial_error_flag = True
        error_msg = f"串口通信异常: {str(e)}"
        logging.error(f"获取状态失败: {error_msg}")
        return jsonify({"success": False, "error": "串口通信失败，请检查设备连接", "code": 500}), 500
    
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        logging.error(f"获取状态失败: {error_msg}")
        return jsonify({"success": False, "error": "服务器内部错误", "code": 500}), 500


@app.route('/shutdown_motors', methods=['POST'])
def shutdown_motors():
    """
    关闭所有电机
    接收JSON: {} (空对象)
    返回JSON: {"success": true} 或 {"success": false, "error": "错误信息", "code": 错误码}
    """
    global serial_error_flag
    
    try:
        # 检查串口状态
        if serial_error_flag:
            error_msg = "串口通信失败，请检查设备连接"
            logging.error(f"关闭电机失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 500}), 500
        
        # 发送关闭电机指令
        if ptz_controller.close_motors():
            logging.info("关闭电机成功")
            return jsonify({"success": True})
        else:
            error_msg = "电机关闭命令发送失败"
            logging.error(f"关闭电机失败: {error_msg}")
            return jsonify({"success": False, "error": error_msg, "code": 500}), 500
    
    except serial.SerialException as e:
        serial_error_flag = True
        error_msg = f"串口通信异常: {str(e)}"
        logging.error(f"关闭电机失败: {error_msg}")
        return jsonify({"success": False, "error": "串口通信失败，请检查设备连接", "code": 500}), 500
    
    except Exception as e:
        error_msg = f"未知错误: {str(e)}"
        logging.error(f"关闭电机失败: {error_msg}")
        return jsonify({"success": False, "error": "服务器内部错误", "code": 500}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """
    健康检查接口
    返回JSON: {"healthy": true, "serial_connected": true}
    """
    return jsonify({
        "healthy": True,
        "serial_connected": not serial_error_flag
    })


def init_ptz_controller(port='/dev/ttyUSB0', yaw_id=1, pitch_id=2):
    """
    初始化PTZ控制器并启动监控线程
    :param port: 串口设备路径
    :param yaw_id: YAW电机ID
    :param pitch_id: PITCH电机ID
    """
    global ptz_controller, serial_error_flag
    
    try:
        logging.info(f"初始化PTZ控制器: port={port}, yaw_id={yaw_id}, pitch_id={pitch_id}")
        ptz_controller = PTZController(port=port, yaw_id=yaw_id, pitch_id=pitch_id)
        
        # 启动500ms轮询监控线程
        ptz_controller.start_monitoring(interval_ms=500)
        
        # 等待首次轮询完成
        time.sleep(1.0)
        
        serial_error_flag = False
        logging.info("PTZ控制器初始化成功，监控线程已启动（500ms轮询间隔）")
        
    except Exception as e:
        serial_error_flag = True
        logging.error(f"PTZ控制器初始化失败: {str(e)}")
        raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PTZ Motor Control API Server')
    parser.add_argument('--port', type=str, default='/dev/ttyUSB0',
                       help='串口设备路径 (默认: /dev/ttyUSB0)')
    parser.add_argument('--yaw-id', type=int, default=1,
                       help='YAW电机ID (默认: 1)')
    parser.add_argument('--pitch-id', type=int, default=2,
                       help='PITCH电机ID (默认: 2)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                       help='监听地址 (默认: 127.0.0.1)')
    parser.add_argument('--port-num', type=int, default=50278,
                       help='监听端口 (默认: 50278)')
    
    args = parser.parse_args()
    
    # 配置日志
    try:
        setup_logging()
    except Exception as e:
        print(f"警告: 无法配置日志到 {LOG_DIR}，使用控制台输出: {e}")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 初始化PTZ控制器
    try:
        init_ptz_controller(port=args.port, yaw_id=args.yaw_id, pitch_id=args.pitch_id)
    except Exception as e:
        logging.error(f"无法启动API服务器: {str(e)}")
        sys.exit(1)
    
    # 启动Flask服务器
    logging.info(f"启动Flask API服务器: http://{args.host}:{args.port_num}")
    logging.info(f"API端点:")
    logging.info(f"  POST /set_position   - 设置PTZ位置 (JSON: {{\"yaw\": float, \"pitch\": float}})")
    logging.info(f"  GET  /get_status     - 获取PTZ状态 (返回角度和温度)")
    logging.info(f"  POST /shutdown_motors - 关闭所有电机 (JSON: {{}})")
    logging.info(f"  GET  /health         - 健康检查")
    logging.info(f"角度限制: YAW={YAW_MIN}°~{YAW_MAX}°, PITCH={PITCH_MIN}°~{PITCH_MAX}°")
    
    try:
        app.run(host=args.host, port=args.port_num, debug=False, threaded=True)
    except KeyboardInterrupt:
        logging.info("收到退出信号，正在关闭...")
    finally:
        if ptz_controller:
            # 发送关闭电机指令
            try:
                ptz_controller.close_motors()
                logging.info("电机关闭指令已发送")
            except:
                logging.warning("发送电机关闭指令时出错")
            
            ptz_controller.stop_monitoring()
            ptz_controller.close()
            logging.info("PTZ控制器已关闭")


if __name__ == '__main__':
    main()
