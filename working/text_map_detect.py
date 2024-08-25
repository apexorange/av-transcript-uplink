import fitz  # PyMuPDF
import re


def extract_vector_objects(page):
    vector_objects = []
    for obj in page.get_drawings():
        if obj['fill'] is not None:  # Check if the object is filled
            vector_objects.append(obj)
    return vector_objects


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
                        line_number = previous_line_number
                        previous_line_number = None
                        previous_line_text = ""
                    else:
                        line_number = None

                text_boxes.append({
                    'bbox': line['bbox'],
                    'text': line_text.strip(),
                    'line_number': line_number
                })

    return text_boxes


def check_overlap(box1, box2):
    # Check if two bounding boxes overlap
    x1, y1, x2, y2 = box1
    x3, y3, x4, y4 = box2
    return not (x1 > x4 or x3 > x2 or y1 > y4 or y3 > y2)


def detect_overlaps(pdf_path):
    document = fitz.open(pdf_path)
    overlapping_texts = []
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        vector_objects = extract_vector_objects(page)
        text_boxes = extract_text_boxes(page)

        for vector in vector_objects:
            vector_bbox = vector['rect']
            for text in text_boxes:
                if check_overlap(vector_bbox, text['bbox']):
                    overlapping_texts.append((page_num + 1, text['line_number'], text['text']))

    for page_num, line_number, text in overlapping_texts:
        print(f"{page_num}:{line_number}: {text}")


# Example usage
pdf_path = 'demo1.pdf'
detect_overlaps(pdf_path)
