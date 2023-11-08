import json
import math
import random
import typing
import os
import shutil
import requests
import re
import subprocess
import xml.etree.ElementTree as xml
import sys
import PIL.Image
import io
import argparse
import consolemenu

# I'm too lazy to call a finance API for this; update it whenever the card list changes
EUR_TO_USD = 1.07

# update this whenever the set of card types expands (which isn't often)
VALID_TYPES = (
    "Artifact",
    "Battle",
    "Conspiracy",
    "Creature",
    "Enchantment",
    "Instant",
    "Land",
    "Planeswalker",
    "Sorcery",
)

# filter out basic lands; we'll be handling these specially
INVALID_TYPES = ("Basic",)

# Filter out sets that are by definition not composed of legal cards
INVALID_SET_TYPES = (
    "memorabilia",
    "token",
    "minigame",
)

# Filter out UBs, for legal reasons (this (un?)fortunately also must hit all SLDs)
# To find these on Scryfall: is:ub -set:40k -set:ltc -set:who -set:sld -st:token -set:pip -set:ltr -set:pltr -set:bot -set:rex -set:pf23 -set:pw23
INVALID_SET_IDS = (
    "40k",
    "ltc",
    "who",
    "sld",
    "pip",
    "ltr",
    "pltr",
    "bot",
    "rex",
    "pf23",
    "pw23",
)

COLORS = "WUBRG"
COLOR_TO_BASIC_LAND = {
    "W": "Plains",
    "U": "Island",
    "B": "Swamp",
    "R": "Mountain",
    "G": "Forest",
}
SPECIAL_BASIC_LANDS = (
    "Snow-Covered Plains",
    "Snow-Covered Island",
    "Snow-Covered Swamp",
    "Snow-Covered Mountain",
    "Snow-Covered Forest",
    "Wastes",
)
BASIC_LAND_TO_COLOR = {
    "Plains": "W",
    "Island": "U",
    "Swamp": "B",
    "Mountain": "R",
    "Forest": "G",
    "Snow-Covered Plains": "W",
    "Snow-Covered Island": "U",
    "Snow-Covered Swamp": "B",
    "Snow-Covered Mountain": "R",
    "Snow-Covered Forest": "G",
    "Wastes": "C",
}
BASIC_LANDS = set(BASIC_LAND_TO_COLOR.keys())


class CardData:
    prices: typing.List[float]
    new_rarity: int
    raw_data: typing.List[typing.Dict[str, typing.Any]]

    def __init__(self) -> None:
        self.prices = []
        self.new_rarity = -1
        self.raw_data = []

    @property
    def printings(self):
        return len(self.raw_data)

    def name(self, face=None) -> str:
        return self.face(face)["name"]

    def typeline(self, face=None) -> str:
        return self.face(face)["type_line"]

    @property
    def color_id(self) -> str:
        return "".join(self.raw_data[0]["color_identity"])

    @property
    def old_rarities(self) -> typing.Set[str]:
        return set(c["rarity"] for c in self.raw_data if c.get("rarity"))

    @property
    def needs_snow(self) -> bool:
        return any(
            (card.get("mana_cost") and "{S}" in card["mana_cost"])
            or (card.get("oracle_text") and "{S}" in card["oracle_text"])
            for card in self.raw_data
        )

    @property
    def needs_colorless(self) -> bool:
        return any(
            card.get("mana_cost") and "{C}" in card["mana_cost"]
            for card in self.raw_data
        )

    def supertypes(self, face=None) -> typing.List[str]:
        types = self.typeline(face).split(" ")

        try:
            dash = types.index("—")
        except ValueError:
            return types

        return types[:dash]

    def subtypes(self, face=None) -> typing.List[str]:
        types = self.typeline(face).split(" ")

        try:
            dash = types.index("—")
        except ValueError:
            return []
        return types[dash + 1 :]

    @property
    def is_dfc(self):
        return any(
            ("card_faces" in printing and len(printing["card_faces"]) > 1)
            or printing["layout"] == "meld"
            for printing in self.raw_data
        )

    def face(
        self, face: typing.Union[int, None], n_printing: int = 0
    ) -> typing.Dict[str, typing.Any]:
        printing = self.raw_data[n_printing]
        if face is None or (face == 0 and printing["layout"] == "meld"):
            return printing
        elif face == 1 and printing["layout"] == "meld":
            part = next(
                iter(
                    p for p in printing["all_parts"] if p["component"] == "meld_result"
                )
            )
            return next(iter(c for c in cards if c["id"] == part["id"]))
        else:
            return printing["card_faces"][face]


# goal is: 71%, 21%, 6%, 0.8% (based on pack distribution)
BRACKETS = (0.25, 4.00, 40.00, math.inf)
# OR: 38%, 30%, 23%, 7% (based on set contents)
# BRACKETS = (0.05, 0.20, 2.50, math.inf)

