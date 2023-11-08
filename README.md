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

Do note that, because an integral part of this program, [Magic Set Editor](https://magicseteditor.boards.net/), is Windows-only, Proxy League Helper only works on Windows as well. Sorry, Unix people!

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

# Customizing

If you're hosting your own proxy league, you should ensure that your specific league is unique! Parts of this program are made to be altered by you. The parts you'll need to change for your own league include:

* `cardback.png`: This the back of all your proxy league cards! There is a GIMP project file, `cardback.xcf`, if you need it. Make sure your card back is playing card sized (5:7 aspect ratio), and at least 300 dpi. Be sure to also label *VERY CLEARLY* that these cards are proxies, and are not for sale.
* `proxyleague.mse-symbol`: This is your league's set symbol, showing up on every card. It's a [Magic Set Editor](https://magicseteditor.boards.net/) set symbol, so pop it into MSE's set symbol editor to change it.

If you know what you're doing, you can also change the Magic Set Editor template for the cards, located in `MSE/data`. To change things like how rarities and packs are made, you'll need to dive into the code, located at `proxy_league_helper.py`.

# Contributing

This app is very VERY ***VERY*** much a work in progress. Please mind the dust. There is no easy installer, nor a GUI for this just yet. But if you want to contribute, feel free, and be sure to install [pre-commit](https://pre-commit.com/) in your local repository.
