from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="proxy_league_helper",
    version="0.1.0",
    description="Generate Magic: the Gathering cards for Proxy Leagues",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/iconmaster5326/ProxyLeagueHelper",
    author="iconmaster5326",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="magic,mtg,proxy,proxyleague,proxy_league",
    py_modules=["proxy_league_helper"],
    python_requires=">=3.8, <4",
    install_requires=["requests", "Pillow", "console-menu"],
    extras_require={
        "dev": [],
        "test": [],
    },
    package_data={
        "proxy_league_helper": [
            "MSE",
            "autofill.exe",
            "cardback.png",
            "proxyleague.mse-symbol",
        ],
    },
    entry_points={
        "console_scripts": [
            "proxy_league_helper=proxy_league_helper:main",
        ],
    },
)
