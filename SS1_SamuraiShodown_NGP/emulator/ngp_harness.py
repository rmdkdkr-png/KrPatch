# -*- coding: utf-8 -*-
"""ngp_harness.py — beetle-ngp(libretro) 헤드리스 하네스 (SS1용, 이 세션에서 재작성)

mednafen+Xvfb 경로가 이 컨테이너에서 불가(apt 차단)라서 libretro 코어 직결로 대체.
장점: 화면이 애초에 원본 해상도(160×152)로 나옴 — 3배 축소 복원 불필요.

사용:
    from ngp_harness import NGP
    n = NGP('/root/ss2_work/ss1/rom.ngp')
    n.run(600)                        # 프레임 진행
    n.press('option'); n.run(30)      # 키 1회 누르기(10프레임 홀드)
    n.screenshot('out.png', scale=3)
    n.save_state('a.state'); n.load_state('a.state')

버튼 이름: up down left right a b option
"""
import ctypes as C
import os

CORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'beetle-ngp', 'mednafen_ngp_libretro.so')

# libretro 상수
ENV_SET_PIXEL_FORMAT = 10
PIXFMT_RGB565 = 2
DEV_JOYPAD = 1
JOY = {'a': 0, 'b': 8, 'option': 3,
       'up': 4, 'down': 5, 'left': 6, 'right': 7}
# beetle-ngp 매핑: RETRO B(id0)→NGP A, RETRO A(id8)→NGP B, START(3)→OPTION
# (libretro.c 458행: JOYPAD_B 가 "A" 라벨)

_env_cb_t   = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
_video_cb_t = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
_audio_cb_t = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
_audiob_cb_t= C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
_poll_cb_t  = C.CFUNCTYPE(None)
_input_cb_t = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class _GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p),
                ('size', C.c_size_t), ('meta', C.c_char_p)]


