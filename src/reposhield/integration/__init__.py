"""Formal agent integration helpers for RepoShield."""

from .connect import ConnectResult, connect_repo
from .coverage import build_coverage_report
from .doctor import DoctorReport, run_doctor
from .start import build_start_summary

__all__ = [
    "ConnectResult",
    "DoctorReport",
    "build_coverage_report",
    "build_start_summary",
    "connect_repo",
    "run_doctor",
]
