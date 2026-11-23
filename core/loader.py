# Astro Userbot
# © جميع الحقوق محفوظة
import importlib
import importlib.util
import logging
import sys

from . import PLUGINS_DIR, PREFIX, lang, registry, state
from . import errors as err

log = logging.getLogger("astro.loader")


def _load_file(stem, path):
    registry.current = stem
    try:
        name = f"plugins.{stem}"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        registry.current = None


def load_all():
    """Load the built-in commands, then every plugin file. Returns failure notes."""
    registry.current = "core"
    try:
        importlib.import_module("core.builtin")
    finally:
        registry.current = None

    failed = []
    state.loaded.clear()
    state.failed.clear()
    for path in sorted(PLUGINS_DIR.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            _load_file(path.stem, path)
            state.loaded[path.stem] = 0
            log.info("loaded plugin %s", path.name)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            log.exception("plugin failed: %s", path.name)
            registry.rollback(path.stem)
            hint = lang.LOAD_FAILED_HINT.format(
                add=f"{PREFIX}{lang.CMD_ADD_FILE}", update=f"{PREFIX}{lang.CMD_UPDATE}"
            )
            body = err.describe(exc, hint)
            state.failed.append((path.name, err.reason(exc)))
            failed.append(f"{lang.LOAD_FAILED.format(name=path.name)}\n{body}")
    for plugin, names in registry.by_plugin().items():
        if plugin in state.loaded:
            state.loaded[plugin] = len(names)
    return failed
