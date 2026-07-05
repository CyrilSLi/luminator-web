import csv, itertools, os, shutil

os.makedirs("fonts", exist_ok=True)

BITMAP_OFFSET = 28

with open("data/fonts", encoding="latin-1", newline="") as f:
    fonts = csv.DictReader(f)

    for font in fonts:
        data = font["Font"].encode("latin-1")

        font_name = data[:20].decode("latin-1").replace("\x00", "").strip()
        font_height = data[22]

        print(f"Font: {font_name}, FontFile: {font['FontFile']}, Height: {font_height}")
        # print(f"Height: {font_height}")

        index = BITMAP_OFFSET
        pointers = []
        while not pointers or pointers[-1] != 0:
            pointers.append(data[index] << 8 | data[index + 1])
            index += 2
        pointers.pop()
        index -= 2

        # print(f"# of characters: {len(pointers)}")

        bitmap = [[] for _ in range(font_height + 1)]
        for column in itertools.batched(data[index:], -(-font_height // 8)):
            col_bits = [(byte >> i) & 1 for byte in column for i in range(7, -1, -1)]
            col_bits = col_bits[-font_height:][::-1]

            for j, i in enumerate(col_bits):
                bitmap[j].append(i)
            bitmap[-1].append((0, 1)[index - BITMAP_OFFSET in pointers])

            index += len(column)

        with open(f'fonts/{font["FontFile"]}.txt', "w") as f:
            for i in bitmap:
                f.write("".join((" ", "█")[bit] for bit in i) + "\n")