#!/usr/bin/env python3
"""Convert STEP (.stp/.step) CAD to GLB for PQ-AI body-map 3D view.

Uses ``cascadio`` (Open CASCADE tessellation). Install once:

    pip install cascadio==0.0.17

Default: paint.stp → apps/web/public/body-models/custom/ms11.glb
and registers the asset in view-models.json.

Examples
--------
    python scripts/stp_to_glb.py
    python scripts/stp_to_glb.py --input "...paint.stp" --model-key ms11
    python scripts/stp_to_glb.py --tol-linear 0.5 --no-manifest
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "apps"
    / "web"
    / "public"
    / "body-models"
    / "custom"
    / "MVPS10032-W42FROZEN-00000000150 BODY STRUCTUREa.2 paint.stp"
)
DEFAULT_OUTPUT = ROOT / "apps" / "web" / "public" / "body-models" / "custom" / "ms11.glb"
MANIFEST_PATH = ROOT / "apps" / "web" / "public" / "body-models" / "view-models.json"


def _mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def update_manifest(model_key: str, glb_public_url: str, *, up_axis: str, unit_scale: float) -> None:
    manifest = {"version": 1, "models": {}}
    if MANIFEST_PATH.is_file():
        try:
            payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                manifest["version"] = int(payload.get("version") or 1)
                models = payload.get("models")
                if isinstance(models, dict):
                    manifest["models"] = models
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    manifest["models"][model_key] = {
        "url": glb_public_url,
        "up_axis": up_axis,
        "unit_scale": unit_scale,
        "bounds": None,
        "model_asset_key": glb_public_url,
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def convert(
    input_path: Path,
    output_path: Path,
    *,
    tol_linear: float,
    tol_angular: float,
    tol_relative: bool,
    merge_primitives: bool,
    use_parallel: bool,
) -> int:
    try:
        import cascadio
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "缺少依赖 cascadio。请先执行: pip install cascadio==0.0.17"
        ) from exc

    if not input_path.is_file():
        raise SystemExit(f"输入文件不存在: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[stp→glb] input : {input_path} ({_mb(input_path):.1f} MB)")
    print(f"[stp→glb] output: {output_path}")
    print(
        f"[stp→glb] tol_linear={tol_linear} tol_angular={tol_angular} "
        f"tol_relative={tol_relative} merge_primitives={merge_primitives}"
    )

    started = time.perf_counter()
    # cascadio returns int status (0 = success typically)
    status = cascadio.step_to_glb(
        str(input_path),
        str(output_path),
        tol_linear=tol_linear,
        tol_angular=tol_angular,
        tol_relative=tol_relative,
        merge_primitives=merge_primitives,
        use_parallel=use_parallel,
    )
    elapsed = time.perf_counter() - started

    if not output_path.is_file():
        raise SystemExit(f"转换失败：未生成输出文件（status={status}）")

    size_mb = _mb(output_path)
    print(f"[stp→glb] done   status={status} size={size_mb:.1f} MB elapsed={elapsed:.1f}s")
    if size_mb > 80:
        print(
            "[stp→glb] warning: GLB > 80MB，超过网页上传上限。"
            "可用更大 --tol-linear（如 1.0 / 2.0）再转一版。"
        )
    return int(status) if isinstance(status, int) else 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="STEP → GLB for PQ-AI body-map 3D")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="STEP 输入路径")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="GLB 输出路径")
    parser.add_argument("--model-key", default="ms11", help="写入 view-models.json 的车型 key")
    parser.add_argument(
        "--tol-linear",
        type=float,
        default=0.5,
        help="线性离散公差（模型单位，车身 STEP 多为 mm；Web 建议 0.5~2.0）",
    )
    parser.add_argument("--tol-angular", type=float, default=0.5, help="角度离散公差（弧度相关）")
    parser.add_argument(
        "--tol-relative",
        action="store_true",
        help="将 tol_linear 视为相对边长比例",
    )
    parser.add_argument(
        "--no-merge-primitives",
        action="store_true",
        help="不为每个零件合并 primitive（默认合并）",
    )
    parser.add_argument("--no-parallel", action="store_true", help="关闭并行网格化")
    parser.add_argument("--up-axis", default="Y", choices=["X", "Y", "Z"])
    parser.add_argument(
        "--unit-scale",
        type=float,
        default=0.001,
        help="前端缩放：STEP 常为 mm，Web 用米则 0.001",
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="不更新 view-models.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    status = convert(
        args.input.resolve(),
        args.output.resolve(),
        tol_linear=args.tol_linear,
        tol_angular=args.tol_angular,
        tol_relative=args.tol_relative,
        merge_primitives=not args.no_merge_primitives,
        use_parallel=not args.no_parallel,
    )

    if not args.no_manifest:
        # public URL relative to apps/web/public
        try:
            rel = args.output.resolve().relative_to((ROOT / "apps" / "web" / "public").resolve())
            public_url = "/" + rel.as_posix()
        except ValueError:
            public_url = f"/body-models/custom/{args.output.name}"
        update_manifest(
            args.model_key.strip().lower(),
            public_url,
            up_axis=args.up_axis,
            unit_scale=args.unit_scale,
        )
        print(f"[stp→glb] manifest updated: {MANIFEST_PATH}")
        print(f"[stp→glb] model key={args.model_key!r} url={public_url}")

    print("[stp→glb] 下一步：打开质量管理 → 3D View，选择 code 匹配的车型（如 MS11）加载数模。")
    return 0 if status == 0 else status


if __name__ == "__main__":
    sys.exit(main())
