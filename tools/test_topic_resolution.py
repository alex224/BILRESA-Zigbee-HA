"""Exercise topic resolution without requiring a Home Assistant installation."""

import ast
import asyncio
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace


class NotReady(Exception):
    pass


@dataclass(frozen=True)
class Config:
    remote_id: str = "0x1234"
    name: str = "Display name"
    topic_name: str | None = None
    mode: None = None

    @classmethod
    def from_subentry(cls, data, *, base_topic):
        return cls()


class Coordinator:
    def __init__(self, hass, config, *, mode_resolver):
        self.config = config

    async def async_start(self):
        pass


def load_setup():
    source = Path("custom_components/bilresa_remote/__init__.py").read_text()
    tree = ast.parse(source)
    func = next(
        n
        for n in tree.body
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "_async_setup_remote"
    )
    module = ast.Module(
        body=[
            ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
            func,
        ],
        type_ignores=[],
    )
    return compile(ast.fix_missing_locations(module), "integration", "exec")


async def check(compiled):
    devices = [{"ieee_address": "0x1234", "friendly_name": "IKEA Bilresa grün"}]

    async def fetch(hass, base_topic):
        return devices

    env = {
        "RemoteConfig": Config,
        "replace": replace,
        "async_fetch_devices": fetch,
        "Z2MError": RuntimeError,
        "ConfigEntryNotReady": NotReady,
        "ModeResolver": lambda *a, **kw: None,
        "BilresaCoordinator": Coordinator,
        "RemoteRuntime": lambda **kw: SimpleNamespace(**kw),
    }
    exec(compiled, env)
    subentry = SimpleNamespace(data={}, subentry_id="id", title="remote")
    result = await env["_async_setup_remote"](None, subentry, "zigbee2mqtt", None)
    assert result.ieee == "0x1234"
    assert result.config.topic_name == "IKEA Bilresa grün"
    devices.clear()
    try:
        await env["_async_setup_remote"](None, subentry, "zigbee2mqtt", None)
    except NotReady:
        pass
    else:
        raise AssertionError("missing device must cause a retry")
    print("Topic resolution and missing-device retry: OK")


asyncio.run(check(load_setup()))
