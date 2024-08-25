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
                    'line_number': line_number
                })

    return text_boxes


def check_overlap(box1, box2):
    # Check if two bounding boxes overlap
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    return not (x1 > x4 or x3 > x2 or y1 > y4 or y3 > y2)


def estimate_color_name(rgb):
    color_map = {
        (1.0, 1.0, 0.0)    : "Bright Yellow",
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
        (0.8, 1.0, 1.0)    : "Light Blue"  # RGB equivalent of #CFF (or #CCFFFF)
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
    overlapping_lines = {}

    for page_index in range(len(document)):
        page = document.load_page(page_index)
        page_number = extract_page_number(page)
        if page_number is None:
            continue

        vector_objects = extract_vector_objects(page)
        text_boxes = extract_text_boxes(page)

        for vector in vector_objects:
            vector_bbox = vector['rect']
            color = vector['color']
            for text_box in text_boxes:
                if check_overlap(vector_bbox, text_box['bbox']) and text_box['line_number'] is not None:
                    line_info = (page_number, text_box['line_number'])
                    color_name = estimate_color_name(color)
                    if line_info in overlapping_lines:
                        overlapping_lines[line_info].add(color_name)
                    else:
                        overlapping_lines[line_info] = {color_name}

    sorted_overlapping_lines = sorted(overlapping_lines.items(), key=lambda x: (x[0][0], x[0][1]))

    for (page_num, line_number), colors in sorted_overlapping_lines:
        colors_str = ", ".join(colors)
        print(f"{page_num}:{line_number} - Highlight colors: {colors_str}")


# Example usage
pdf_path = 'Textmap_Clip_Report.pdf'
all_colors = analyze_pdf_colors(pdf_path)

print("All colors represented in the PDF:")
for color, count in all_colors.items():
    print(f"{color}: {count}")

detect_overlaps(pdf_path, all_colors)
