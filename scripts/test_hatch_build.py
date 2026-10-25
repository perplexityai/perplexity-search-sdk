import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hatch_build import PrebuiltCdylibHook


class PrebuiltCdylibHookTest(unittest.TestCase):
    def make_bundle(self, root: Path, tag: str) -> bytes:
        payload = b"verified native library"
        binary = root / "bin" / tag / "pplx_sdk.abi3.so"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(payload)
        (root / "bin" / "metadata.json").write_text(json.dumps({
            "sha256s": {tag: hashlib.sha256(payload).hexdigest()},
        }))
        (root / "src" / "pplx_srch_sdk").mkdir(parents=True)
        return payload

    def test_verified_library_is_packaged_for_each_platform(self) -> None:
        for tag in (
            "manylinux_2_28_x86_64",
            "manylinux_2_28_aarch64",
            "macosx_11_0_x86_64",
            "macosx_11_0_arm64",
        ):
            with self.subTest(tag=tag), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                payload = self.make_bundle(root, tag)
                hook = PrebuiltCdylibHook(str(root), {}, None, None, directory, "wheel")
                build_data = {}
                with patch.dict(os.environ, {"PPLX_SDK_PLATFORM": tag}, clear=True):
                    hook.initialize("standard", build_data)
                packaged = root / "src" / "pplx_srch_sdk" / "pplx_sdk.abi3.so"
                self.assertEqual(packaged.read_bytes(), payload)
                self.assertEqual(build_data, {
                    "pure_python": False,
                    "tag": f"cp312-abi3-{tag}",
                })
                hook.finalize("standard", build_data, "unused.whl")
                self.assertFalse(packaged.exists())

    def test_tampered_library_is_rejected_before_packaging(self) -> None:
        tag = "manylinux_2_28_x86_64"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_bundle(root, tag)
            (root / "bin" / tag / "pplx_sdk.abi3.so").write_bytes(b"tampered")
            hook = PrebuiltCdylibHook(str(root), {}, None, None, directory, "wheel")
            with patch.dict(os.environ, {"PPLX_SDK_PLATFORM": tag}, clear=True):
                with self.assertRaisesRegex(RuntimeError, "sha256"):
                    hook.initialize("standard", {})
            self.assertFalse((root / "src" / "pplx_srch_sdk" / "pplx_sdk.abi3.so").exists())
