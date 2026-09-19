import pytest
from app.main import app
import sys

def _clear():
    app.dependency_overrides.clear()
    for mod_name, mod in list(sys.modules.items()):
        if mod and hasattr(mod, "client"):
            client_obj = getattr(mod, "client", None)
            if client_obj and hasattr(client_obj, "cookies"):
                try:
                    client_obj.cookies.clear()
                    client_obj.headers.clear()
                except Exception:
                    pass

@pytest.fixture(autouse=True)
def clear_test_client_cookies():
    _clear()
    yield
    _clear()

