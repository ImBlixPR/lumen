"""Pick CUDA when an NVIDIA GPU is usable, otherwise the CPU, and tune compute types."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    device: str  # "cuda" or "cpu"
    compute_type: str
    name: str


CPU = DeviceInfo("cpu", "int8", "CPU")


def cpu_threads() -> int:
    """Leave two cores free so audio playback and the UI stay smooth."""
    return max(1, (os.cpu_count() or 4) - 2)


def add_cuda_library_paths() -> None:
    """Expose the cuBLAS/cuDNN DLLs shipped by the `nvidia-*-cu12` wheels (the `gpu` extra)."""
    bases: list[str] = []
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:  # PyInstaller build: the wheels' DLLs are copied under _internal/nvidia
        bases.append(str(Path(bundle) / "nvidia"))
    spec = importlib.util.find_spec("nvidia")
    if spec is not None and spec.submodule_search_locations:
        bases.extend(spec.submodule_search_locations)
    subdir = "bin" if sys.platform == "win32" else "lib"
    for base in bases:
        for lib_dir in sorted(Path(base).glob(f"*/{subdir}")):
            if sys.platform == "win32":
                os.add_dll_directory(str(lib_dir))
            os.environ["PATH"] = f"{lib_dir}{os.pathsep}{os.environ.get('PATH', '')}"


def _gpu_name() -> str:
    try:
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, creationflags=flags,
        )
        return out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else "NVIDIA GPU"
    except (OSError, subprocess.SubprocessError, IndexError):
        return "NVIDIA GPU"


def _cuda_libraries_present() -> bool:
    """CTranslate2 sees a GPU even without cuBLAS/cuDNN, then fails at the first inference."""
    if sys.platform != "win32":
        return True
    import ctypes

    import ctranslate2

    os.add_dll_directory(str(Path(ctranslate2.__file__).parent))
    for name in ("cublas64_12.dll", "cublasLt64_12.dll", "cudnn64_9.dll"):
        try:
            # winmode=0: the classic search order, PATH included. CTranslate2 loads the DLLs the
            # same way, so a system-wide CUDA install counts too, not just the `gpu` extra.
            ctypes.WinDLL(name, winmode=0)
        except OSError:
            return False
    return True


@lru_cache(maxsize=1)
def detect() -> DeviceInfo:
    if os.environ.get("LUMEN_FORCE_CPU"):
        return CPU
    add_cuda_library_paths()
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() < 1 or not _cuda_libraries_present():
            return CPU
        supported = ctranslate2.get_supported_compute_types("cuda")
    except Exception:
        return CPU
    for compute in ("int8_float16", "float16", "int8", "float32"):
        if compute in supported:
            return DeviceInfo("cuda", compute, _gpu_name())
    return CPU


def lower_process_priority() -> None:
    """Run heavy model work below normal priority so playback never stutters."""
    try:
        if sys.platform == "win32":
            import ctypes

            below_normal = 0x00004000
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), below_normal)
        else:
            os.nice(5)
    except OSError:
        pass
