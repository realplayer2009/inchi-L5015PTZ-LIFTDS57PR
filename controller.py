"""控制器：聚合两个轴，轮询线程，缓存状态。"""
from __future__ import annotations
import threading
import time
import random
from typing import Optional
from rs485_comm import RS485Comm
from gimbal_axis import GimbalAxis
from config import axis_yaw_config, axis_pitch_config, comm_config, controller_config
from safety import SafetyManager

FUNC_WRITE_ANGLE = 0x01
FUNC_READ_ANGLE = 0x02
FUNC_READ_FAULT = 0x03

class GimbalController:
    def __init__(self):
        self.yaw = GimbalAxis(axis_yaw_config.name, axis_yaw_config.min_deg, axis_yaw_config.max_deg, axis_yaw_config.zero_offset_deg)
        self.pitch = GimbalAxis(axis_pitch_config.name, axis_pitch_config.min_deg, axis_pitch_config.max_deg, axis_pitch_config.zero_offset_deg)
        self._comm = RS485Comm()
        self._safety = SafetyManager()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._stop_evt = threading.Event()
        self._cache_lock = threading.Lock()
        self._last_update_ts = time.monotonic()
        self._started = False

    def start(self):
        if not self._started:
            self._poll_thread.start()
            self._started = True

    def stop(self):
        self._stop_evt.set()

    def _simulate_angle(self, axis: GimbalAxis) -> float:
        base = (axis.min_deg + axis.max_deg) / 2.0
        noise = random.uniform(-controller_config.simulate_noise_deg, controller_config.simulate_noise_deg)
        return base + noise

    def _read_angle(self, address: int) -> Optional[float]:
        if not self._comm.available:
            return None
        data = self._comm.transact(address, FUNC_READ_ANGLE)
        if data is None or len(data) < 2:
            return None
        # int16 0.01°
        val = int.from_bytes(data[:2], byteorder='little', signed=True)
        return val / 100.0

    def _write_angle(self, address: int, target_deg: float) -> bool:
        if not self._comm.available:
            return False
        val = int(target_deg * 100)
        payload = val.to_bytes(2, byteorder='little', signed=True)
        data = self._comm.transact(address, FUNC_WRITE_ANGLE, payload)
        if data is None or len(data) < 1:
            return False
        status_code = data[0]
        return status_code == 0

    def set_angles(self, yaw_deg: float, pitch_deg: float) -> bool:
        # 软限位提前校验
        if not self.yaw.validate(yaw_deg):
            self.yaw.add_fault('RANGE')
            return False
        else:
            self.yaw.clear_fault('RANGE')
        if not self.pitch.validate(pitch_deg):
            self.pitch.add_fault('RANGE')
            return False
        else:
            self.pitch.clear_fault('RANGE')
        ok_y = self._write_angle(comm_config.address_yaw, yaw_deg) if self._comm.available else True
        ok_p = self._write_angle(comm_config.address_pitch, pitch_deg) if self._comm.available else True
        if not (ok_y and ok_p):
            self._safety.add_fault('WRITE_FAIL')
            return False
        else:
            self._safety.clear_fault('WRITE_FAIL')
        return True

    def _poll_loop(self):
        while not self._stop_evt.is_set():
            updated = False
            yaw_val = self._read_angle(comm_config.address_yaw)
            pitch_val = self._read_angle(comm_config.address_pitch)
            if yaw_val is None and controller_config.simulate_if_fail:
                yaw_val = self._simulate_angle(self.yaw)
                self.yaw.add_fault('COMM_SIM')
            else:
                self.yaw.clear_fault('COMM_SIM')
            if pitch_val is None and controller_config.simulate_if_fail:
                pitch_val = self._simulate_angle(self.pitch)
                self.pitch.add_fault('COMM_SIM')
            else:
                self.pitch.clear_fault('COMM_SIM')
            if yaw_val is not None and pitch_val is not None:
                with self._cache_lock:
                    self.yaw.update_raw(yaw_val)
                    self.pitch.update_raw(pitch_val)
                    self._last_update_ts = time.monotonic()
                self._safety.mark_comm_ok()
                updated = True
            time.sleep(comm_config.poll_interval_s)
        
    def get_status(self):
        with self._cache_lock:
            yaw_state = self.yaw.state
            pitch_state = self.pitch.state
            status = self._safety.compose_status(self._last_update_ts)
        return {
            'yaw': {
                'raw_deg': yaw_state.raw_deg,
                'corrected_deg': yaw_state.corrected_deg,
                'rad': yaw_state.rad,
                'in_range': yaw_state.in_range,
                'faults': yaw_state.faults,
            },
            'pitch': {
                'raw_deg': pitch_state.raw_deg,
                'corrected_deg': pitch_state.corrected_deg,
                'rad': pitch_state.rad,
                'in_range': pitch_state.in_range,
                'faults': pitch_state.faults,
            },
            'status': status
        }
