import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = ROOT / "desktop" / "scripts" / "prepare_runtime.py"


def load_module():
    spec = importlib.util.spec_from_file_location("prepare_runtime", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DesktopRuntimeBundleTests(unittest.TestCase):
    def test_build_repo_copy_jobs_preserves_manifest_relative_paths(self):
        module = load_module()
        repo_root = Path("/tmp/fake-repo")
        manifest = {
            "include": [
                "publish.py",
                "scripts/workbench_bridge.py",
                "tiandi_engine",
            ]
        }

        jobs = module.build_repo_copy_jobs(repo_root, manifest)

        self.assertEqual(
            jobs,
            [
                (repo_root / "publish.py", Path("publish.py")),
                (repo_root / "scripts" / "workbench_bridge.py", Path("scripts/workbench_bridge.py")),
                (repo_root / "tiandi_engine", Path("tiandi_engine")),
            ],
        )

    def test_prepare_runtime_builds_packaged_repo_and_python_layout(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            repo_root.mkdir()
            (repo_root / "scripts").mkdir()
            (repo_root / "scripts" / "workbench_bridge.py").write_text("print('ok')", encoding="utf-8")
            (repo_root / "publish.py").write_text("print('publish')", encoding="utf-8")

            python_prefix = root / "python-prefix"
            (python_prefix / "bin").mkdir(parents=True)
            (python_prefix / "bin" / "python3").write_text("", encoding="utf-8")
            (python_prefix / "lib" / "python3.11").mkdir(parents=True)
            (python_prefix / "lib" / "python3.11" / "os.py").write_text("# stdlib", encoding="utf-8")
            (python_prefix / "lib" / "python3.11" / "site-packages" / "pip").mkdir(parents=True)
            (python_prefix / "lib" / "python3.11" / "site-packages" / "pip" / "__init__.py").write_text(
                "# bundled but unused",
                encoding="utf-8",
            )

            extra_site_packages = root / "venv-site-packages"
            (extra_site_packages / "demo_pkg").mkdir(parents=True)
            (extra_site_packages / "demo_pkg" / "__init__.py").write_text("# pkg", encoding="utf-8")
            (extra_site_packages / "imageio_ffmpeg").mkdir(parents=True)
            (extra_site_packages / "imageio_ffmpeg" / "__init__.py").write_text("# large unused pkg", encoding="utf-8")

            manifest = {
                "runtime_root": "ordo-runtime",
                "bundled_repo_root": "repo",
                "bundled_python": {"root": "python", "executable": "python/bin/python3"},
                "bundled_node": {"root": "node", "executable": "node/bin/node"},
                "include": ["publish.py", "scripts/workbench_bridge.py"],
            }
            output_root = root / "runtime-dist"

            node_prefix = root / "node-prefix"
            (node_prefix / "bin").mkdir(parents=True)
            (node_prefix / "bin" / "node").write_text("", encoding="utf-8")
            (node_prefix / "lib").mkdir(parents=True)
            (node_prefix / "lib" / "libnode.1.dylib").write_text("", encoding="utf-8")

            runtime_dir = module.prepare_runtime(
                repo_root=repo_root,
                output_root=output_root,
                manifest=manifest,
                python_metadata={
                    "base_prefix": str(python_prefix),
                    "executable": str(python_prefix / "bin" / "python3"),
                    "site_packages": [str(extra_site_packages)],
                    "version_dir_name": "python3.11",
                    "required_site_package_names": ["demo_pkg"],
                },
                node_metadata={
                    "prefix": str(node_prefix),
                    "executable": str(node_prefix / "bin" / "node"),
                },
            )

            self.assertEqual(runtime_dir, output_root / "ordo-runtime")
            self.assertTrue((runtime_dir / "repo" / "publish.py").is_file())
            self.assertTrue((runtime_dir / "repo" / "scripts" / "workbench_bridge.py").is_file())
            self.assertTrue((runtime_dir / "python" / "bin" / "python3").exists())
            self.assertTrue((runtime_dir / "node" / "bin" / "node").exists())
            self.assertTrue((runtime_dir / "node" / "lib" / "libnode.1.dylib").exists())
            self.assertTrue((runtime_dir / "node-runtime.tar.gz").is_file())
            self.assertTrue((runtime_dir / "python" / "lib" / "python3.11" / "os.py").is_file())
            self.assertTrue(
                (runtime_dir / "python" / "lib" / "python3.11" / "site-packages" / "demo_pkg" / "__init__.py").is_file()
            )
            self.assertFalse((runtime_dir / "python" / "lib" / "python3.11" / "site-packages" / "pip").exists())
            self.assertFalse((runtime_dir / "python" / "lib" / "python3.11" / "site-packages" / "imageio_ffmpeg").exists())
            metadata = json.loads((runtime_dir / "runtime-metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["python"]["version_dir_name"], "python3.11")

    def test_prepare_runtime_updates_source_fingerprint_when_included_file_changes(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            repo_root.mkdir()
            (repo_root / "publish.py").write_text("print('v1')", encoding="utf-8")

            python_prefix = root / "python-prefix"
            (python_prefix / "bin").mkdir(parents=True)
            (python_prefix / "bin" / "python3").write_text("", encoding="utf-8")
            (python_prefix / "lib" / "python3.11" / "site-packages").mkdir(parents=True)

            node_prefix = root / "node-prefix"
            (node_prefix / "bin").mkdir(parents=True)
            (node_prefix / "bin" / "node").write_text("", encoding="utf-8")
            (node_prefix / "lib").mkdir(parents=True)
            (node_prefix / "lib" / "libnode.1.dylib").write_text("", encoding="utf-8")

            manifest = {
                "runtime_root": "ordo-runtime",
                "bundled_repo_root": "repo",
                "bundled_python": {"root": "python", "executable": "python/bin/python3"},
                "bundled_node": {"root": "node", "executable": "node/bin/node"},
                "include": ["publish.py"],
            }
            output_root = root / "runtime-dist"
            build_kwargs = {
                "repo_root": repo_root,
                "output_root": output_root,
                "manifest": manifest,
                "python_metadata": {
                    "base_prefix": str(python_prefix),
                    "executable": str(python_prefix / "bin" / "python3"),
                    "site_packages": [],
                    "version_dir_name": "python3.11",
                    "required_site_package_names": [],
                },
                "node_metadata": {
                    "prefix": str(node_prefix),
                    "executable": str(node_prefix / "bin" / "node"),
                },
            }

            first_runtime = module.prepare_runtime(**build_kwargs)
            first_meta = json.loads((first_runtime / "runtime-metadata.json").read_text(encoding="utf-8"))

            (repo_root / "publish.py").write_text("print('v2')", encoding="utf-8")

            second_runtime = module.prepare_runtime(**build_kwargs)
            second_meta = json.loads((second_runtime / "runtime-metadata.json").read_text(encoding="utf-8"))

            self.assertNotEqual(first_meta["source_fingerprint"], second_meta["source_fingerprint"])


if __name__ == "__main__":
    unittest.main()
