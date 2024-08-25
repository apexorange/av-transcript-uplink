#!/usr/bin/env python
# coding: utf-8
# Core Transcript Cleaner

import re

""" VARIABLES """

lines_to_hide: list = ["<OBJ>", "<OTHER>", "<NAME>"]
detect_pages = True
witness_name = "Helt"
num_range = []

""" SOURCE """

original_line_lst: list = [
    "Q. Why you so cool, bro?",
    "8 A. There were a lot of documents. I don't",
    "9 remember any specific document. There were lots.",
    "10 BY MR. HOLLANDER:",
    "11 Q. Can you describe the categories of",
    "12 documents that you reviewed?",
    "13 MR. DORSKY: Same caution, same",
    "14 objection.",
    "15 A. No, I really don't remember.",
    "16 BY MR. HOLLANDER:",
    "17 Q. Do you have any documents or notes with",
    "18 you today?",
    "19 A. No, I do not."
]


# FUNCTIONS

def set_pattern_match(text_str: str) -> tuple:
    """
    INPUT: str
    OUTPUT: str 

    Detect a pattern based on a deposition transcript with a each
    lines starting with a line number that typically ranges from 1-25 lines.

    However, we also have a mechanism to deal with non-standard
    deposition pages - for instance, trial transcripts, by turning off
    page detection."
    """

    first_num = None  # set up variables to keep track of line number range
    last_num = None  # set up variables to keep track of line number range

    if not detect_pages:  # format for non-standard transcripts
        """# This regex matches one or more digits at the start of a string, 
        optionally followed by a colon and zero or more whitespace characters, 
        then more digits, ending with at least one whitespace character."""

        match = re.match(r"^\d+(:\s*\d+)?\s+", text_str)

        if match:
            num = match.group(1)
            text_str = text_str[match.end():].lstrip()
    else:  # format for standard transcripts
        """# This regex matches one or more digits at the beginning of a 
        string followed by at least one whitespace character."""

        match = re.match(r"^(\d+)\s+", text_str)

        if match:
            num = int(match.group(1))
            text_str = text_str[match.end():].lstrip()  # remove spaces on the left of text string
            num_range.append(num)
    return text_str, num_range


def word_replacements(text_str: str) -> str:
    """
    INPUT: str
    OUTPUT: str

    Performs a key/value word replacement for 
    any of the text strings in the current line
    """
    swap_phrase_dct = {"THE WITNESS:": "A."}
    for word, replacement in swap_phrase_dct.items():
        if word in text_str:
            text_str = text_str.replace(word, replacement)
    return text_str


def tag_all_lines(text_lst: list) -> list:
    output_lst = []
    qa_prefixes_lst = ["Q.", "A."]
    objection_phrases_lst = ["MR", "MRS", "MS", "ATTY", "ATTORNEY"]
    for i, text in enumerate(text_lst):
        text_line = text.strip()
        text_line = word_replacements(text_line)
        text_line = set_pattern_match(text_line)[0]
        if any(text_line.startswith(prefix) for prefix in qa_prefixes_lst):
            output_lst.append([f'{text_line}', "<QA>", True])
        elif any(text_line.startswith(phrase) for phrase in objection_phrases_lst):
            output_lst.append([f'{text_line.upper()}', "<OBJ>", True])
        elif text_line.startswith("BY") and text_line.endswith(":"):
            output_lst.append([f'{text_line.upper()}', "<NAME>", True])
        else:
            output_lst.append([text_line, None, False])
    return output_lst


""" Example output for function """
"""
[
['LINE OF TEXT', 'TYPE OF LINE', 'KEY LINE?']
['Q. Why you so cool, bro?', '<QA>', True]
['remember any specific document. There were lots.', None, False]
['BY MR. HOLLANDER:', '<NAME>', True]
....
]
"""


