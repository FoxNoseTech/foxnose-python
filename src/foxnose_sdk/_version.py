"""Single source of truth for the package version.

Read by ``foxnose_sdk.__version__``, by the transport ``User-Agent`` string, and
by the build backend (see ``[tool.hatch.version]`` in ``pyproject.toml``).
"""

__version__ = "0.7.0"
