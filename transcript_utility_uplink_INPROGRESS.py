import re
import os
import sys
import fitz  # PyMuPDF Do not import fitz library
import json
import anvil.server

# with open('config.json', 'r') as config_file:
#     config = json.load(config_file)
#     anvil_uplink_key = config['ANVIL_UPLINK_KEY']

anvil.server.connect("server_ARFEZLY67UIMLRTENGAWS7CJ-NV5FCPEABGGH7M5W")


def sort_key(s):
    page, lines = s.split(':')
    start_line, end_line = map(int, lines.split('-'))
    return int(page), start_line


@anvil.server.callable()
def setup_variables():
    build_number = 7710
    copyright_info = "Copyright 2024, Apex Designs"
    return f"{copyright_info}"  # {the_known_issues}\n


@anvil.server.callable
def process_pdf_locally(file):
    # Here, 'file' is the Media object sent from Anvil
    # You can read its content and process it as needed
    with open("temp_pdf.pdf", "wb") as f:
        f.write(file.get_bytes())

    with open("temp_pdf.pdf", "rb") as f:
        text_display = extract_highlighted_text_with_coordinates(f)
        return "".join(text_display)


@anvil.server.callable
def process_pdf(file):
    # This function will be called from the client code with the uploaded file
    # Now, send this file to the local script
    print(f"File name: {file.name}")
    print(f"Content type: {file.content_type}")
    # Get the file content
    file_content = file.get_bytes()

    # Check the size of the file content
    print(f"File size: {len(file_content)} bytes")
    return anvil.server.call('process_pdf_locally', file)


@anvil.server.callable
def delete_temp_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        return "File deleted successfully"
    else:
        return "File does not exist"


# @anvil.server.callable()
# def process_pdf_content(file):
#     if file:
#         # Call the function to extract highlighted text and populate the left text field
#         text_display = extract_highlighted_text_with_coordinates(file)
#         return "".join(text_display)


def extract_highlighted_text_with_coordinates(file: object) -> object:
    """ EXTRACT TEXT FROM PDF """

    highlighted_texts = []
    citations = []
    doc = fitz.open(file)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        annotations = page.annots()

        if annotations is not None:
            annotations_found = True
            for annot in annotations:
                if annot.type[0] == 8:  # Check if the annotation is a highlight
                    rect = annot.rect
                    highlighted_text = page.get_text("text", clip=rect)

                    # Call the function and store the result
                    result = process_pdf_highlighted_text(page_num, highlighted_text)
                    # print(f'Page Number: {result[0]}')

                    # Extract the line range info and processed text from the result
                    line_range_info = "".join(result.keys())
                    processed_pdf_highlighted_text = "".join(result.values())

                    # Append the processed text to the highlighted_texts list
                    highlighted_texts.append(f"Pg. {line_range_info}: \n{processed_pdf_highlighted_text} "
                                             f"---\n\n")

                    # Append the line range info to the citations list
                    citations.append(line_range_info)

    doc.close()
    return highlighted_texts


def process_pdf_highlighted_text(page_num, text):
    """ PREPARE TEXT THAT HAS BEEN EXTRACTED FROM PDF """

    excerpt_dict = {}
    processed_text = []
    first_line_number = None
    last_line_number = None
    lines = text.split('\n')

    for i, line in enumerate(lines):
        # Match a line number at the beginning of a line
        match = re.match(r'^(\d+)\s*$', line)
        if match:
            line_number = int(match.group(1))

            # Track the first and last line numbers
            if first_line_number is None:
                first_line_number = line_number
            last_line_number = line_number

            # Append line number with the subsequent line of text
            if i + 1 < len(lines):
                combined_line = f"{line_number} {lines[i + 1]}"
                processed_text.append(combined_line)
        elif i == 0 or not re.match(r'^\d+\s*$', lines[i - 1]):
            # Include lines that are not immediately after a line number
            processed_text.append(line)

    # Format the line range and page information
    line_range_info = f"{page_num + 1}:{first_line_number}-{last_line_number}" if (first_line_number and
                                                                                   last_line_number) else f"{page_num + 1}"

    excerpt_dict.update({line_range_info: '\n'.join(processed_text)})

    return excerpt_dict


