import argparse, base64, csv, json, os

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
            clean_pointers.pop() # Remove the last pointer for the end of the truncated data (if there are more characters than in the charset)
            output_fonts[font_name_repl.get(font["FontFile"], font["FontFile"]).upper().removesuffix(".FNT")] = {
                "height": font_height,
                "spacing": int(font["FontWidth"]),
                "pointers": clean_pointers,
                "bitmap": base64.b64encode(truncated_data).decode("utf-8"),
            }

with open("fonts.js", "w") as f:
    f.write(output_prefix)
    json.dump(output_fonts, f, separators=(",", ":"), ensure_ascii=False)