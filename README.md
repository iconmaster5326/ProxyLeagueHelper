# Proxy League Helper

This is the tool used to generate cards for hosting your own Magic: the Gathering Proxy League.

# [What's a Proxy League, you ask? Read more here!](https://docs.google.com/document/d/1lW8ouYNFoHTqrP0ogB5bgt-c33Mkn15caEYqEG1StaE/edit?usp=sharing)

# Installation

You'll need [Python](https://www.python.org/downloads/) to run this. You'll also need some very basic knowledge of how to use command line applications. Once you have Python, it is a simple matter of installing the package, with some simple command line steps:

```bash
python -m pip install -e .
python setup.py build
```

And then running it is as simple as running this command:

```bash
proxy_league_helper
```

# Usage

You should be given a user interface in your terminal that allows you to generate cards, among other things. You have several options for what to make:

* Booster packs
* Starter decks
* Basic land bundles
* Imported decklists

From there, you can generate the following:

* decklists (for online tabletop use, etc)
* [Magic Set Editor](https://magicseteditor.boards.net/) projects
* Card images
* [MPCFill](https://mpcfill.com/) order forms, for use in [MakePlayingCards](https://www.makeplayingcards.com/)

# Contributing

This app is very VERY ***VERY*** much a work in progress. Please mind the dust. There is no easy installer, nor a GUI for this just yet. But if you want to contribute, feel free, and be sure to install [pre-commit](https://pre-commit.com/) in your local repository.
