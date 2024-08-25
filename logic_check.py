import re
import os
import sys
import fitz  # PyMuPDF Do not import fitz library
import json
import anvil.server

# with open('config.json', 'r') as config_file:
#     config = json.load(config_file)
#     anvil_uplink_key = config['ANVIL_UPLINK_KEY']
#
# anvil.server.connect(anvil_uplink_key)

problem_text = """
    Q, hello sir
    11: or should
    12 I say ma'am
    13 3 more times
    14. or more
    321:2 Q. let me just
    321:3 say that I
    321:4 Q think you make
    321:5 A. $100 or more
    333:234: $78 is
    4567:433 %10 of you"""



def sort_key(s):
    page, lines = s.split(':')
    start_line, end_line = map(int, lines.split('-'))
    return int(page), start_line

def prepare_text_for_powerpoint(text, name_checkbox_state=True, obj_checkbox_state=True,
                                detect_pages_checkbox_state=False, witness_name_checkbox_state=False,
                                witness_name_text="Cow"):

    lines = text.split('\n')  # split lines into a list based on hard returns
    first_num = None  # set up variables to keep track of line number range
    last_num = None  # set up variables to keep track of line number range

    qa_phrases = ["Q.", "A.", "Q ", "A ", "Q, ", "A, "]  # phrases or words that will impact when line breaks occur - Qs and As
    objection_phrases = ["MR ", "MRS ", "MS ", "ATTY ",
                         "ATTORNEY ", "MR. ", "MRS. ", "MS. ", "ATTY. "]  # phrases or words that affect capitalization and are flagged for removal
    non_party_phrases = [
        "THE VIDEOGRAPHER"]  # phrases or words that are not objections that affect caps for removal
    completed_line_groups = []  # Used to create larger lines that are combined based on common attributes (all
    # part of an objection, etc)
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

    for i, line in enumerate(lines):
        line = line.strip()  # Strips any white-space at the beginning or end of a line

        # Perform word replacements
        for word, replacement in swap_phrase_dict.items():
            if word in line:
                line = line.replace(word, replacement)

        # create match variable for a line that detects a sequence of one
        # or more digits followed by any number of whitespace characters, including none

        if not detect_pages:
            match = re.match(r'^\d+(:\d+)*(:|\.|)', line)

            if match:
                num = match.group(0).rstrip()
                print(num)
                line = line[match.end():].lstrip()
        else:
            match = line
            print(match)
        # else:
        #     match = re.match(r'^\d+(:(\d+)|.)(\d+\s|.|:|;)?\s+', line)
        #
        #     if match:
        #         num = int(match.group(1))
        #         print(num)
        #
        #         if first_num is None:
        #             first_num = num
        #         last_num = num  # Always update last_num with the latest number
        #
        #         line = line[match.end():].lstrip()

        if hide_names and line.startswith("QUESTIONS BY") and ":" in line:
            continue
        elif hide_names and line.startswith("BY") and ":" in line:
            continue

        if line.startswith("Pg. "):
            line = "\n\n" + line

        ##############################
        # If the line starts with a Q. or A., and if it is not capitalized or flagged by "hide objections"
        # append the current_line to phrases being assembled on a new line and remove any extraneous spaces

        if any(line.startswith(phrase) for phrase in qa_phrases):
            if phrase_being_assembled and not (capitalize and hide_objections):
                completed_line_groups.append(
                    phrase_being_assembled.upper() if capitalize else phrase_being_assembled)

            # Add first two characters, then add tab, then strip any white space on the left
            # of the remaining phrase, then add the remaining phrase

            modified_second_char = "."


            phrase_being_assembled = "\n" + line[0] + modified_second_char + "\t" + line[2:].lstrip()

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
    print("\n\n" + processed_text)
    return processed_text

prepare_text_for_powerpoint(problem_text)