BRACKET_NAMES = ("common", "uncommon", "rare", "mythic")
OLD_RARITIES = ("common", "uncommon", "rare", "mythic", "special")

cards: typing.List[typing.Dict[str, typing.Any]]
valid_cards: typing.Dict[str, CardData]
valid_basics: typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]]
cards_by_rarity: typing.List[typing.List[CardData]]


def parse_card_list():
    global cards, valid_cards, valid_basics, cards_by_rarity

    with open("cards.json", encoding="utf-8") as input_file:
        cards = json.load(input_file)

    valid_cards = {}
    valid_basics = {}
    for card in cards:
        if card["name"] in BASIC_LANDS:
            if card["set"] not in INVALID_SET_IDS and card["lang"] == "en":
                valid_basics.setdefault(card["name"], [])
                valid_basics[card["name"]].append(card)
            continue
        types = card.get("type_line", "").split(" ")
        prices: typing.List[float] = []
        if "prices" in card and card["prices"]:
            if "usd" in card["prices"] and card["prices"]["usd"]:
                prices.append(float(card["prices"]["usd"]))
            if "usd_foil" in card["prices"] and card["prices"]["usd_foil"]:
                prices.append(float(card["prices"]["usd_foil"]))
            if "usd_etched" in card["prices"] and card["prices"]["usd_etched"]:
                prices.append(float(card["prices"]["usd_etched"]))
            if "eur" in card["prices"] and card["prices"]["eur"]:
                prices.append(float(card["prices"]["eur"]) * EUR_TO_USD)
            if "eur_foil" in card["prices"] and card["prices"]["eur_foil"]:
                prices.append(float(card["prices"]["eur_foil"]) * EUR_TO_USD)
            if "eur_etched" in card["prices"] and card["prices"]["eur_etched"]:
                prices.append(float(card["prices"]["eur_etched"]) * EUR_TO_USD)
        if (
            len(prices) > 0
            and any((t in types) for t in VALID_TYPES)
            and not any((t in types) for t in INVALID_TYPES)
            and card["set_type"] not in INVALID_SET_TYPES
            and not card["oversized"]
            and not all(
                legality == "not_legal" for legality in card["legalities"].values()
            )
            and card["set"] not in INVALID_SET_IDS
            and "playing for ante" not in card.get("oracle_text", "")
        ):
            valid_cards.setdefault(
                card["oracle_id"],
                CardData(),
            )
            card_data = valid_cards[card["oracle_id"]]
            card_data.raw_data.append(card)
            card_data.prices += prices

    last_bracket = 0
    cards_by_rarity = []
    i = 0
    for bracket in BRACKETS:
        cards_by_rarity.append(
            [
                card
                for card in valid_cards.values()
                if min(card.prices) > last_bracket and min(card.prices) <= bracket
            ]
        )
        for card in cards_by_rarity[-1]:
            card.new_rarity = i
        i += 1
        last_bracket = bracket


class SealedProduct:
    contents: typing.List[CardData]
    basics: typing.Dict[str, int]

    def __init__(
        self, contents: typing.List[CardData], basics: typing.Dict[str, int]
    ) -> None:
        self.contents = contents
        self.basics = basics

    def __len__(self) -> int:
        return len(self.contents) + sum(n for n in self.basics.values())


PACK_TOTAL = 15


def make_pack() -> SealedProduct:
    pack_rarities = [0] * 10 + [1] * 3 + [3 if random.random() < 1 / 8.0 else 2]
    pack: typing.List[CardData] = []
    for rarity in pack_rarities:
        pack.append(random.choice(cards_by_rarity[rarity]))
    if random.random() < 1 / 8.0:
        basic_land = random.choice(SPECIAL_BASIC_LANDS)
    else:
        basic_land = random.choice(list(COLOR_TO_BASIC_LAND.values()))
    return SealedProduct(pack, {basic_land: 1})


DECK_TOTAL = 60
DECK_BASICS = 25
DECK_RARITIES = [0] * 20 + [1] * 12 + [2] * 3 + [3] * 0
DECK_CREATURE_NONCREATURE = (
    [True] * 14 + [False] * 6 + [True] * 8 + [False] * 4 + [None] * 3
)


