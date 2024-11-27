import re
import os
import sys
import fitz  # PyMuPDF Do not import fitz library
import json
import anvil.server
from dotenv import load_dotenv

# Step 1: Identify if the environment is Docker
is_docker = os.path.exists('/.dockerenv')
live_server = is_docker  # Use the Docker environment as the live server indicator

# Step 2: Load the appropriate .env file
if is_docker:
    load_dotenv(".env")  # Load production environment variables
    auth_file_path = "/run/secrets/auth_file"  # Docker secrets location
else:
    load_dotenv(".env.local")  # Load local development environment variables
    auth_file_path = os.path.join("config", "auth.json")  # Local path to auth file

# Step 3: Handle missing configurations
if not auth_file_path or not os.path.exists(auth_file_path):
    raise FileNotFoundError(
        f"Authentication file not found at {auth_file_path}. Ensure it exists in the expected location."
    )

# Step 4: Load the authentication key file
with open(auth_file_path, 'r') as f:
    key = json.load(f)

# Step 5: Determine the uplink key
uplink_key = key.get("ANVIL_UPLINK_KEY" if live_server else "ANVIL_TEST_KEY")
if not uplink_key:
    raise ValueError("Uplink key not found in the authentication file.")

# Step 6: Connect to the Anvil server
anvil.server.connect(uplink_key)


def sort_key(s):
    page, lines = s.split(':')
    start_line, end_line = map(int, lines.split('-'))
    return int(page), start_line


@anvil.server.callable()
def setup_variables():
    version_number = "0.0.5"
    build_number = "7714"
    # known_issues_lst = ("Known Issues",
    #                     "- Segments that span multiple pages are not yet supported for designation lists",
    #                     "- Items imported",
    #                     "- from PDF appear in the left window in the order they were highlighted, not sequentially",
    #                     "- The auto-generated cite does not yet account for multiple segments",
    #                     "- When copying from pdf or text file, make sure to include selection of the first line number to"
    #                     " get an accurate cite")
    # the_known_issues = "\n".join(known_issues_lst)
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
def prepare_text_for_powerpoint(text, name_checkbox_state, obj_checkbox_state,
                                detect_pages_checkbox_state, witness_name_checkbox_state, witness_name_text):

    """
    Processes transcript text to prepare it for PowerPoint output.
    """
    def clean_line(line):
        """Cleans and replaces special characters in a line."""
        # Strip whitespace and replace middle dots
        line = line.strip().replace('·', ' ')

        # Replace specific phrases using the swap dictionary
        for word, replacement in swap_phrase_dict.items():
            line = line.replace(word, replacement)

        # Remove timestamps at the end of the line
        line = remove_timestamps(line)

        # Handle lines starting with special characters
        if line and not line[0].isalnum() and not any(
                line.startswith(phrase) for phrase in qa_phrases + objection_phrases + non_party_phrases):
            line = re.sub(r'^[^\w\s]', '', line)

        # Handle lines that start with "Pg. "
        if line.startswith("Pg. "):
            line = "\n\n" + line

        return line

    def remove_timestamps(line):
        """Removes timestamps in the format XX:XX:XX from the end of the line."""
        return re.sub(r'[\s\t]*\b\d{2}:\d{2}:\d{2}$', '', line).strip()


    def process_line_groups(phrase, capitalize_flag):
        """Adds a processed phrase to the completed groups, with optional capitalization."""
        if phrase:
            return phrase.upper() if capitalize_flag else phrase
        return None

    # Configuration and state variables
    qa_phrases = ["Q.", "A.", "Q ", "A ", "Q: ", "A: "]
    objection_phrases = ["MR ", "MRS ", "MS ", "ATTY ", "ATTORNEY ", "MR. ", "MRS. ", "MS. ", "ATTY. "]
    non_party_phrases = ["THE VIDEOGRAPHER", "THE COURT"]
    swap_phrase_dict = {"THE WITNESS:": "A."}
    completed_line_groups = []
    capitalize = False
    phrase_being_assembled = ""
    
    
    print(text)
    # Replace all middle dots '·' with spaces
    # text = text.replace('·', ' ')
    lines = text.split('\n')  # split lines into a list based on hard returns
    first_num = None  # set up variables to keep track of line number range
    last_num = None  # set up variables to keep track of line number range

    # qa_phrases = ["Q.", "A.", "Q ", "A ", "Q: ", "A: "]  # phrases or words that will impact when line breaks occur -
    # Qs
    # and As
    # objection_phrases = ["MR ", "MRS ", "MS ", "ATTY ",
    #                      "ATTORNEY ", "MR. ", "MRS. ", "MS. ",
    #                      "ATTY. "]  # phrases or words that affect capitalization and are flagged for removal
    # non_party_phrases = [
    #     "THE VIDEOGRAPHER", "THE COURT"]  # phrases or words that are not objections that affect caps for removal
    # completed_line_groups = []  # Used to create larger lines that are combined based on common attributes (all
    # part of an objection, etc)
    # phrase_being_assembled = ""
    # capitalize = False
    # swap_phrase_dict = {"THE WITNESS:": "A."}

    # hide_names = name_checkbox_state
    # hide_objections = obj_checkbox_state
    # show_witness_names = witness_name_checkbox_state
    # detect_pages = detect_pages_checkbox_state

    # We will be going through line by line to perform various steps. The key to understanding this
    # code is to understand when and why lines get combined and added. And everything that happens in this
    # section happens per line.

    # for-loop to go through each current line - which at this stage includes any original line breaks.

    # Process each line
    for i, line in enumerate(text.split('\n')):
        line = clean_line(line)

        # Handle page number detection
        if detect_pages_checkbox_state:
            match = re.match(r'^(\d+)\s+', line)
            if match:
                num = int(match.group(1))
                if first_num is None:
                    first_num = num
                last_num = num
                line = line[match.end():].strip()
        else:
            match = re.match(r'^\d+(:\s*\d+)?\s+', line)
            if match:
                line = line[match.end():].strip()

        # Skip lines based on checkbox states
        if name_checkbox_state and line.startswith(("QUESTIONS BY", "BY")) and ":" in line:
            continue

        # Process lines starting with specific phrases
        if any(line.startswith(phrase) for phrase in qa_phrases):
            if phrase_being_assembled:
                completed_line_groups.append(process_line_groups(phrase_being_assembled, capitalize))
            phrase_being_assembled = f"\n{line[:2]}\t{line[2:].strip()}"
            capitalize = False

        elif any(line.startswith(phrase) for phrase in objection_phrases + non_party_phrases):
            if phrase_being_assembled:
                completed_line_groups.append(process_line_groups(phrase_being_assembled, capitalize))
            phrase_being_assembled = f"\n{line}"
            capitalize = True

        else:
            if line and not capitalize:
                if phrase_being_assembled:
                    phrase_being_assembled += " "
                phrase_being_assembled += line

    # Add the final assembled phrase
    if phrase_being_assembled:
        completed_line_groups.append(process_line_groups(phrase_being_assembled, capitalize))

    # Remove objection lines if checkbox is checked
    if obj_checkbox_state:
        completed_line_groups = [line for line in completed_line_groups if not line.isupper()]

    # Combine processed lines
    processed_text = ''.join(completed_line_groups).strip()

    # Append witness name and page/line range if applicable
    if witness_name_checkbox_state and first_num is not None and last_num is not None:
        processed_text += f'\n\n{witness_name_text} Tr. Pg. __, Ln. {first_num}-{last_num}'

    return processed_text


