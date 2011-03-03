import os, os.path
import re
import sys

TEMPLATE = "page.html"
OUTPUT_DIR = "out/"

custom_tags = []

class BlockException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "Line: " + self.value

# Decorators -----------------------------------------
def tag(function):
    custom_tags.append((function.__name__, function))
    return function

def read_file(filename):
    with open(filename,"r") as f:
        return f.read()

def read_file_lines(filename):
    with open(filename,"r") as f:
        return list(f)

def write_file(filename, content):
    if not os.path.exists(OUTPUT_DIR):
        os.mkdir(OUTPUT_DIR)
    with open(filename, "w") as f:
        f.write(content)

def init_sections(sections):
    for tag_name, tag_function in custom_tags:
        sections[tag_name] = tag_function(sections)

    return sections

def parse_sections(lines, init = True):
    sections = {}
    if init:
        sections = init_sections(sections)

    section = []
    name = "__nosection__"
    for line in lines:
        if line.startswith("##"):
            sections[name] = "".join(section).strip()
            section = []
            name = line[2:].strip()
        else:
            section.append(line)

    sections[name] = "".join(section)
    sections[name].strip()
    return sections

def block_extract_name(line):
    line = line.strip().strip()
    search = re.search('{% block \w+ %}', line)
    if search is not None:
        arg = line[search.start():search.end()]
        arg = arg.split(" ")[2]
        return arg
    else:
        raise BlockException(line)

def block_extract_content(block_name, text):
    block_re ='{% block BLOCK_NAME %}'
    block_re = block_re.replace('BLOCK_NAME', block_name)
    search_start = re.search(block_re, text)
    block_ending ='{% endblock %}'
    search_end = re.search(block_ending, text)
    return text[search_start.end():search_end.start()]

def blocks_extract(template):
    blocks = {}
    arg = None
    in_block = False
    for line_no, line in enumerate(template):
        if re.match(".*{% block ", line):
            try:
                arg = block_extract_name(line)
            except BlockException as ex:
                print "There's an error in parsing a block at line:", line_no
                print ex
                sys.exit(-1)
            blocks[arg] = {}
            blocks[arg]['lines'] = []
            in_block = True
        if re.match(".*{% endblock %}", line):
            in_block = False
            blocks[arg]['lines'].append(line)
        if in_block:
            blocks[arg]['lines'].append(line)
    return blocks

def template_has_base(template):
    first_line = template[0].strip()
    if re.match('{% extends "\w+.\w+" %}', first_line) is not None:
        return True
    return False

def template_base_filename(template):
    first_line = template[0].strip()
    base_search = re.search('"\w+.\w+"', first_line)
    base_filename = first_line[base_search.start()+1:base_search.end()-1]
    return base_filename

def replace_block(block_name, block, template_base):
    block_re = '{% block BLOCK_NAME %}\n*.*{% endblock %}'
    block_string = block_re.replace('BLOCK_NAME', block_name)
    search = re.search(block_string, template_base)
    if search is not None:
        to_be_replaced = template_base[search.start():search.end()]
        block_in_template = "".join(block['lines'])
        replace_by = block_extract_content(block_name, block_in_template)

        template_base = template_base.replace(to_be_replaced, "".join(replace_by))
    return template_base

def replace_blocks(blocks, base_filename):
    template_base = read_file(base_filename)

    for block in blocks:
        template_base = replace_block(block, blocks[block], template_base)

    #set unprocessed blocks to default values
    default_blocks = blocks_extract(template_base.split("\n"))
    for block in default_blocks:
        line = default_blocks[block]['lines'][0]
        block_name = block_extract_name(line)
        template_base = replace_block(block_name, default_blocks[block], template_base)
    return template_base

def construct_inheritance(filename):
    template = read_file_lines(filename)
    if template_has_base(template):
        base_filename = template_base_filename(template)

        blocks = blocks_extract(template)
        return replace_blocks(blocks, base_filename)
    else:
        return read_file(filename)

def replace_sections(template, sections):
    for section in sections:
        tag = "{{" + section + "}}"
        template = template.replace(tag, "".join(sections[section]))
    return template

def read_sections(filename, init = False):
    lines = read_file_lines(filename)
    sections =  parse_sections(lines, init)
    sections[ "__filename__" ] = filename
    return sections

def output_filename(filename):
    if filename.endswith(".w"):
        basename = filename[:-2]
    else:
        basename = filename
    return basename + ".html"

def preprocess(filename, sections):
    return [ (output_filename(filename), sections) ]

def process_file(filename):
    template = construct_inheritance(TEMPLATE)
    for outfile, sections in preprocess(filename, read_sections(filename, True)):
        output = replace_sections(template, sections)
        write_file(os.path.join(OUTPUT_DIR, outfile), output)

def main():
    if len(sys.argv) == 1:
        print "usage: snowflake <file>"
    else:    
        for filename in sys.argv[1:]:
            print "Processing ", filename, "..."
            process_file(filename)

if __name__ == '__main__':
    if os.path.isfile("customize.py"):
        execfile("customize.py")
    main()
