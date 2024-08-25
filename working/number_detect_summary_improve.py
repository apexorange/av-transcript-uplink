import fitz  # PyMuPDF
import re
import math
from collections import defaultdict


def extract_vector_objects(page):
    vector_objects = []
    for obj in page.get_drawings():
        if obj['fill'] is not None:  # Check if the object is filled
            vector_objects.append({
                'rect' : obj['rect'],
                'color': obj['fill']
            })
    return vector_objects


def extract_page_number(page):
    # Extract the first line of text on the page to get the page number
    first_line = page.get_text("text").split('\n')[0].strip()
    match = re.search(r'\d+$', first_line)  # Match the last number in the line
    if match:
        return int(match.group())
    return None


def extract_text_boxes(page):
    text_instances = page.get_text("dict")
    text_boxes = []
    previous_line_number = None
    previous_line_text = ""

    for block in text_instances['blocks']:
        if block['type'] == 0:  # Text block
            for line in block['lines']:
                line_text = ""
                for span in line['spans']:
                    line_text += span['text']

                line_text_stripped = line_text.strip()
                match = re.match(r'^\s*(\d+)\s*(Q\.|A\.)?\s*$', line_text_stripped)
                if match:
                    # If the line contains only a line number, optionally followed by "Q." or "A."
                    previous_line_number = match.group(1)
                    previous_line_text = match.group(2) if match.group(2) else ""
                    continue
                else:
                    # If the line contains text, merge it with the previous line number and "Q."/"A." if present
                    if previous_line_number is not None:
                        if previous_line_text:
                            line_text = f"{previous_line_text} {line_text_stripped}"
                        line_number = int(previous_line_number)  # Ensure line number is an integer
                        previous_line_number = None
                        previous_line_text = ""
                    else:
                        line_number = None

                text_boxes.append({
                    'bbox'       : line['bbox'],
                    'line_number': line_number,
                    'text'       : line_text_stripped
                })

    return text_boxes


def check_partial_overlap(box1, box2):
    # Check if two bounding boxes partially overlap
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    return not (x2 < x3 or x4 < x1 or y2 < y3 or y4 < y1)


def estimate_color_name(rgb):
    color_map = {
        (1.0, 1.0, 0.0)    : "Yellow",
        (1.0, 0.8, 0.6)    : "Light Orange",
        (1.0, 0.0, 0.0)    : "Red",
        (0.0, 1.0, 0.0)    : "Green",
        (0.0, 0.0, 1.0)    : "Blue",
        (0.5, 0.0, 0.5)    : "Purple",
        (0.0, 1.0, 1.0)    : "Cyan",
        (1.0, 0.0, 1.0)    : "Magenta",
        (1.0, 0.647, 0.0)  : "Orange",
        (0.545, 0.0, 0.545): "Dark Purple",
        (0.0, 0.0, 0.0)    : "Black",
        (1.0, 1.0, 1.0)    : "White",
        (0.5, 0.5, 0.5)    : "Gray",
        (0.859, 0.718, 1.0): "Purple",  # RGB equivalent of #DBB7FF
        (0.804, 1.0, 1.0)  : "Light Blue",  # RGB equivalent of #CDFFFF
        (0.8, 1.0, 1.0)    : "Light Blue",  # RGB equivalent of #CCFFFF
        (0.988, 0.6, 0.6)  : "Light Orange",  # RGB equivalent of #FC9
        (1.0, 1.0, 0.5098) : "Yellow"  # RGB equivalent of #FFFF82
    }

    def euclidean_distance(color1, color2):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(color1, color2)))

    closest_color = min(color_map.keys(), key=lambda k: euclidean_distance(k, rgb))
    return color_map[closest_color]


def analyze_pdf_colors(pdf_path):
    document = fitz.open(pdf_path)
    all_colors = defaultdict(int)

    for page_index in range(len(document)):
        page = document.load_page(page_index)
        vector_objects = extract_vector_objects(page)

        for vector in vector_objects:
            color = vector['color']
            color_name = estimate_color_name(color)
            all_colors[color_name] += 1

    return all_colors