## CHATGPT ##
# def prepare_text_for_powerpoint(text, name_checkbox_state, obj_checkbox_state,
#                                 detect_pages_checkbox_state, witness_name_checkbox_state, witness_name_text):
#     """
#     Processes transcript text to prepare it for PowerPoint output.
#     """
# 
#     def clean_line(line):
#         """Cleans and replaces special characters in a line."""
#         line = line.strip().replace('·', ' ')
#         for word, replacement in swap_phrase_dict.items():
#             line = line.replace(word, replacement)
#         return remove_timestamps(line)
# 
#     def remove_timestamps(line):
#         """Removes timestamps in the format XX:XX:XX from the end of the line."""
#         return re.sub(r'\b\d{2}:\d{2}:\d{2}$', '', line).strip()
# 
#     def process_line_groups(phrase, capitalize_flag):
#         """Adds a processed phrase to the completed groups, with optional capitalization."""
#         if phrase:
#             return phrase.upper() if capitalize_flag else phrase
#         return None
# 
#     detect_pages = detect_pages_checkbox_state
# 
#     # Configuration and state variables
#     qa_phrases = ["Q.", "A.", "Q ", "A ", "Q: ", "A: "]
#     objection_phrases = ["MR ", "MRS ", "MS ", "ATTY ", "ATTORNEY ", "MR. ", "MRS. ", "MS. ", "ATTY. "]
#     non_party_phrases = ["THE VIDEOGRAPHER", "THE COURT"]
#     swap_phrase_dict = {"THE WITNESS:": "A."}
#     completed_line_groups = []
#     capitalize = False
#     phrase_being_assembled = ""
# 
#     # Page and line number tracking
#     first_num = None
#     last_num = None
# 
#     # Process each line
#     for i, line in enumerate(text.split('\n')):
#         line = clean_line(line)
# 
#         # Handle page number detection
#         if detect_pages:
#             match = re.match(r'^(\d+)\s+', line)
#             if match:
#                 num = int(match.group(1))
#                 if first_num is None:
#                     first_num = num
#                 last_num = num
#                 line = line[match.end():].strip()
#         else:
#             match = re.match(r'^\d+(:\s*\d+)?\s+', line)
#             if match:
#                 line = line[match.end():].strip()
# 
#         # Skip lines based on checkbox states
#         if name_checkbox_state and line.startswith(("QUESTIONS BY", "BY")) and ":" in line:
#             continue
# 
#         # Process lines starting with specific phrases
#         if any(line.startswith(phrase) for phrase in qa_phrases):
#             if phrase_being_assembled:
#                 completed_line_groups.append(process_line_groups(phrase_being_assembled, capitalize))
#             phrase_being_assembled = f"\n{line[:2]}\t{line[2:].strip()}"
#             capitalize = False
# 
#         elif any(line.startswith(phrase) for phrase in objection_phrases + non_party_phrases):
#             if phrase_being_assembled:
#                 completed_line_groups.append(process_line_groups(phrase_being_assembled, capitalize))
#             phrase_being_assembled = f"\n{line}"
#             capitalize = True
# 
#         else:
#             if line and not capitalize:
#                 if phrase_being_assembled:
#                     phrase_being_assembled += " "
#                 phrase_being_assembled += line
# 
#     # Add the final assembled phrase
#     if phrase_being_assembled:
#         completed_line_groups.append(process_line_groups(phrase_being_assembled, capitalize))
# 
#     # Remove objection lines if checkbox is checked
#     if obj_checkbox_state:
#         completed_line_groups = [line for line in completed_line_groups if not line.isupper()]
# 
#     # Combine processed lines
#     processed_text = ''.join(completed_line_groups).strip()
# 
#     # Append witness name and page/line range if applicable
#     if witness_name_checkbox_state and first_num is not None and last_num is not None:
#         processed_text += f'\n\n{witness_name_text} Tr. Pg. __, Ln. {first_num}-{last_num}'
# 
#     return processed_text


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