@anvil.server.callable()
def prepare_text_for_powerpoint(
        text,
        name_checkbox_state,
        obj_checkbox_state,
        detect_pages_checkbox_state,
        witness_name_checkbox_state,
        witness_name_text
        ) -> str:

    lines = text.split('\n')  # split lines into a list base on hard returns
    # first_num = None  # set up variables to keep track of line number range
    # last_num = None  # set up variables to keep track of line number range
    qa_phrases = ["Q.", "A."]  # phrases or words that will impact when line breaks occur - Qs and As
    # phrases or words that affect capitalization and are flagged for removal
    objection_phrases = ["MR", "MRS", "MS", "ATTY", "ATTORNEY"]
    non_party_phrases = ["THE VIDEOGRAPHER"]  # phrases or words that are not objections that affect caps for removal
    completed_line_groups = []  # Used to create larger lines that are combined based on common attributes (all
    # part of an objection, etc...)
    phrase_being_assembled = ""
    capitalize = False
    swap_phrase_dict = {"THE WITNESS:": "A."}

    hide_names = name_checkbox_state
    hide_objections = obj_checkbox_state
    show_witness_names = witness_name_checkbox_state
    detect_pages = detect_pages_checkbox_state

    # We will be going through line by line to perform various steps. The key to understanding this
    # code is to understand when and why lines get combined and added. And everything that happens in this
    # section happens per line.

    # for-loop to go through each current line - which at this stage includes any original line breaks.

    def set_pattern_match(text: str) -> str:
        first_num = None  # set up variables to keep track of line number range
        last_num = None  # set up variables to keep track of line number range
        if not detect_pages:
            match = re.match(r'^\d+(:\s*\d+)?\s+', text)

            if match:
                num = match.group(1)
                text = text[match.end():].lstrip()
        else:
            match = re.match(r'^(\d+)\s+', text)
            print(match)

            if match:
                num = int(match.group(1))

                if first_num is None:
                    first_num = num
                last_num = num  # Always update last_num with the latest number

                text = text[match.end():].lstrip()
        print(type(text))
        return text

    def perform_word_replacement(l):
        for word, replacement in swap_phrase_dict.items():
            if word in l:
                l = l.replace(word, replacement)
        return l

    def perform_hide_names_bypass(l):
        if hide_names and l.startswith("QUESTIONS BY") and ":" in l:
            pass
        elif hide_names and line.startswith("BY") and ":" in l:
            pass

        if l.startswith("Pg. "):
            l = "\n\n" + l
        return l

    for i, line in enumerate(lines):
        line = line.strip()  # Strips any white-space at the beginning or end of a line

        # create match variable for a line that detects a sequence of one
        # or more digits followed by any number of whitespace characters, including none

        """ Assign pattern based on Detect Pages checkbox """
        line = set_pattern_match(line)

        """ Check for words to replace and replace them in the line """
        line = perform_word_replacement(line)

        """ Check for hide names """
        line = perform_hide_names_bypass(line)

        ##############################
        # If the line starts with a Q. or A., and if it is not capitalized or flagged by "hide objections"
        # append the current_line to phrases being assembled on a new line and remove any extraneous spaces

        if any(line.startswith(phrase) for phrase in qa_phrases):
            if phrase_being_assembled and not (capitalize and hide_objections):
                completed_line_groups.append(
                    phrase_being_assembled.upper() if capitalize else phrase_being_assembled)

            # Add first two characters, then add tab, then strip any white space on the left
            # of the remaining phrase, then add the remaining phrase

            phrase_being_assembled = "\n" + line[:2] + "\t" + line[2:].lstrip()

            # Do not capitalize because these are Q and A phrases and need to be shown.
            capitalize = False

        ##############################
        # If the line starts with one of the objection phrases, append the current_line to
        # phrases being assembled and capitalize it, if not just append it as is

        elif any(line.startswith(phrase) for phrase in objection_phrases):
            if phrase_being_assembled and not (capitalize and hide_objections):
                completed_line_groups.append(
                    phrase_being_assembled.upper() if capitalize else phrase_being_assembled)
            phrase_being_assembled = "\n" + line
            capitalize = True

        ##############################
        # If the line starts with one of the non-party phrases, append the current_line to
        # phrases being assembled and capitalize it, if not just append it as is

        elif any(line.startswith(phrase) for phrase in non_party_phrases):
            if phrase_being_assembled and not (capitalize and hide_objections):
                completed_line_groups.append(
                    phrase_being_assembled.upper() if capitalize else phrase_being_assembled)
            phrase_being_assembled = "\n" + line
            capitalize = True

        ##############################
        # Else, any other line that is not flagged as capitalized or hide_objections, and if it is not starting
        # with one of the Q or A phrases, then add a space so it connects to the previous line, and then add the
        # line
        # to phrase being assembled

        else:
            if line and not capitalize:  # and hide_objections):
                if phrase_being_assembled and not any(line.startswith(phrase) for phrase in qa_phrases):
                    phrase_being_assembled += " "
                phrase_being_assembled += line

    if phrase_being_assembled:
        completed_line_groups.append(phrase_being_assembled.upper() if capitalize else phrase_being_assembled)
        for line in completed_line_groups:
            if line.isupper() and hide_objections:
                completed_line_groups.remove(line)

    processed_text = ''.join(completed_line_groups).strip()

    # Fetch the name from the name field
    # name = self.name_edit.text()

    # Append the line number range with the name if detected
    if show_witness_names:
        if first_num is not None and last_num is not None:
            processed_text += '\n\n{} Tr. Pg. __, Ln. {}-{}'.format(witness_name_text, first_num, last_num)  # name,

    return processed_text


@anvil.server.callable()
def prepare_text_for_oncue(text):
    matches = []
    lines = text.split()
    for i, line in enumerate(lines):
        line = line.strip()  # Strips any white-space at the beginning or end of a line
        match = re.match(r'\d+:\d+-\d+:', line)

        if match:
            matches.append(line.rstrip(":"))

    sorted_matches = sorted(matches, key=sort_key)
    processed_text = "\n".join(sorted_matches)
    return processed_text


anvil.server.wait_forever()