def make_deck() -> SealedProduct:
    color1 = random.choice(COLORS)
    color2 = random.choice(COLORS)
    color_id = "".join(sorted(set(color1 + color2)))

    pack: typing.List[CardData] = []
    basics: typing.Dict[str, int] = {}
    deck_valid_cards = [
        c
        for c in valid_cards.values()
        if "Land" not in c.supertypes()
        and "Conspiracy" not in c.supertypes()
        and "".join(sorted(c.color_id)) in color_id
    ]
    deck_valid_noncreature_cards = [
        c for c in deck_valid_cards if "Creature" not in c.supertypes()
    ]
    deck_valid_creature_cards = [
        c for c in deck_valid_cards if "Creature" in c.supertypes()
    ]

    for (rarity, creature) in zip(DECK_RARITIES, DECK_CREATURE_NONCREATURE):
        pool = deck_valid_cards
        if creature is True:
            pool = deck_valid_creature_cards
        if creature is False:
            pool = deck_valid_noncreature_cards
        pack.append(random.choice([c for c in pool if c.new_rarity == rarity]))

    total_basics = DECK_BASICS
    if any(c.needs_snow for c in pack):
        total_basics -= 2
        land1 = f"Snow-Covered {COLOR_TO_BASIC_LAND[color1]}"
        basics.setdefault(land1, 0)
        basics[land1] += 1
        land2 = f"Snow-Covered {COLOR_TO_BASIC_LAND[color2]}"
        basics.setdefault(land2, 0)
        basics[land2] += 1
    if any(c.needs_colorless for c in pack):
        total_basics -= 2
        basics["Wastes"] = 2

    n_color1 = sum(
        sum(1 for color in c.color_id if color == color1)
        for c in pack
        if "".join(sorted(c.color_id)) in color1
    )
    n_color2 = sum(
        sum(1 for color in c.color_id if color == color2)
        for c in pack
        if "".join(sorted(c.color_id)) in color2
    )
    n_colored = n_color1 + n_color2

    land1 = COLOR_TO_BASIC_LAND[color1]
    basics.setdefault(land1, 0)
    basics[land1] += math.ceil(total_basics * (n_color1 / n_colored))
    land2 = COLOR_TO_BASIC_LAND[color2]
    basics.setdefault(land2, 0)
    basics[land2] += math.floor(total_basics * (n_color2 / n_colored))

    return SealedProduct(pack, basics)


SET_TEMPLATE = """mse_version: 2.0.2
game: magic
game_version: 2020-04-25
stylesheet: old
stylesheet_version: 2023-02-13
set_info:
	copyright: PROXY — NOT FOR SALE
	set_code: PL
	symbol: proxyleague.mse-symbol
styling:
	magic-old:
		text_box_mana_symbols: magic-mana-small.mse-symbol-font
		alpha_style_blending: no
		pt_font: MPlantin-Bold
		colored_nonbasic_land_trim: trim, textbox
version_control:
	type: none
"""

CARD_TEMPLATE = """mse_version: 2.1.2
card:
	has_styling: false
	extra_data:
		magic-old:
			list_icon: no icon
	name: @NAME@
	casting_cost: @COST@
	card_symbol: none
	image: @IMAGE@
	super_type: @SUPERTYPE@
	sub_type: @SUBTYPE@
	rarity: @RARITY@
	rule_text:
		@RULES@
	flavor_text:
		@FLAVOR@
	power: @POWER@
	toughness: @TOUGHNESS@
	illustrator: Illus. @ARTIST@
	copyright: PROXY — NOT FOR SALE
	index: @INDEX@
"""

BASIC_LAND_TEMPLATE = """mse_version: 2.1.2
card:
	has_styling: false
	extra_data:
		magic-old:
			list_icon: no icon
	name: @NAME@
	card_symbol: none
	image: @IMAGE@
	super_type: @SUPERTYPE@
	sub_type: @SUBTYPE@
	rarity: basic land
	illustrator: Illus. @ARTIST@
	copyright: PROXY — NOT FOR SALE
	index: @INDEX@
	watermark: mana symbol @SYMBOL@
"""

MSE_RARITIES = ("common", "uncommon", "rare", "mythic rare")
COLORS_TO_CARD_BACKS = {
    "W": "white",
    "U": "blue",
    "B": "black",
    "R": "red",
    "G": "green",
    "C": "",
}
COLORS_TO_WATERMARKS = {
    "W": "white",
    "U": "blue",
    "B": "black",
    "R": "red",
    "G": "green",
    "C": "colorless",
}

MSE_SET_SYMBOL_FILENAME = "proxyleague.mse-symbol"
MSE_PATH = "MSE/magicseteditor.com"
IMAGE_FORMAT = "{card.index}.png"


def mse_format_symbols(s: str) -> str:
    def symfmt(m: re.Match) -> str:
        sym = m.group(1)
        result = sym
        if sym == "TK":
            result = "D"  # TODO: handle this when Unfinity support is added to MSE
        if sym == "CHAOS":
            result = "A"
        if sym == "P":
            result = "H"
        if re.match(r"[^/]+/P", sym) or re.match(r"[^/]+/[^/]+/P", sym):
            result = f"H/{sym[:-2]}"
        if re.match(r"\d\d+", sym):
            result = f"[{sym}]"
        return "{" + result + "}"

    return re.sub(r"{([^}]*)}", symfmt, s)


def mse_format_mana_cost(s: str) -> str:
    return mse_format_symbols(s).replace("{", "").replace("}", "")


