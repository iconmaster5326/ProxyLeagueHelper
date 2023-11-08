import os
import pathlib

import setuptools
import setuptools.command.build_py
import setuptools.command.install
import setuptools.command.sdist

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")


def download_deps():
    import requests

    def download(src: str, dest: str):
        if not os.path.exists(dest):
            print(f"downloading {dest}...")
            response = requests.get(src)
            if not response.ok:
                response.raise_for_status()
            with open(dest, "wb") as file:
                file.write(response.content)

    download(
        "https://github.com/MagicSetEditorPacks/Full-Magic-Pack/raw/main/magicseteditor.com",
        "MSE/magicseteditor.com",
    )
    download(
        "https://github.com/MagicSetEditorPacks/Full-Magic-Pack/raw/main/magicseteditor.exe",
        "MSE/magicseteditor.exe",
    )
    download(
        "https://github.com/chilli-axe/mpc-autofill/releases/download/v4.4/autofill-windows.exe",
        "autofill.exe",
    )


class install(setuptools.command.install.install):
    def run(self):
        setuptools.command.install.install.run(self)
        download_deps()


class sdist(setuptools.command.sdist.sdist):
    def run(self):
        setuptools.command.sdist.sdist.run(self)
        download_deps()


class build_py(setuptools.command.build_py.build_py):
    def run(self):
        setuptools.command.build_py.build_py.run(self)
        download_deps()


setuptools.setup(
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
        "dev": ["pre-commit"],
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
    cmdclass={"install": install, "sdist": sdist, "build_py": build_py},
)
