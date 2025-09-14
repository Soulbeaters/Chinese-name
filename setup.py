# -*- coding: utf-8 -*-
"""
安装配置文件 / Setup Configuration File

ChineseNameProcessor - 中文姓名处理模块
用于ИСТИНА系统的中文姓名处理和验证
"""

from setuptools import setup, find_packages

with open("docs/README_ChineseNameProcessor.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="chinese-name-processor",
    version="2.0.0",
    author="Ma Jiaxin",
    author_email="ma.jiaxin@student.msu.ru",
    description="中文姓名处理和验证模块 - ИСТИНА系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.com/istina/chinese-name-processor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.7",
    install_requires=[
        # 核心依赖 / Core dependencies
    ],
    extras_require={
        "full": ["pypinyin>=0.44.0"],
        "dev": ["pytest>=6.0", "pytest-cov", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "chinese-name-processor=src.chinese_name_processor:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": ["*.json", "*.yml"],
    },
)