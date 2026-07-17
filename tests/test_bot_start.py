"""Tests that the bot thread starts when BOT_START=true, even under gunicorn.

The bug: _start_bot_thread() is only called inside `if __name__ == "__main__":`,
which never runs when gunicorn imports dashboard.py. The bot never starts,
set_bot_adapter() is never called, and api.py's StubBotAdapter default serves
fake data forever.
"""

from pathlib import Path


DASHBOARD_PY = Path(__file__).resolve().parent.parent / "dashboard.py"


def _read_source():
    return DASHBOARD_PY.read_text(encoding="utf-8")


def _lines_in_main_guard(source):
    """Return True if _start_bot_thread() is called inside the __main__ guard."""
    lines = source.splitlines()
    in_main_guard = False
    main_guard_indent = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if stripped.startswith('if __name__ == "__main__"'):
            in_main_guard = True
            main_guard_indent = indent
            continue

        if in_main_guard:
            if indent <= main_guard_indent:
                in_main_guard = False
            elif "_start_bot_thread" in stripped:
                return True

    return False


def _bot_start_at_module_level(source):
    """Return True if the BOT_START check is at module level (outside __main__)."""
    lines = source.splitlines()
    in_main_guard = False
    main_guard_indent = None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if stripped.startswith('if __name__ == "__main__"'):
            in_main_guard = True
            main_guard_indent = indent
            continue

        if in_main_guard and indent <= main_guard_indent:
            in_main_guard = False

        if not in_main_guard and "BOT_START" in stripped:
            return True

    return False


class TestBotStartsOnModuleImport:
    """When BOT_START=true, importing dashboard.py must start the bot thread."""

    def test_bot_start_check_is_not_inside_main_guard(self):
        """The BOT_START check must be at module level, not inside __main__.

        This is the root cause test. If BOT_START + _start_bot_thread() is
        inside `if __name__ == "__main__":`, it never runs under gunicorn.
        """
        source = _read_source()
        assert not _lines_in_main_guard(source), (
            "_start_bot_thread() is called inside `if __name__ == '__main__':` "
            "— it will never run under gunicorn. Move it to module level."
        )

    def test_bot_start_check_exists_at_module_level(self):
        """The BOT_START check must exist at module level."""
        source = _read_source()
        assert _bot_start_at_module_level(source), (
            "BOT_START check must be at module level, "
            "not inside `if __name__ == '__main__':`."
        )
