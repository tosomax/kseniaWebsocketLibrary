from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="kseniaWebsocketUtil",
    version="0.0.2",
    author="realnot16",
    author_email="benedetto.padula@gmail.com",
    description="a simple websocket utility to communicate with lares units",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/realnot16/kseniaWebsocketUtil",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
