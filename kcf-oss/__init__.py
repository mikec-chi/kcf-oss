"""KCF — the open knowledge-coding standard.

This file makes the open-source stack importable as the ``kcf_oss`` package when
installed as a wheel (the distribution maps the ``kcf-oss`` directory to the
``kcf_oss`` import name). It is inert for in-repo use: the reference tools are
run by path and import each other flatly, exactly as before.
"""

__version__ = "1.3.0"
