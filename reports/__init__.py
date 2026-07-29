"""PDF report generation for simulation snapshots."""

__all__ = ["compile_simulation_report"]


def __getattr__(name: str):
    if name == "compile_simulation_report":
        from reports.compile import compile_simulation_report

        return compile_simulation_report
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
