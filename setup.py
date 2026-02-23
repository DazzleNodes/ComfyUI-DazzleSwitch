from setuptools import setup, find_packages

setup(
    name="ComfyUI-DazzleSwitch",
    version="0.3.0",
    description="Smart switch node with dropdown-based input selection - Part of DazzleNodes",
    author="Dustin",
    author_email="6962246+djdarcy@users.noreply.github.com",
    url="https://github.com/DazzleNodes/ComfyUI-DazzleSwitch",
    packages=find_packages(),
    install_requires=[
        "torch",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
)