def mse_format_rules(card: CardData, face, s: str) -> str:
    if not s:
        return s
    result = (
        "<kw-0>"
        + mse_format_symbols(s)
        .replace("\n", "\n\t\t")
        .replace("{", "<sym>")
        .replace("}", "</sym>")
        .replace("(", "<i>(")
        .replace(")", ")</i>")
        + "</kw-0>"
    )
    if "Planeswalker" in card.supertypes(face):
        result = re.sub(
            r"\+(\d+|[XYZ]): ", lambda m: f"<sym>+{m.group(1)}</sym>: ", result
        )
        result = re.sub(
            r"[\-−](\d+|[XYZ]): ", lambda m: f"<sym>-{m.group(1)}</sym>: ", result
        )
        result = re.sub(
            r"=(\d+|[XYZ]): ", lambda m: f"<sym>={m.group(1)}</sym>: ", result
        )
        result = re.sub(r"0: ", lambda m: f"<sym>+0</sym>: ", result)
    if "Saga" in card.subtypes(face):
        result = re.sub(r"\b[IVX]+", lambda m: f"<no-sym>{m.group(0)}</no-sym>", result)
    return result


def mse_format_flavor(s: str) -> str:
    if not s:
        return s
    return "<i-flavor>" + s.replace("\n", "\n\t\t") + "</i-flavor>"


CARD_ART_WIDTH = 286
CARD_ART_HEIGHT = 233
CARD_ART_RATIO = float(CARD_ART_WIDTH) / float(CARD_ART_HEIGHT)