class NGP:
    def __init__(self, rom_path, core_path=CORE, language='japanese'):
        self.lib = C.CDLL(core_path)
        self.w = self.h = 0
        self.frame = None           # bytes, RGB565 rows (w*2 each)
        self._held = {}             # button -> frames remaining
        self._lang_buf = C.create_string_buffer(language.encode())
        self._make_callbacks()
        lib = self.lib
        lib.retro_set_environment(self._env_cb)
        lib.retro_set_video_refresh(self._video_cb)
        lib.retro_set_audio_sample(self._audio_cb)
        lib.retro_set_audio_sample_batch(self._audiob_cb)
        lib.retro_set_input_poll(self._poll_cb)
        lib.retro_set_input_state(self._input_cb)
        lib.retro_init()
        data = open(rom_path, 'rb').read()
        self._romdata = C.create_string_buffer(data, len(data))
        gi = _GameInfo(rom_path.encode(), C.cast(self._romdata, C.c_void_p),
                       len(data), b'')
        if not lib.retro_load_game(C.byref(gi)):
            raise RuntimeError('retro_load_game failed')
        lib.retro_serialize_size.restype = C.c_size_t
        self._ss = lib.retro_serialize_size()

    def _make_callbacks(self):
        class _Var(C.Structure):
            _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]

        def env(cmd, data):
            if cmd == ENV_SET_PIXEL_FORMAT:
                fmt = C.cast(data, C.POINTER(C.c_int)).contents.value
                return fmt == PIXFMT_RGB565
            if cmd == 15 and data:                      # GET_VARIABLE
                v = C.cast(data, C.POINTER(_Var)).contents
                if v.key == b'ngp_language':
                    v.value = C.cast(self._lang_buf, C.c_char_p)
                    return True
                return False
            return False
        def video(ptr, w, h, pitch):
            if not ptr:
                return
            self.w, self.h = w, h
            buf = C.cast(ptr, C.POINTER(C.c_ubyte))
            rows = []
            for y in range(h):
                off = y * pitch
                rows.append(bytes(buf[off:off + w * 2]))
            self.frame = b''.join(rows)
        def audio(l, r):
            pass
        def audiob(ptr, frames):
            return frames
        def poll():
            pass
        def inp(port, device, index, _id):
            if port != 0:
                return 0
            for name, left in self._held.items():
                if left > 0 and JOY.get(name) == _id:
                    return 1
            return 0
        self._env_cb = _env_cb_t(env)
        self._video_cb = _video_cb_t(video)
        self._audio_cb = _audio_cb_t(audio)
        self._audiob_cb = _audiob_cb_t(audiob)
        self._poll_cb = _poll_cb_t(poll)
        self._input_cb = _input_cb_t(inp)

    # ---- 실행 ----
    def run(self, frames=1):
        for _ in range(frames):
            self.lib.retro_run()
            for k in list(self._held):
                self._held[k] -= 1
                if self._held[k] <= 0:
                    del self._held[k]

    def press(self, button, hold=10, wait=8):
        """버튼을 hold프레임 누르고 wait프레임 쉼 (연타 안전)."""
        self._held[button] = hold
        self.run(hold + wait)

    # ---- 화면 ----
    def pixels(self):
        """(h,w) uint8 RGB ndarray."""
        import numpy as np
        a = np.frombuffer(self.frame, dtype='<u2').reshape(self.h, self.w)
        r = ((a >> 11) & 31) * 255 // 31
        g = ((a >> 5) & 63) * 255 // 63
        b = (a & 31) * 255 // 31
        return np.stack([r, g, b], -1).astype('uint8')

    def screenshot(self, path, scale=1):
        from PIL import Image
        im = Image.fromarray(self.pixels())
        if scale > 1:
            im = im.resize((self.w * scale, self.h * scale), Image.NEAREST)
        im.save(path)
        return path

    # ---- 상태 ----
    def save_state(self, path):
        buf = C.create_string_buffer(self._ss)
        if not self.lib.retro_serialize(buf, self._ss):
            raise RuntimeError('serialize failed')
        open(path, 'wb').write(buf.raw)

    def load_state(self, path):
        data = open(path, 'rb').read()
        buf = C.create_string_buffer(data, len(data))
        if not self.lib.retro_unserialize(buf, len(data)):
            raise RuntimeError('unserialize failed')

    # ---- 디버그 (트레이싱 코어 전용) ----
    def watch(self, lo, hi):
        """CPU 주소 [lo,hi) 읽기 감시 시작 (로그 초기화). 파일오프셋+0x200000."""
        self.lib.retro_dbg_watch(C.c_uint32(lo), C.c_uint32(hi))

    def watch_log(self, uniq=True):
        """[(pc, addr), ...] — uniq=True면 (pc,addr) 중복 제거(순서 유지)."""
        n = self.lib.retro_dbg_log_count()
        pcf = self.lib.retro_dbg_log_pc; adf = self.lib.retro_dbg_log_ad
        pcf.restype = adf.restype = C.c_uint32
        out, seen = [], set()
        for i in range(n):
            t = (pcf(C.c_uint32(i)), adf(C.c_uint32(i)))
            if uniq:
                if t in seen:
                    continue
                seen.add(t)
            out.append(t)
        return out, n

    def wwatch(self, lo, hi):
        self.lib.retro_dbg_wwatch(C.c_uint32(lo), C.c_uint32(hi))

    def wlog(self):
        """[(pc, addr, value), ...] 쓰기 로그 (순서 그대로)."""
        n = self.lib.retro_dbg_wlog_count()
        pf, af, vf = (self.lib.retro_dbg_wlog_pc, self.lib.retro_dbg_wlog_ad,
                      self.lib.retro_dbg_wlog_v)
        pf.restype = af.restype = vf.restype = C.c_uint32
        return [(pf(C.c_uint32(i)), af(C.c_uint32(i)), vf(C.c_uint32(i)))
                for i in range(n)]

    def peek(self, addr, length=1):
        buf = C.create_string_buffer(length)
        self.lib.retro_dbg_peek_block(C.c_uint32(addr), C.c_uint32(length), buf)
        return buf.raw


if __name__ == '__main__':
    import sys
    n = NGP(sys.argv[1])
    n.run(int(sys.argv[2]) if len(sys.argv) > 2 else 300)
    print(n.screenshot(sys.argv[3] if len(sys.argv) > 3 else '/tmp/ngp.png', 3))
