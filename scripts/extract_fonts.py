import argparse, base64, csv, json, os, re

parser = argparse.ArgumentParser(description="Extract font bitmaps from a CSV file extracted from a Luminator IPS project.")
parser.add_argument("csv_file", help="Path to the CSV file containing font data.")
parser.add_argument("-c", "--clear", action="store_true", help="Clear the output file before writing new data.")
args = parser.parse_args()

POINTER_OFFSET = 28
CHARSET = r""" !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~"""
output_prefix = "window.fonts = "

with open(os.path.join(os.path.dirname(__file__), "font_name_repl.json"), "r") as f:
    font_name_repl = json.load(f)

output_fonts = {}
if (not os.path.exists("fonts.js") or args.clear):
    with open("fonts.js", "w") as f:
        pass # Create empty file
else:
    with open("fonts.js", "r") as f:
        if f.read(len(output_prefix)) == output_prefix:
            output_fonts = json.load(f)
output_fonts["__charset__"] = CHARSET

with open(args.csv_file, encoding="latin-1", newline="") as f:
    fonts = csv.DictReader(f)

    for font in fonts:
        data = font["Font"].encode("latin-1")

        font_name = data[:20].decode("latin-1").replace("\x00", "").strip()
        font_height = data[22]

        if font_name_repl.get(font["FontFile"]) == "__skip__" or font_name_repl.get(font_name) == "__skip__":
            print(f"Skipping font: {font_name}, FontFile: {font['FontFile']}")
            continue

        index = POINTER_OFFSET
        pointers = []
        while not pointers or pointers[-1] != 0:
            pointers.append(data[index] << 8 | data[index + 1])
            index += 2
        pointers.pop()
        index -= 2
        BITMAP_OFFSET = index - POINTER_OFFSET

        print(f"Font: {font_name}, FontFile: {font['FontFile']}, Height: {font_height}, # characters: {len(pointers)}")

        col_width = -(-font_height // 8)
        clean_pointers = []
        for p in pointers:
            if p < BITMAP_OFFSET or (p - BITMAP_OFFSET) % col_width != 0:
                print(f"ERROR: Invalid pointer {p} for {font['FontFile']} (height: {font_height}, bitmap offset: {BITMAP_OFFSET}), skipping.")
                break
            if len(clean_pointers) >= len(CHARSET):
                print(f"WARNING: Extra pointer {p} for {font['FontFile']} (height: {font_height}, bitmap offset: {BITMAP_OFFSET}), ignoring.")
            if len(clean_pointers) < len(CHARSET) + 1: # Add one for the end of the truncated data
                clean_pointers.append((p - BITMAP_OFFSET) // col_width)
        else:
            truncated_data = data[index : index + clean_pointers[-1] * col_width]
            if (int(re.search(r"\d+", font["FontFile"]).group()) >= 10): # TODO: Find a better way to determine font spacing
                spacing = 2
            else:
                spacing = 1

            trimmed_bitmap, bit_buffer, buffer_len = [], 0, 0
            mask = (1 << font_height) - 1
            for i in range(0, len(truncated_data), col_width):
                chunk = int.from_bytes(truncated_data[i:i+col_width], byteorder="big")
                bit_buffer = (bit_buffer << font_height) | int(f"{(chunk & mask):0{font_height}b}"[::-1], 2)
                buffer_len += font_height

            while buffer_len >= 8:
                buffer_len -= 8
                trimmed_bitmap.append((bit_buffer >> buffer_len) & 0xFF)
            if buffer_len > 0:
                trimmed_bitmap.append((bit_buffer << (8 - buffer_len)) & 0xFF)
            assert len(trimmed_bitmap) == -(-len(truncated_data) * font_height // (col_width * 8)), f"Bitmap length mismatch for {font['FontFile']} (expected {-(-len(truncated_data) * font_height // (col_width * 8))}, got {len(trimmed_bitmap)})"

            output_fonts[font_name_repl.get(font["FontFile"], font["FontFile"]).upper().removesuffix(".FNT")] = {
                "height": font_height,
                "spacing": spacing,
                "pointers": clean_pointers,
                "bitmap": base64.b64encode(bytes(trimmed_bitmap)).decode("utf-8"),
            }

with open("fonts.js", "w") as f:
    f.write(output_prefix)
    json.dump(output_fonts, f, separators=(",", ":"), ensure_ascii=False)