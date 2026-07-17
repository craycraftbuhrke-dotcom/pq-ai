"""STEP (.stp/.step) → GLB conversion for body-map 3D assets.

Requires optional dependency ``cascadio`` (Open CASCADE tessellation):
``pip install cascadio==0.0.17`` or ``pip install .[cad]``.
"""

from __future__ import annotations

from pathlib import Path


class StpConvertError(RuntimeError):
    """Raised when STEP conversion cannot run or fails."""


def cascadio_available() -> bool:
    try:
        import cascadio  # noqa: F401
    except ImportError:
        return False
    return True


def step_to_glb(
    input_path: Path | str,
    output_path: Path | str,
    *,
    tol_linear: float = 0.5,
    tol_angular: float = 0.5,
    tol_relative: bool = False,
    merge_primitives: bool = True,
    use_parallel: bool = True,
) -> Path:
    """Convert a STEP file to GLB. Returns the output path."""
    try:
        import cascadio
    except ImportError as exc:
        raise StpConvertError(
            "服务器未安装 STEP 转换依赖 cascadio，请执行 pip install cascadio==0.0.17"
        ) from exc

    src = Path(input_path)
    dst = Path(output_path)
    if not src.is_file():
        raise StpConvertError(f"STEP 文件不存在: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    status = cascadio.step_to_glb(
        str(src),
        str(dst),
        tol_linear=tol_linear,
        tol_angular=tol_angular,
        tol_relative=tol_relative,
        merge_primitives=merge_primitives,
        use_parallel=use_parallel,
    )
    if not dst.is_file():
        raise StpConvertError(f"STEP 转换失败，未生成 GLB（status={status}）")
    if status not in (0, None):
        # cascadio documents 0 as success; tolerate None for older bindings
        if isinstance(status, int) and status != 0:
            raise StpConvertError(f"STEP 转换返回非零状态: {status}")
    return dst


__all__ = ["StpConvertError", "cascadio_available", "step_to_glb"]
