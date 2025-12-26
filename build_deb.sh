#!/bin/bash
# build_deb.sh - 构建InchiPTZ deb包的脚本

set -e

PACKAGE_NAME="inchiptz"
VERSION="1.0.1"
ARCH="all"
BUILD_DIR="build/${PACKAGE_NAME}_${VERSION}_${ARCH}"

echo "======================================"
echo "构建 ${PACKAGE_NAME} deb 包"
echo "版本: ${VERSION}"
echo "架构: ${ARCH}"
echo "======================================"

# 清理旧的构建目录
if [ -d "build" ]; then
    echo "清理旧的构建目录..."
    rm -rf build
fi

# 创建deb包目录结构
echo "创建目录结构..."
mkdir -p ${BUILD_DIR}/DEBIAN
mkdir -p ${BUILD_DIR}/usr/share/inchiptz
mkdir -p ${BUILD_DIR}/etc/systemd/system
mkdir -p ${BUILD_DIR}/var/log/inchiptz

# 复制控制文件
echo "复制控制文件..."
cp debian/control ${BUILD_DIR}/DEBIAN/
cp debian/postinst ${BUILD_DIR}/DEBIAN/
cp debian/prerm ${BUILD_DIR}/DEBIAN/
chmod 755 ${BUILD_DIR}/DEBIAN/postinst
chmod 755 ${BUILD_DIR}/DEBIAN/prerm

# 复制Python源代码
echo "复制应用程序文件..."
cp api_server.py ${BUILD_DIR}/usr/share/inchiptz/
cp ptz_controller.py ${BUILD_DIR}/usr/share/inchiptz/
cp lift_motor.py ${BUILD_DIR}/usr/share/inchiptz/
cp rs485_comm.py ${BUILD_DIR}/usr/share/inchiptz/
cp proto_v43.py ${BUILD_DIR}/usr/share/inchiptz/

# 复制systemd服务文件
echo "复制systemd服务文件..."
cp debian/inchiptz.service ${BUILD_DIR}/etc/systemd/system/

# 设置文件权限
echo "设置文件权限..."
chmod 755 ${BUILD_DIR}/usr/share/inchiptz/api_server.py
chmod 644 ${BUILD_DIR}/usr/share/inchiptz/*.py
chmod 644 ${BUILD_DIR}/etc/systemd/system/inchiptz.service

# 构建deb包
echo "构建deb包..."
dpkg-deb --build ${BUILD_DIR}

# 移动到输出目录
echo "移动deb包到当前目录..."
mv build/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb .

echo "======================================"
echo "构建完成!"
echo "输出文件: ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "======================================"
echo ""
echo "安装命令:"
echo "  sudo dpkg -i ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "卸载命令:"
echo "  sudo dpkg -r ${PACKAGE_NAME}"
echo ""
echo "如果依赖项缺失，运行:"
echo "  sudo apt-get install -f"
echo ""
