# SPDX-License-Identifier: Apache-2.0
"""
Plugin autodiscovery and registration.

This module provides the autodiscover function that scans the plugins directory
and imports all plugin packages, triggering their registration with the registry.
"""

import importlib
import logging
import pkgutil
from pathlib import Path

logger = logging.getLogger(__name__)


def autodiscover():
    """
    Scan plugins directory and import all plugin packages.

    Each plugin package should register itself with the registry
    when imported (typically in its __init__.py).

    Import errors are logged but don't stop the discovery process.
    """
    from plugins.base import registry

    plugins_dir = Path(__file__).parent

    for module_info in pkgutil.iter_modules([str(plugins_dir)]):
        # Skip base module (it's infrastructure, not a plugin)
        if module_info.name == "base":
            continue

        module_name = f"plugins.{module_info.name}"
        try:
            importlib.import_module(module_name)
            logger.debug("Loaded plugin: %s", module_name)
        except ImportError as e:
            logger.warning("Failed to import plugin %s: %s", module_name, e)
        except Exception as e:
            logger.error("Error loading plugin %s: %s", module_name, e)

    logger.info("Plugin autodiscovery complete: %s plugins loaded", len(registry.all()))
