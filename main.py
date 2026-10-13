"""Time Calculator - entry point."""
import sys


def _enable_dpi_awareness():
    """Crisp text on high-DPI Windows displays (the UI scales itself to match)."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


if __name__ == "__main__":
    _enable_dpi_awareness()
    from timecalc.ui import run
    run()