def assemble_lines(tagged_lines: list) -> list:
    """
    This function iterates through the `tagged_lines_lst` list, 
    and when it finds a `True` line, it starts concatenating the `False` 
    lines that follow until it hits another `True` line. It then prints the concatenated result. 
    This ensures all `False` lines are included with the preceding `True` line.
    """

    cap_strings_lst = ["<OBJ>", "<OTHER>", "<NAME>"]
    assembled_lines = []
    for i, e in enumerate(tagged_lines):
        if tagged_lines[i][2]:
            if tagged_lines[i][1] not in cap_strings_lst:
                output = tagged_lines[i][0]
                i += 1
                while i < len(tagged_lines) and not tagged_lines[i][2]:
                    output += " " + tagged_lines[i][0]
                    i += 1
                assembled_lines.append(output)
            else:
                output = tagged_lines[i][1] + " " + tagged_lines[i][0]
                i += 1
                while i < len(tagged_lines) and not tagged_lines[i][2]:
                    output += " " + tagged_lines[i][0].upper()
                    i += 1
                assembled_lines.append(output)
    return assembled_lines


def hide_line_types(lines: list, hide_lst: list) -> list:
    "Choose line type to hide based on prefix"

    def no_objection(line):
        if not any(item in line for item in hide_lst):
            return line

    return list(filter(no_objection, lines))


def calculate_line_numbers():
    prefix_num_count: int = len(num_range)
    total_line_count: int = len(original_line_lst)
    prefix_first_digit: int = num_range[0]
    prefix_last_digit: int = num_range[-1]
    if prefix_num_count < total_line_count:
        prefix_first_digit = prefix_first_digit - 1
        return [prefix_first_digit, prefix_last_digit]
    return prefix_first_digit, prefix_last_digit


def final_formatting(lines: list) -> str:
    first_num = calculate_line_numbers()[0]
    last_num = calculate_line_numbers()[1]
    formatted_lines = []
    for line in lines:
        if line.startswith("Q. "):
            formatted_lines.append(line.replace("Q. ", "Q.\t"))
        elif line.startswith("A. "):
            formatted_lines.append(line.replace("A. ", "A.\t"))
        else:
            formatted_lines.append(line)
    output_lines: str = '\n'.join(formatted_lines)
    output_lines_cite: str = f"{output_lines}\n\n{witness_name} Dep. Tr. Pg. {first_num}-{last_num}"
    return output_lines_cite


# EXECUTE

def process_all() -> str:
    tagged_lines: list = tag_all_lines(original_line_lst)
    assembled_lines: list = assemble_lines(tagged_lines)
    visible_lines: list = hide_line_types(assembled_lines, lines_to_hide)
    formatted_lines: str = final_formatting(visible_lines)
    return formatted_lines

print(process_all())

