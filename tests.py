import os

import proxy_league_helper as plh

plh.parse_card_list()

print(f"Valid cards: {len(plh.valid_cards)}")
print(f"Valid printings: {sum(c.printings for c in plh.valid_cards.values())}")

last_bracket = 0
for i, bracket in enumerate(plh.BRACKETS):
    n_in_bracket = 0
    for card in plh.valid_cards.values():
        price = min(card.prices)
        if price > last_bracket and price <= bracket:
            n_in_bracket += 1
    print(
        f"cards in bracket '{plh.BRACKET_NAMES[i]}': {n_in_bracket} ({(n_in_bracket/len(plh.valid_cards))*100:.2f}%)"
    )
    last_bracket = bracket

for rarity in range(4):
    print(f"{plh.BRACKET_NAMES[rarity]}:")
    old_to_n_new = {}
    for card in plh.cards_by_rarity[rarity]:
        for old_rarity in card.old_rarities:
            old_to_n_new.setdefault(old_rarity, 0)
            old_to_n_new[old_rarity] += 1
    for old in plh.OLD_RARITIES:
        n_new = old_to_n_new.get(old)
        if n_new:
            print(
                f"\t{old}: {n_new} ({(n_new/len(plh.cards_by_rarity[rarity]))*100:.2f}%)"
            )

for rarity in plh.OLD_RARITIES:
    print(f"{rarity}:")
    cards = [card for card in plh.valid_cards.values() if rarity in card.old_rarities]
    new_to_n_old = {}
    for card in cards:
        new_to_n_old.setdefault(card.new_rarity, 0)
        new_to_n_old[card.new_rarity] += 1
    for new in range(4):
        n_old = new_to_n_old.get(new)
        if n_old:
            print(
                f"\t{plh.BRACKET_NAMES[new]}: {n_old} ({(n_old/len(cards))*100:.2f}%)"
            )

output_dir = "IPL.mse-set"
output_pack = plh.make_pack()
plh.mse_gen_set(output_dir, output_pack)
images = plh.mse_gen_card_images(output_dir)
for i, image in enumerate(plh.mse_gen_card_image_sheets(images, len(output_pack))):
    image.save(os.path.join(output_dir, f"sheet{i+1}.png"))
plh.mpc_gen_order(output_dir, plh.MPC_XML_FILENAME, output_pack)
# mpc_fulfill_order(plh.MPC_XML_FILENAME)