def mse_download_card_image(output_dir: str, i: int, printing, face, face_data):
    image_filename = ""

    image_url = None
    if "image_uris" in face_data and "art_crop" in face_data["image_uris"]:
        image_url = face_data["image_uris"]["art_crop"]
    elif "image_uris" in printing and "art_crop" in printing["image_uris"]:
        image_url = printing["image_uris"]["art_crop"]

    if image_url:
        response = requests.get(image_url)
        if response.ok:
            # open image
            image = PIL.Image.open(io.BytesIO(response.content))
            # if split, then pick the right half-image
            if printing["layout"] == "split":
                if face is None or face == 0:
                    resize = (0, 0, image.width // 2, image.height)
                else:
                    resize = (image.width // 2, 0, image.width, image.height)
                image = image.crop(resize)
            # flip around the back half of a flip card
            if printing["layout"] == "flip" and face == 1:
                image = image.transpose(PIL.Image.ROTATE_180)
            # fit to aspect ratio
            ratio = float(image.width) / float(image.height)
            if ratio > CARD_ART_RATIO:
                # crop the left and right
                new_width = int(CARD_ART_RATIO * image.height)
                offset = int((image.width - new_width) / 2)
                resize = (offset, 0, image.width - offset, image.height)
            else:
                # crop the top and bottom
                new_height = int(image.width / CARD_ART_RATIO)
                offset = int((image.height - new_height) / 2)
                resize = (0, offset, image.width, image.height - offset)
            image = image.crop(resize)
            # save image
            image_filename = f"image {i} {face or 0}"
            with open(os.path.join(output_dir, image_filename), "wb") as image_file:
                image.save(image_file, format="PNG")

    return image_filename


def mse_gen_card(output_dir: str, i: int, card: CardData, printing, face, face_data):
    image_filename = mse_download_card_image(output_dir, i, printing, face, face_data)

    with open(
        os.path.join(output_dir, f"card {i} {face or 0}"), "w", encoding="utf-8"
    ) as card_file:
        power = face_data.get("power", "")
        if "Planeswalker" in card.supertypes(face):
            power = face_data.get("loyalty", "")
        if "Battle" in card.supertypes(face):
            power = face_data.get("defense", "")

        card_file.write(
            CARD_TEMPLATE.replace("@NAME@", card.name(face))
            .replace("@COST@", mse_format_mana_cost(face_data.get("mana_cost", "")))
            .replace(
                "@SUPERTYPE@",
                " ".join(
                    f"<word-list-type>{t}</word-list-type>"
                    for t in card.supertypes(face)
                ),
            )
            .replace(
                "@SUBTYPE@",
                " ".join(
                    f"<word-list-type>{t}</word-list-type>" for t in card.subtypes(face)
                ),
            )
            .replace("@RARITY@", MSE_RARITIES[card.new_rarity])
            .replace("@POWER@", power)
            .replace("@TOUGHNESS@", face_data.get("toughness", ""))
            .replace(
                "@ARTIST@", face_data.get("artist", printing.get("artist", "Unknown"))
            )
            .replace("@IMAGE@", image_filename)
            .replace(
                "@RULES@",
                mse_format_rules(card, face, face_data.get("oracle_text", "")),
            )
            .replace("@FLAVOR@", mse_format_flavor(face_data.get("flavor_text", "")))
            .replace("@INDEX@", str(i))
        )
        if (
            "color_indicator" in face_data
            and face_data["color_indicator"]
            and "Artifact" not in card.supertypes(face)
            and "Land" not in card.supertypes(face)
        ):
            color = "multicolor"
            if len(face_data["color_indicator"]) == 1:
                color = COLORS_TO_CARD_BACKS[face_data["color_indicator"][0]]
            card_file.write(f"\tcard_color: {color}\n")


def mse_gen_basic_land(output_dir: str, i: int, printing):
    image_filename = mse_download_card_image(output_dir, i, printing, None, printing)

    with open(
        os.path.join(output_dir, f"card {i} 0"), "w", encoding="utf-8"
    ) as card_file:
        types = printing["type_line"].split("—")
        supertypes = types[0].strip().split(" ")
        subtypes = []
        if len(types) > 1:
            subtypes = types[1].strip().split(" ")
        card_file.write(
            BASIC_LAND_TEMPLATE.replace("@NAME@", printing["name"])
            .replace(
                "@SUPERTYPE@",
                " ".join(f"<word-list-type>{t}</word-list-type>" for t in supertypes),
            )
            .replace(
                "@SUBTYPE@",
                " ".join(f"<word-list-type>{t}</word-list-type>" for t in subtypes),
            )
            .replace("@ARTIST@", printing.get("artist", "Unknown"))
            .replace("@IMAGE@", image_filename)
            .replace("@INDEX@", str(i))
            .replace(
                "@SYMBOL@", COLORS_TO_WATERMARKS[BASIC_LAND_TO_COLOR[printing["name"]]]
            )
        )


def mse_gen_set(output_dir: str, *packs: SealedProduct):
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.mkdir(output_dir)

    shutil.copy(
        MSE_SET_SYMBOL_FILENAME, os.path.join(output_dir, MSE_SET_SYMBOL_FILENAME)
    )

    with open(os.path.join(output_dir, "set"), "w", encoding="utf-8") as set_file:
        set_file.write(SET_TEMPLATE)
        i = 0
        for pack in packs:
            for basic, n_basics in pack.basics.items():
                for _ in range(n_basics):
                    set_file.write(f"include_file: card {i} 0\n")
                    mse_gen_basic_land(
                        output_dir, i, random.choice(valid_basics[basic])
                    )
                    i += 1

            for card in pack.contents:
                set_file.write(f"include_file: card {i} 0\n")
                if card.is_dfc:
                    set_file.write(f"include_file: card {i} 1\n")

                printing = random.choice(
                    [c for c in card.raw_data if c["lang"] == "en"]
                )
                if card.is_dfc:
                    mse_gen_card(
                        output_dir,
                        i,
                        card,
                        printing,
                        0,
                        card.face(0, card.raw_data.index(printing)),
                    )
                    mse_gen_card(
                        output_dir,
                        i,
                        card,
                        printing,
                        1,
                        card.face(1, card.raw_data.index(printing)),
                    )
                else:
                    mse_gen_card(output_dir, i, card, printing, None, printing)

                i += 1


def mse_gen_card_images(output_dir: str) -> typing.List[str]:
    subprocess.run(
        [
            MSE_PATH,
            "--export-images",
            os.path.join(output_dir, "set"),
            os.path.join(output_dir, IMAGE_FORMAT),
        ],
        stdin=subprocess.DEVNULL,
        stdout=sys.stdout,
        stderr=sys.stderr,
        check=True,
    )

    for card_image_filename in (
        f for f in os.listdir(output_dir) if f.endswith(".png")
    ):
        input_image_path = os.path.join(output_dir, card_image_filename)
        input_image = PIL.Image.open(input_image_path)
        output_image = PIL.Image.new(
            input_image.mode,
            (int(input_image.width * 1.1), int(input_image.height * 1.072)),
        )
        output_image.paste("#000000", (0, 0, output_image.width, output_image.height))
        output_image.paste(
            input_image,
            (
                int((output_image.width - input_image.width) / 2),
                int((output_image.height - input_image.height) / 2),
            ),
        )
        output_image.save(input_image_path)

    return [
        os.path.join(output_dir, f)
        for f in os.listdir(output_dir)
        if f.endswith(".png")
    ]


def mse_gen_card_image_sheets(
    image_filepaths: typing.List[str], images_per_sheet: int
) -> typing.Iterable[PIL.Image.Image]:
    sq_n = math.sqrt(images_per_sheet)
    for factor in range(int(sq_n), int(sq_n) // 2, -1):
        other_factor = images_per_sheet // factor
        if int(other_factor) == other_factor:
            sheet_rows = factor
            sheet_cols = int(other_factor)
            break
    else:
        sheet_rows = int(math.ceil(sq_n))
        sheet_cols = int(math.ceil(sq_n))

    card_size = PIL.Image.open(image_filepaths[0]).size

    def make_sheet():
        return PIL.Image.new(
            "RGBA", (card_size[0] * sheet_cols, card_size[1] * sheet_rows)
        )

    sheet_image = make_sheet()
    n_cards = 0
    row = 0
    col = 0
    for image_filepath in image_filepaths:
        sheet_image.paste(
            PIL.Image.open(image_filepath), (col * card_size[0], row * card_size[1])
        )
        n_cards += 1
        col += 1
        if col >= sheet_cols:
            row += 1
            col = 0
        if n_cards >= images_per_sheet:
            yield sheet_image
            sheet_image = make_sheet()
            n_cards = row = col = 0


CARDBACK_FILEPATH = "cardback.png"
MPC_XML_FILENAME = "order.xml"
MPC_BRACKETS = (
    18,
    36,
    55,
    72,
    90,
    108,
    126,
    144,
    162,
    180,
    198,
    216,
    234,
    396,
    504,
    612,
)


class TooManyCardsException(Exception):
    def __init__(self, got: int, maximum: int) -> None:
        super().__init__(f"Too many cards: {got} > {maximum}")
        self.got = got
        self.maximum = maximum


def mpc_gen_orders(
    mse_output_dir: str, *packs: SealedProduct, bracket=None
) -> typing.Iterable[str]:
    result = []
    for i, orderset in enumerate(split_packs(packs, bracket or MPC_BRACKETS[-1])):
        order_filepath = os.path.join(mse_output_dir, f"order{i+1}.xml")
        mpc_gen_order(mse_output_dir, order_filepath, *orderset)
        result.append(order_filepath)
    return result


def mpc_gen_order(mse_output_dir: str, mpc_output_filepath: str, *packs: SealedProduct):
    n_cards = sum(len(pack) for pack in packs)
    if n_cards > MPC_BRACKETS[-1]:
        raise TooManyCardsException(n_cards, MPC_BRACKETS[-1])
    mpc_order = xml.Element("order")
    mpc_details = xml.SubElement(mpc_order, "details")
    xml.SubElement(mpc_details, "quantity").text = str(n_cards)
    xml.SubElement(mpc_details, "bracket").text = str(
        [b for b in MPC_BRACKETS if b >= n_cards][0]
    )
    # xml.SubElement(mpc_details, "stock").text = "(S27) Smooth" # TODO: whenever MPCFill get support...
    xml.SubElement(mpc_details, "stock").text = "(S30) Standard Smooth"
    xml.SubElement(mpc_details, "foil").text = "false"
    mpc_fronts = xml.SubElement(mpc_order, "fronts")
    mpc_backs = xml.SubElement(mpc_order, "backs")
    xml.SubElement(mpc_order, "cardback").text = os.path.abspath(CARDBACK_FILEPATH)

    def mpc_add_card(i, face):
        card = xml.SubElement(mpc_fronts if face == 0 else mpc_backs, "card")
        xml.SubElement(card, "id").text = os.path.abspath(
            os.path.join(mse_output_dir, f"{i}.png" if face == 0 else f"{i}.1.png")
        )
        xml.SubElement(card, "slots").text = str(i)

    i = 0
    for pack in packs:
        for n_basic in pack.basics.values():
            for _ in range(n_basic):
                mpc_add_card(i, 0)
                i += 1
        for card in pack.contents:
            mpc_add_card(i, 0)
            if card.is_dfc:
                mpc_add_card(i, 1)
            i += 1

    with open(mpc_output_filepath, "wb") as mpc_file:
        xml.ElementTree(mpc_order).write(mpc_file, encoding="utf-8")


def mpc_fulfill_order(order_filepath: str):
    if os.path.exists(MPC_XML_FILENAME) and os.path.abspath(
        order_filepath
    ) != os.path.abspath(MPC_XML_FILENAME):
        raise IOError("Already an XML present; would destroy!")
    shutil.copy(order_filepath, MPC_XML_FILENAME)
    try:
        subprocess.run(
            "./autofill",
            input=b"\n\n\nn\n\n\n",
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=True,
        )
    finally:
        if os.path.abspath(order_filepath) != os.path.abspath(MPC_XML_FILENAME):
            os.remove(MPC_XML_FILENAME)


def mpc_merge_orders(orders: typing.Iterable[str], output_filepath: str):
    order_xmls = [xml.parse(order) for order in orders]
    order_qtys = [int(o.find("details").find("quantity").text) for o in order_xmls]
    n_cards = sum(order_qtys)
    if n_cards > MPC_BRACKETS[-1]:
        raise TooManyCardsException(n_cards, MPC_BRACKETS[-1])

    mpc_order = xml.Element("order")
    mpc_details = xml.SubElement(mpc_order, "details")
    mpc_fronts = xml.SubElement(mpc_order, "fronts")
    mpc_backs = xml.SubElement(mpc_order, "backs")
    xml.SubElement(mpc_order, "cardback").text = os.path.abspath(CARDBACK_FILEPATH)

    def card_index(order_index: int, card_index: int) -> int:
        return sum(order_qtys[:order_index]) + card_index

    def mpc_add_card(where: xml.Element, order_index: int, old_card: xml.Element):
        old_card_index = int(old_card.find("slots").text)
        new_card_index = card_index(order_index, old_card_index)
        card = xml.SubElement(where, "card")
        xml.SubElement(card, "id").text = old_card.find("id").text
        xml.SubElement(card, "slots").text = str(new_card_index)

    for i, order in enumerate(order_xmls):
        for card in order.find("fronts").findall("card"):
            mpc_add_card(mpc_fronts, i, card)
        for card in order.find("backs").findall("card"):
            mpc_add_card(mpc_backs, i, card)

    xml.SubElement(mpc_details, "quantity").text = str(n_cards)
    xml.SubElement(mpc_details, "bracket").text = str(
        [b for b in MPC_BRACKETS if b >= n_cards][0]
    )
    # xml.SubElement(mpc_details, "stock").text = "(S27) Smooth" # TODO: whenever MPCFill get support...
    xml.SubElement(mpc_details, "stock").text = "(S30) Standard Smooth"
    xml.SubElement(mpc_details, "foil").text = "false"

    with open(output_filepath, "wb") as mpc_file:
        xml.ElementTree(mpc_order).write(mpc_file, encoding="utf-8")


def to_decklist(pack: SealedProduct) -> str:
    result = ""
    for card in pack.contents:
        result += f"1 {card.name()}\n"
    for basic, n in pack.basics.items():
        result += f"{n} {basic}\n"
    return result


class CardNotFoundException(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Card not found: {name}")
        self.name = name


BASIC_LANDS_LOWERCASE = {n.lower(): n for n in BASIC_LANDS}


def from_decklist(decklist: str) -> SealedProduct:
    result = SealedProduct([], {})
    for line in decklist.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        qty_str = re.match(r"\d+", line)
        if qty_str:
            qty = int(qty_str.group())
        else:
            qty = 1
        card_name = re.match(r"(\d+\s+)?(.*)", line).group(2).strip().lower()
        if card_name in BASIC_LANDS_LOWERCASE.keys():
            fixed_card_name = BASIC_LANDS_LOWERCASE[card_name]
            result.basics.setdefault(fixed_card_name, 0)
            result.basics[fixed_card_name] += qty
        else:
            for _ in range(qty):
                matches = [
                    c for c in valid_cards.values() if c.name().lower() == card_name
                ]
                if matches:
                    result.contents.append(matches[0])
                else:
                    raise CardNotFoundException(card_name)
    return result


def make_basic_land_bundle(n_each_land: int) -> SealedProduct:
    return SealedProduct(
        [], {name: n_each_land for name in COLOR_TO_BASIC_LAND.values()}
    )


def split_packs(
    packs: typing.Iterable[SealedProduct], chunk_size: int
) -> typing.Iterable[typing.List[SealedProduct]]:
    result = []
    size = 0
    for pack in packs:
        pack_size = len(pack)
        if pack_size > chunk_size:
            raise TooManyCardsException(pack_size, chunk_size)
        if result and size + pack_size > chunk_size:
            yield result
            result = []
            size = 0
        result.append(pack)
        size += pack_size
    if result:
        yield result


def main(argv: typing.List[str]) -> int:
    parser = argparse.ArgumentParser(
        argv[0], description="generates Proxy League cards"
    )
    args = parser.parse_args(argv[1:])
    print("Loading card list... ", end="", flush=True)
    parse_card_list()
    print("done.")
    show_main_menu(args)
    return 0


def show_main_menu(args: argparse.Namespace):
    menu = consolemenu.ConsoleMenu("Welcome to the Proxy League Helper!")
    menu.append_item(
        consolemenu.items.FunctionItem("Generate cards", show_pack_menu, [args])
    )
    menu.append_item(consolemenu.items.FunctionItem("Show statistics", lambda: None))
    menu.show()


def show_pack_menu(args: argparse.Namespace):
    generating = ""
    packs: typing.List[SealedProduct] = []

    def add_pack():
        nonlocal generating, packs
        n_str = input("How many packs? ")
        try:
            n = int(n_str)
        except Exception:
            return
        generating += f"{', ' if generating else ''}{n} packs"
        for _ in range(n):
            packs.append(make_pack())

    def add_deck():
        nonlocal generating, packs
        n_str = input("How many decks? ")
        try:
            n = int(n_str)
        except Exception:
            return
        generating += f"{', ' if generating else ''}{n} decks"
        for _ in range(n):
            packs.append(make_deck())

    def add_basics():
        nonlocal generating, packs
        print("How many of each basic land? ", end="")
        n_str = input()
        try:
            n = int(n_str)
        except Exception:
            return
        generating += f"{', ' if generating else ''}{n*5}-card basic land bundle"
        packs.append(make_basic_land_bundle(n))

    def add_custom():
        nonlocal generating, packs
        path = input("What is the filesystem path to your decklist? ")
        if not path:
            return
        with open(path, encoding="utf-8") as decklist_file:
            pack = from_decklist(decklist_file.read())
        generating += f"{', ' if generating else ''}{len(pack)}-card decklist ({os.path.basename(path)})"
        packs.append(pack)

    menu = consolemenu.ConsoleMenu(
        "What would you like to generate?",
        lambda: f"About to generate: {generating}\nTotal cards: {sum(len(pack) for pack in packs)}",
        exit_option_text="Cancel",
    )
    menu.append_item(consolemenu.items.FunctionItem("Booster packs", add_pack))
    menu.append_item(consolemenu.items.FunctionItem("Starter decks", add_deck))
    menu.append_item(consolemenu.items.FunctionItem("Basic land bundle", add_basics))
    menu.append_item(
        consolemenu.items.FunctionItem("Custom (from decklist)", add_custom)
    )
    menu.append_item(
        consolemenu.items.FunctionItem("Confirm", show_packs_output_menu, [args, packs])
    )
    menu.show()


def show_packs_output_menu(args: argparse.Namespace, packs: typing.List[SealedProduct]):
    def decklist_console():
        for pack in packs:
            print(to_decklist(pack))
        input("(press ENTER to continue)")

    def decklist_file():
        path = input("What is the path to where you want the file? ")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as file:
            for pack in packs:
                file.write(to_decklist(pack))
        print("Decklist written.")
        input("(press ENTER to continue)")

    def mse():
        path = input("What is the path to where you want the MSE set directory? ")
        if not path:
            return
        mse_gen_set(path, *packs)
        print("MSE set generated.")
        input("(press ENTER to continue)")

    def images():
        path = input("What is the path to where you want the MSE set directory? ")
        if not path:
            return
        mse_gen_set(path, *packs)
        print("MSE set generated.")
        mse_gen_card_images(path)
        print("Images generated into MSE set directory.")
        input("(press ENTER to continue)")

    def images_sheets():
        path = input("What is the path to where you want the MSE set directory? ")
        if not path:
            return
        n_cards = sum(len(p) for p in packs)
        ips: int = None
        while ips is None:
            ips_str = input(
                f"How many images do you want per sheet? (default is {n_cards}) "
            )
            if not ips_str:
                ips = n_cards
            else:
                try:
                    ips = int(ips_str)
                except Exception:
                    pass
        mse_gen_set(path, *packs)
        print("MSE set generated.")
        images = mse_gen_card_images(path)
        print("Images generated into MSE set directory.")
        for i, image in enumerate(mse_gen_card_image_sheets(images, ips)):
            image.save(os.path.join(path, f"sheet{i+1}.png"))
        for image in images:
            os.remove(image)
        print("Image sheets generated into MSE set directory.")
        input("(press ENTER to continue)")

    def mpc():
        path = input("What is the path to where you want the MSE set directory? ")
        if not path:
            return
        mse_gen_set(path, *packs)
        print("MSE set generated.")
        mse_gen_card_images(path)
        print("Images generated into MSE set directory.")
        mpc_gen_orders(path, *packs)
        print("MPC order XMLs generated into MSE set directory.")
        print(
            "To upload using MPCFill manually: Copy the XMLs into the Proxy League Helper directory and run autofill."
        )
        input("(press ENTER to continue)")

    def mpc_autofill():
        path = input("What is the path to where you want the MSE set directory? ")
        if not path:
            return
        mse_gen_set(path, *packs)
        print("MSE set generated.")
        mse_gen_card_images(path)
        print("Images generated into MSE set directory.")
        orders = mpc_gen_orders(path, *packs)
        print("MPC order XMLs generated into MSE set directory.")
        for i, order in enumerate(orders):
            print(f"Generating order {i+1}...")
            mpc_fulfill_order(order)
            input(
                "Finish filling out the fields and add to cart in the provided browser, then press ENTER here."
            )
        print("MPC order complete.")
        input("(press ENTER to continue)")

    menu = consolemenu.ConsoleMenu(
        "How would you like your cards?",
        lambda: f"Total cards: {sum(len(pack) for pack in packs)}",
        exit_option_text="Back",
    )
    menu.append_item(
        consolemenu.items.FunctionItem("Decklist (to console)", decklist_console)
    )
    menu.append_item(
        consolemenu.items.FunctionItem("Decklist (to file)", decklist_file)
    )
    menu.append_item(consolemenu.items.FunctionItem("Magic Set Editor project", mse))
    menu.append_item(
        consolemenu.items.FunctionItem("MSE project + card images (individual)", images)
    )
    menu.append_item(
        consolemenu.items.FunctionItem(
            "MSE project + card images (sheets)", images_sheets
        )
    )
    menu.append_item(
        consolemenu.items.FunctionItem(
            "MSE project + images + MakePlayingCards order", mpc
        )
    )
    menu.append_item(
        consolemenu.items.FunctionItem(
            "MSE project + images + MPC order + autofill via MPCFill", mpc_autofill
        )
    )
    menu.show()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
