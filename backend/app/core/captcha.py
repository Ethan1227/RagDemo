"""图形验证码：生成 + 校验。

生成 4 位字符验证码图片（base64 PNG），验证码文本存入内存 TTL 存储，
以 captcha_id 关联。校验成功或过期后即失效（一次性）。

内存存储适用于单机部署；如需多实例可替换为 Redis（services 层可插拔）。
"""
from __future__ import annotations

import base64
import io
import random
import threading
import time
import uuid

from PIL import Image, ImageDraw, ImageFont

# 去除易混淆字符（0/O、1/I/l）
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
_CODE_LEN = 4
_TTL_SECONDS = 300
_WIDTH, _HEIGHT = 120, 44


class _CaptchaStore:
    """带 TTL 的内存验证码存储，线程安全。"""

    def __init__(self, ttl: int = _TTL_SECONDS) -> None:
        self._ttl = ttl
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()

    def put(self, code: str) -> str:
        captcha_id = uuid.uuid4().hex
        with self._lock:
            self._purge()
            self._data[captcha_id] = (code.upper(), time.time() + self._ttl)
        return captcha_id

    def verify(self, captcha_id: str, code: str) -> bool:
        """校验并使其失效（一次性）。"""
        if not captcha_id or not code:
            return False
        with self._lock:
            item = self._data.pop(captcha_id, None)
        if item is None:
            return False
        expected, expire_at = item
        if time.time() > expire_at:
            return False
        return expected == code.strip().upper()

    def _purge(self) -> None:
        now = time.time()
        expired = [k for k, (_, exp) in self._data.items() if exp < now]
        for k in expired:
            self._data.pop(k, None)


_store = _CaptchaStore()


def _random_code(length: int = _CODE_LEN) -> str:
    return "".join(random.choice(_ALPHABET) for _ in range(length))


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """尽量使用系统字体，失败则退回 PIL 默认位图字体。"""
    for name in ("arial.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_captcha() -> tuple[str, str]:
    """生成验证码，返回 (captcha_id, base64_png_data_uri)。"""
    code = _random_code()
    image = Image.new("RGB", (_WIDTH, _HEIGHT), (240, 243, 248))
    draw = ImageDraw.Draw(image)
    font = _load_font(28)

    # 干扰线
    for _ in range(5):
        xy = [random.randint(0, _WIDTH), random.randint(0, _HEIGHT),
              random.randint(0, _WIDTH), random.randint(0, _HEIGHT)]
        draw.line(xy, fill=(random.randint(150, 200),) * 3, width=1)

    # 逐字符绘制，带随机颜色与偏移
    for i, ch in enumerate(code):
        color = (random.randint(20, 90), random.randint(30, 80), random.randint(80, 150))
        x = 12 + i * 26 + random.randint(-3, 3)
        y = random.randint(2, 10)
        draw.text((x, y), ch, font=font, fill=color)

    # 干扰点
    for _ in range(60):
        draw.point(
            (random.randint(0, _WIDTH), random.randint(0, _HEIGHT)),
            fill=(random.randint(150, 220),) * 3,
        )

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    captcha_id = _store.put(code)
    return captcha_id, f"data:image/png;base64,{b64}"


def verify_captcha(captcha_id: str, code: str) -> bool:
    """校验验证码（一次性）。"""
    return _store.verify(captcha_id, code)
