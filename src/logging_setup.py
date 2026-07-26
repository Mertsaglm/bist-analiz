"""Loglama kurulumu — dönen dosya logu + konsol."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from . import util

_KURULDU = False


def setup(cfg: dict, *, level: int = logging.INFO, sessiz: bool = False) -> None:
    """Kök logger'ı bir kez kurar. Tekrar çağrılırsa hiçbir şey yapmaz."""
    global _KURULDU
    if _KURULDU:
        return

    log_dir = util.resolve(cfg["paths"]["log_dir"])
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)-18s %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

    fh = RotatingFileHandler(log_dir / "bist.log", maxBytes=5_000_000,
                             backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(fh)

    if not sessiz:
        sh = logging.StreamHandler(sys.stderr)
        sh.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
        sh.setLevel(level)
        root.addHandler(sh)

    # yfinance ve urllib3 çok gürültülü — dosyaya da yazmasınlar.
    for gurultulu in ("yfinance", "urllib3", "peewee"):
        logging.getLogger(gurultulu).setLevel(logging.WARNING)

    _KURULDU = True