# <a style='text-decoration:none;line-height:16px;display:flex;color:#5B5B62;padding:10px;justify-content:end;' href='https://deepnote.com?utm_source=created-in-deepnote-cell&projectId=e1d586bc-da2c-47e6-8a41-c6e331a26a2f' target="_blank">
# <img alt='Created in deepnote.com' style='display:inline;max-height:16px;margin:0px;margin-right:7.5px;' src='data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz4KPHN2ZyB3aWR0aD0iODBweCIgaGVpZ2h0PSI4MHB4IiB2aWV3Qm94PSIwIDAgODAgODAiIHZlcnNpb249IjEuMSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIiB4bWxuczp4bGluaz0iaHR0cDovL3d3dy53My5vcmcvMTk5OS94bGluayI+CiAgICA8IS0tIEdlbmVyYXRvcjogU2tldGNoIDU0LjEgKDc2NDkwKSAtIGh0dHBzOi8vc2tldGNoYXBwLmNvbSAtLT4KICAgIDx0aXRsZT5Hcm91cCAzPC90aXRsZT4KICAgIDxkZXNjPkNyZWF0ZWQgd2l0aCBTa2V0Y2guPC9kZXNjPgogICAgPGcgaWQ9IkxhbmRpbmciIHN0cm9rZT0ibm9uZSIgc3Ryb2tlLXdpZHRoPSIxIiBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPgogICAgICAgIDxnIGlkPSJBcnRib2FyZCIgdHJhbnNmb3JtPSJ0cmFuc2xhdGUoLTEyMzUuMDAwMDAwLCAtNzkuMDAwMDAwKSI+CiAgICAgICAgICAgIDxnIGlkPSJHcm91cC0zIiB0cmFuc2Zvcm09InRyYW5zbGF0ZSgxMjM1LjAwMDAwMCwgNzkuMDAwMDAwKSI+CiAgICAgICAgICAgICAgICA8cG9seWdvbiBpZD0iUGF0aC0yMCIgZmlsbD0iIzAyNjVCNCIgcG9pbnRzPSIyLjM3NjIzNzYyIDgwIDM4LjA0NzY2NjcgODAgNTcuODIxNzgyMiA3My44MDU3NTkyIDU3LjgyMTc4MjIgMzIuNzU5MjczOSAzOS4xNDAyMjc4IDMxLjY4MzE2ODMiPjwvcG9seWdvbj4KICAgICAgICAgICAgICAgIDxwYXRoIGQ9Ik0zNS4wMDc3MTgsODAgQzQyLjkwNjIwMDcsNzYuNDU0OTM1OCA0Ny41NjQ5MTY3LDcxLjU0MjI2NzEgNDguOTgzODY2LDY1LjI2MTk5MzkgQzUxLjExMjI4OTksNTUuODQxNTg0MiA0MS42NzcxNzk1LDQ5LjIxMjIyODQgMjUuNjIzOTg0Niw0OS4yMTIyMjg0IEMyNS40ODQ5Mjg5LDQ5LjEyNjg0NDggMjkuODI2MTI5Niw0My4yODM4MjQ4IDM4LjY0NzU4NjksMzEuNjgzMTY4MyBMNzIuODcxMjg3MSwzMi41NTQ0MjUgTDY1LjI4MDk3Myw2Ny42NzYzNDIxIEw1MS4xMTIyODk5LDc3LjM3NjE0NCBMMzUuMDA3NzE4LDgwIFoiIGlkPSJQYXRoLTIyIiBmaWxsPSIjMDAyODY4Ij48L3BhdGg+CiAgICAgICAgICAgICAgICA8cGF0aCBkPSJNMCwzNy43MzA0NDA1IEwyNy4xMTQ1MzcsMC4yNTcxMTE0MzYgQzYyLjM3MTUxMjMsLTEuOTkwNzE3MDEgODAsMTAuNTAwMzkyNyA4MCwzNy43MzA0NDA1IEM4MCw2NC45NjA0ODgyIDY0Ljc3NjUwMzgsNzkuMDUwMzQxNCAzNC4zMjk1MTEzLDgwIEM0Ny4wNTUzNDg5LDc3LjU2NzA4MDggNTMuNDE4MjY3Nyw3MC4zMTM2MTAzIDUzLjQxODI2NzcsNTguMjM5NTg4NSBDNTMuNDE4MjY3Nyw0MC4xMjg1NTU3IDM2LjMwMzk1NDQsMzcuNzMwNDQwNSAyNS4yMjc0MTcsMzcuNzMwNDQwNSBDMTcuODQzMDU4NiwzNy43MzA0NDA1IDkuNDMzOTE5NjYsMzcuNzMwNDQwNSAwLDM3LjczMDQ0MDUgWiIgaWQ9IlBhdGgtMTkiIGZpbGw9IiMzNzkzRUYiPjwvcGF0aD4KICAgICAgICAgICAgPC9nPgogICAgICAgIDwvZz4KICAgIDwvZz4KPC9zdmc+' > </img>
# Created in <span style='font-weight:600;margin-left:4px;'>Deepnote</span></a>
