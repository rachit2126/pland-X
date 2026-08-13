from setuptools import setup, find_packages

setup(
    name="mpp-parser",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "mpxj>=16.0.0",
        "jpype1>=1.5.0",
        "pydantic>=2.0.0",
        "fastapi>=0.100.0",
        "uvicorn[standard]>=0.20.0",
        "python-multipart>=0.0.6",
    ],
    entry_points={
        "console_scripts": [
            "mpp-parse=mpp_parser.cli:main",
            "mpp-export=mpp_parser.cli:main_export",
        ],
    },
)
