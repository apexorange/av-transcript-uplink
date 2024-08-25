import re

""" VARIABLES """

cap_strings_lst = ["<OBJ>", "<OTHER>", "<NAME>"]
detect_pages = False
witness_name = "Helt"
num_range = []

""" SOURCE """

original_line_lst: list = [
    "7 Q. Why you such shit?",
    "8 A. There were a lot of documents. I don't",
    "9: remember any specific document. There were lots.",
    "10 BY MR. HOLLANDER:",
    "11: Q. Can you describe the categories of",
    "12 documents that you reviewed?",
    "13: MR. DORSKY: Same caution, same",
    "14. objection.",
    "15 A. No, I really don't remember.",
    "16 BY MR. HOLLANDER:",
    "17 Q. Do you have any documents or notes with",
    "18 you today?",
    "19: A. No, I do not.",
    "344:12 Q. Do you like cows?",
    "344:13 A. Yes I do."
]

""" FUNCTIONS """


def set_pattern_match(text_str: str) -> tuple:
    """
    INPUT: str
    OUTPUT: str 

    Detect a pattern based on a deposition transcript with a each
    lines starting with a series of line numbers that typically range from 1-25 lines.
    However, we also have a mechanism to deal with non-standard
    deposition pages - for instance, trial transcripts by turning off
    page detection."
    """

    first_num = None  # set up variables to keep track of line number range
    last_num = None  # set up variables to keep track of line number range

    non_depo_transcript_match = re.match(r"^\d+:\d+", text_str)
    if non_depo_transcript_match is not None:
        non_depo_num = non_depo_transcript_match.group(0).split(":")
        non_depo_text_str = text_str[non_depo_transcript_match.end():].lstrip()
        print(non_depo_num, non_depo_text_str)

    match = re.match(r"^\d+(:\d+)*(:|\.|)", text_str)
    if match:
        num = match.group(0)
        text_str = text_str[match.end():].lstrip()
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


def tag_all_lines(text_str: str, input_lst: list) -> list:
    qa_prefixes_lst = ["Q.", "A."]
    objection_phrases_lst = ["MR", "MRS", "MS", "ATTY", "ATTORNEY"]
    if any(text_str.startswith(prefix) for prefix in qa_prefixes_lst):
        input_lst.append([f'{text_str}', "<QA>", True])
    elif any(text_str.startswith(phrase) for phrase in objection_phrases_lst):
        input_lst.append([f'{text_str.upper()}', "<OBJ>", True])
    elif text_str.startswith("BY") and text_str.endswith(":"):
        input_lst.append([f'{text_str.upper()}', "<NAME>", True])
    else:
        input_lst.append([text_str, None, False])
    return input_lst


def initial_transcript_intake(original: list) -> list:
    processed_lines_lst: list = []
    tagged_lines_lst: list = []
    for i, string in enumerate(original):
        text_line = string.strip()
        text_line = word_replacements(text_line)
        text_line = set_pattern_match(text_line)
        tagged_lines_lst = tag_all_lines(text_line[0], processed_lines_lst)
    return tagged_lines_lst


def assemble_lines(tagged_lines: list) -> list:
    """
    This function iterates through the `tagged_lines_lst` list, 
    and when it finds a `True` line, it starts concatenating the `False` 
    lines that follow until it hits another `True` line. It then prints the concatenated result. 
    This ensures all `False` lines are included with the preceding `True` line.
    """

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

    print(assembled_lines)
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
    first_num = 1 # calculate_line_numbers()[0]
    last_num = 25 # calculate_line_numbers()[1]
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


""" EXECUTE """


def process_all() -> str:
    output: list = initial_transcript_intake(original_line_lst)
    output: list = assemble_lines(output)
    output: list = hide_line_types(output, cap_strings_lst)
    output: str = final_formatting(output)
    return output


""" MAIN """


def main():
    print(process_all())


main()
