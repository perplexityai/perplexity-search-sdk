"""Places the prebuilt cdylib for the target platform into the package and
tags the wheel cp312-abi3-<platform>. No compiler: bin/ ships ready-made."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

SUPPORTED = (
    "manylinux2014_x86_64",
    "manylinux2014_aarch64",
    "macosx_11_0_x86_64",
    "macosx_11_0_arm64",
)
SO_NAME = "pplx_sdk.abi3.so"


def _host_platform_tag() -> str:
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if sys.platform == "darwin":
        return "macosx_11_0_arm64" if arm else "macosx_11_0_x86_64"
    if sys.platform.startswith("linux"):
        return "manylinux2014_aarch64" if arm else "manylinux2014_x86_64"
    raise RuntimeError(f"unsupported platform: {sys.platform}/{machine}")


class PrebuiltCdylibHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        plat = os.environ.get("PPLX_SDK_PLATFORM") or _host_platform_tag()
        if plat not in SUPPORTED:
            raise RuntimeError(f"PPLX_SDK_PLATFORM must be one of {SUPPORTED}, got {plat!r}")

        root = Path(self.root)
        so = root / "bin" / plat / SO_NAME
        if not so.is_file():
            raise RuntimeError(f"missing {so}; bin/ is delivered by the internal build")

        meta = json.loads((root / "bin" / "metadata.json").read_text())
        want = meta["sha256s"][plat]
        got = hashlib.sha256(so.read_bytes()).hexdigest()
        if got != want:
            raise RuntimeError(f"{so} sha256 {got} != bin/metadata.json {want}")

        shutil.copyfile(so, root / "src" / "pplx_srch_sdk" / SO_NAME)
        build_data["pure_python"] = False
        build_data["tag"] = f"cp312-abi3-{plat}"

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        (Path(self.root) / "src" / "pplx_srch_sdk" / SO_NAME).unlink(missing_ok=True)