def detect_overlaps(pdf_path, all_colors):
    document = fitz.open(pdf_path)
    overlapping_lines = defaultdict(lambda: defaultdict(list))
    last_line_on_page = {}
    page_9_lines = []

    for page_index in range(len(document)):
        page = document.load_page(page_index)
        page_number = extract_page_number(page)
        if page_number is None:
            continue

        vector_objects = extract_vector_objects(page)
        text_boxes = extract_text_boxes(page)

        detected_lines = {text_box['line_number']: text_box for text_box in text_boxes if
                          text_box['line_number'] is not None}

        for line_number in range(1, 26):
            if line_number not in detected_lines:
                detected_lines[line_number] = {'bbox': (0, 0, 0, 0), 'line_number': line_number, 'text': ''}

        for vector in vector_objects:
            vector_bbox = vector['rect']
            color = vector['color']
            color_name = estimate_color_name(color)
            for line_number, text_box in detected_lines.items():
                if check_partial_overlap(vector_bbox, text_box['bbox']):
                    overlapping_lines[color_name][(page_number, line_number)] = (page_number, line_number)

        if page_number == 9:
            page_9_lines.extend(detected_lines.keys())

        if text_boxes:
            last_line_on_page[page_number] = text_boxes[-1]['line_number']

    # Process detected lines to fill in missing lines with assumed colors
    for color, lines in overlapping_lines.items():
        sorted_lines = sorted(lines.keys())
        for i in range(len(sorted_lines) - 1):
            (page_num, line_num) = sorted_lines[i]
            (next_page_num, next_line_num) = sorted_lines[i + 1]
            if next_page_num == page_num and next_line_num == line_num + 2:
                missing_line = line_num + 1
                overlapping_lines[color][(page_num, missing_line)] = (page_num, missing_line)

    # Handle across page boundaries
    for page_num in range(1, len(document)):
        if (page_num, 25) in overlapping_lines:
            next_page = page_num + 1
            if (next_page, 2) in overlapping_lines and (next_page, 1) not in overlapping_lines:
                for color, lines in overlapping_lines.items():
                    if (page_num, 25) in lines and (next_page, 2) in lines:
                        overlapping_lines[color][(next_page, 1)] = (next_page, 1)

    color_ranges = defaultdict(list)

    for color, lines in overlapping_lines.items():
        sorted_lines = sorted(lines.keys())
        current_start_page, current_start_line = sorted_lines[0]
        previous_page_num, previous_line_num = sorted_lines[0]

        for (page_num, line_number) in sorted_lines[1:]:
            if page_num == previous_page_num and line_number == previous_line_num + 1:
                previous_line_num = line_number
            elif page_num == previous_page_num + 1 and line_number == 1 and previous_line_num == last_line_on_page[
                previous_page_num]:
                previous_page_num = page_num
                previous_line_num = line_number
            else:
                color_ranges[color].append(
                    (current_start_page, current_start_line, previous_page_num, previous_line_num))
                current_start_page, current_start_line = page_num, line_number
                previous_page_num, previous_line_num = page_num, line_number

        color_ranges[color].append((current_start_page, current_start_line, previous_page_num, previous_line_num))

    return color_ranges, sorted(set(page_9_lines))


def consolidate_ranges(color_ranges):
    consolidated_ranges = defaultdict(list)

    for color, ranges in color_ranges.items():
        new_ranges = []
        current_start_page, current_start_line, current_end_page, current_end_line = ranges[0]

        for r in ranges[1:]:
            start_page, start_line, end_page, end_line = r
            if current_end_line == 25 and start_line == 1 and current_end_page + 1 == start_page:
                current_end_page, current_end_line = end_page, end_line
            else:
                new_ranges.append((current_start_page, current_start_line, current_end_page, current_end_line))
                current_start_page, current_start_line, current_end_page, current_end_line = start_page, start_line, end_page, end_line

        new_ranges.append((current_start_page, current_start_line, current_end_page, current_end_line))
        consolidated_ranges[color] = new_ranges

    return consolidated_ranges


def print_color_ranges(color_ranges):
    for color, ranges in color_ranges.items():
        print(f"Highlight color: {color}")
        for r in ranges:
            if r[0] == r[2]:
                if r[1] == r[3]:
                    print(f"  {r[0]}:{r[1]}")
                elif r[1] == 1 and r[3] == 25:
                    print(f"  {r[0]}:1-25")
                else:
                    print(f"  {r[0]}:{r[1]}-{r[3]}")
            else:
                if r[1] == 1 and r[3] == 25:
                    print(f"  {r[0]}:1-{r[2]}:25")
                else:
                    print(f"  {r[0]}:{r[1]}-{r[2]}:{r[3]}")
        print()


def print_page_9_line_numbers(page_9_lines):
    print("Line numbers on Page 9:")
    for line_number in sorted(page_9_lines):
        print(f"  Line {line_number}")


# Example usage
pdf_path = 'demo2.pdf'
all_colors = analyze_pdf_colors(pdf_path)

print("All colors represented in the PDF:")
for color, count in all_colors.items():
    print(f"{color}: {count}")

color_ranges, page_9_lines = detect_overlaps(pdf_path, all_colors)
consolidated_ranges = consolidate_ranges(color_ranges)
print_color_ranges(consolidated_ranges)
print_page_9_line_numbers(page_9_lines)
