# -*- coding: utf-8 -*-

import setuptools

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    requirements=requirements,
)
