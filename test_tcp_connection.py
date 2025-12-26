#!/usr/bin/env python3
"""测试 TCP 连接到 192.168.25.78:502"""

import socket
import time

def test_tcp_connection():
    host = "192.168.25.78"
    port = 502
    
    print(f"正在测试 TCP 连接: {host}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        
        print(f"尝试连接...")
        start_time = time.time()
        sock.connect((host, port))
        elapsed = time.time() - start_time
        
        print(f"✓ 连接成功！耗时: {elapsed:.3f}秒")
        print(f"  本地地址: {sock.getsockname()}")
        print(f"  远程地址: {sock.getpeername()}")
        
        sock.close()
        return True
        
    except socket.timeout:
        print(f"✗ 连接超时（5秒）")
        return False
    except ConnectionRefusedError:
        print(f"✗ 连接被拒绝 - 目标端口未开放")
        return False
    except socket.gaierror as e:
        print(f"✗ DNS解析失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 连接失败: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    success = test_tcp_connection()
    exit(0 if success else 1)
