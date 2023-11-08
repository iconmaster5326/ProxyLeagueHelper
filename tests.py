from proxy_league_helper import *

parse_card_list()

print(f"Valid cards: {len(valid_cards)}")
print(f"Valid printings: {sum(c.printings for c in valid_cards.values())}")

# for card in valid_cards.values():
#     if all(c > 1000 for c in card.prices):
#         print(
#             f"{card.name()} - MIN ${min(card.prices):.2f} AVG ${sum(card.prices)/len(card.prices):.2f} MAX ${max(card.prices):.2f}"
#         )

last_bracket = 0
for i, bracket in enumerate(BRACKETS):
    n_in_bracket = 0
    for card in valid_cards.values():
        price = min(card.prices)
        if price > last_bracket and price <= bracket:
            n_in_bracket += 1
    print(
        f"cards in bracket '{BRACKET_NAMES[i]}': {n_in_bracket} ({(n_in_bracket/len(valid_cards))*100:.2f}%)"
    )
    last_bracket = bracket

# for card in valid_cards.values():
#     last_bracket = 0
#     i = 0
#     for bracket in BRACKETS:
#         price = min(card.prices)
#         if price > last_bracket and price <= bracket:
#             print(f"{card.name()}: {price:.2f} ({BRACKET_NAMES[i]})")
#         i += 1
#         last_bracket = bracket

# for i in range(1):
#     pack = make_pack()
#     # print(f"pack {i+1}:")
#     # print(f"\tbasic - {basic_land}")
#     print(f"1 {pack.basic}")
#     for i, c in enumerate(pack.contents):
#         # print(f"\t{BRACKET_NAMES[pack_rarities[i]]} - {c.name()} ({min(c.prices):.2f})")
#         print(f"1 {c.name()}")

for rarity in range(4):
    print(f"{BRACKET_NAMES[rarity]}:")
    old_to_n_new = {}
    for card in cards_by_rarity[rarity]:
        for old_rarity in card.old_rarities:
            old_to_n_new.setdefault(old_rarity, 0)
            old_to_n_new[old_rarity] += 1
    for old in OLD_RARITIES:
        n_new = old_to_n_new.get(old)
        if n_new:
            print(f"\t{old}: {n_new} ({(n_new/len(cards_by_rarity[rarity]))*100:.2f}%)")

for rarity in OLD_RARITIES:
    print(f"{rarity}:")
    cards = [card for card in valid_cards.values() if rarity in card.old_rarities]
    new_to_n_old = {}
    for card in cards:
        new_to_n_old.setdefault(card.new_rarity, 0)
        new_to_n_old[card.new_rarity] += 1
    for new in range(4):
        n_old = new_to_n_old.get(new)
        if n_old:
            print(f"\t{BRACKET_NAMES[new]}: {n_old} ({(n_old/len(cards))*100:.2f}%)")

output_dir = "IPL.mse-set"
output_pack = make_pack()
mse_gen_set(output_dir, output_pack)
images = mse_gen_card_images(output_dir)
for i, image in enumerate(mse_gen_card_image_sheets(images, len(output_pack))):
    image.save(os.path.join(output_dir, f"sheet{i+1}.png"))
mpc_gen_order(output_dir, MPC_XML_FILENAME, output_pack)
# mpc_fulfill_order(MPC_XML_FILENAME)
