"""Shared CST runtime primitives.

This package is intentionally protocol-neutral. CLI adapters should
import from cst_runtime.cli or cst_runtime.cli_pipelines.
"""
from cst_runtime.core import (
    modeling,
    project as project_ops,
    results,
    farfield,
    session as session_manager,
    audit,
    workspace,
    identity as project_identity,
    process as process_cleanup,
    environment as cst_env,
    evidence,
    errors,
    utils,
)
