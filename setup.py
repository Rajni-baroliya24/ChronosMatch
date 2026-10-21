
from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        name="limit_order_book",
        sources=["limit_order_book.pyx"],
    )
]

setup(
    name="limit_order_book",
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
    ),
)
