from typing import Any, TypeVar

T = TypeVar('T')


class KeyRegister(dict[T, Any]):
    def on_key(self, key: T):
        def wrapper(func):
            self[key] = func
            return func
        return wrapper

def pango_escape(str):
    return str.translate(
        {38: '&amp;'}
    ).translate({
        34: '&quot;',
        39: '&apos;',
        60: '&lt;',
        62: '&gt;'
    })

def format_duration(seconds):
    return f"{int(seconds // 3600):02d}:{int(seconds // 60 % 60):02d}"
