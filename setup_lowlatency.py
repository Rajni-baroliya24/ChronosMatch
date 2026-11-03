"""Build only the additive ChronosMatch native extension."""
import os
from pathlib import Path
from setuptools import Extension, setup
from Cython.Build import cythonize

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
setup(
    name="chronosmatch-lowlatency",
    version="0.1.0",
    packages=["lowlatency"],
    ext_modules=cythonize(
        [Extension("lowlatency._native", ["lowlatency/_native.pyx"], language="c++",
                   extra_compile_args=["/O2", "/std:c++17"] if os.name == "nt" else ["-O3", "-std=c++17"])],
        annotate=True,
        compiler_directives={"language_level": 3},
    ),
)
