#!/usr/bin/env python3
"""
WhatNote V2 项目安装配置
"""

from setuptools import setup, find_packages

setup(
    name="whatnote_v2",
    version="2.0.0",
    description="WhatNote V2 - 基于真实文件系统的笔记软件",
    author="WhatNote Team",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "websockets>=12.0",
        "python-multipart>=0.0.6",
        "requests>=2.31.0",
    ],
    package_data={
        "": ["*.json", "*.md"],
    },
) 