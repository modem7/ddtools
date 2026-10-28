"""The base for every error ddtools reports to the user.

This module imports nothing from ddtools, so any module can use it without a cycle.
"""

from __future__ import annotations


class DdtoolsError(Exception):
    """An error ddtools reports as a message, not a traceback.

    The message says what went wrong and which file or character it was. The command
    line catches this base and prints it.
    """
