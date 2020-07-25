# -*- coding: utf-8 -*-

import setuptools

from .autocord import __version__

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="tf2-autocord",
    url="https://github.com/Gobot1234/tf2-autocord",
    requirements=requirements,
    version=__version__,
    packages=["autocord"],
    include_package_data=True,
    python_requires=">=3.7",
)
