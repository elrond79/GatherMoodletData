#!/usr/bin/env python3

'''Gather information about all moodlets, and output as a tsv
'''

#C:\Apps\DevTools\Python36\Scripts\ipython3.exe "C:\Apps (x86)\Games\XML Extractor for The Sims 4\gather_moodlet_data.py"
#import runpy; gmd_globals = runpy.run_path("C:\Apps (x86)\Games\XML Extractor for The Sims 4\gather_moodlet_data.py"); globals().update(gmd_globals)

import os
import sys
import argparse
import inspect
import pathlib
import re

from pathlib import Path
import xml.etree.ElementTree as ElementTree

THIS_PATH = Path(inspect.getsourcefile(lambda: None)).resolve(strict=True)
THIS_DIR = THIS_PATH.parent

# ==============================================================================
# ElementTree helpers

# from: https://bugs.python.org/issue8277#msg102078
class MyTreeBuilder(ElementTree.TreeBuilder):
   def comment(self, data):
       self.start(ElementTree.Comment, {})
       self.data(data)
       self.end(ElementTree.Comment)

def iter_comments(element):
    for child in element:
        if child.tag == ElementTree.Comment:
            yield child

def find_comment(element):
    for comment in iter_comments(element):
        return comment

def get_sims_typed_comment(element, typename, allow_none=False):
    comment = find_comment(element)
    if allow_none and comment is None:
        return None
    splitcomment = comment.text.split(": ", 1)
    assert len(splitcomment) == 2
    assert (splitcomment[0]) == typename
    return splitcomment[1]

# ==============================================================================


def parse_and_output_tsv(basedir, output_path):
    parsed_buffs = parse_buffs(basedir)
    output_tsv(parsed_buffs, output_path)

def parse_buffs(basedir):
    basedir = Path(basedir)
    buffs = []
    for buff_xml in iter_buff_xmls(basedir):
        try:
            buffs.append(parse_buff_xml(buff_xml))
        except Exception:
            print("Error parsing: {}".format(buff_xml))
            raise
    return buffs

def iter_buff_xmls(basedir):
    for expansion_dir in basedir.iterdir():
        # directories by expansion / game pack / etc (BG, EP03, GP03, SP05, etc)
        if not expansion_dir.is_dir():
            continue
        buff_dir = expansion_dir / "buff"
        if not buff_dir.is_dir():
            continue
        for buff_xml in buff_dir.iterdir():
            if buff_xml.suffix.lower() != ".xml":
                continue
            yield buff_xml

def parse_buff_xml(buff_xml):
    expansion_dir = buff_xml.parent.parent
    data = {
        'filename': buff_xml,
        'expansion_dir': expansion_dir.name,
        'categories': [],
        'duration': None,
        'buff_description': None,
        'mood_weight': 1,
    }

    parser = ElementTree.XMLParser(target=MyTreeBuilder())
    with buff_xml.open(encoding="utf-8") as f:
        tree = ElementTree.parse(f, parser=parser)
    root = tree.getroot()

    def get_T_comment(n, typename, allow_none=False):
        element = root.find("./T[@n='{}']".format(n))
        if allow_none and element is None:
            return None
        return get_sims_typed_comment(element, typename, allow_none=allow_none)

    try:
        mood_type = get_T_comment('mood_type', 'Mood', allow_none=True)
        if mood_type is None:
            def is_visible():
                vis = root.find("./T[@n='visible']")
                if vis is not None:
                    if vis.text == 'False':
                        return False
                    elif vis.text == 'True':
                        return True
                    else:
                        raise ValueError(vis.text)
                return True

            known = False
            if not is_visible():
                # sim_is_re = re.compile(r'_buff_Sim_Is[A-Za-z]+.xml$')
                # trait_re = re.compile(r'_Buff_Trait_[A-Za-z]+.xml$')
                # wedding_re = re.compile(r'_buff_Wedding_Betrothed[A-Za-z]+.xml$')
                # if sim_is_re.search(buff_xml.name):
                #     known = True
                # elif trait_re.search(buff_xml.name):
                #     known = True
                # elif wedding_re.search(buff_xml.name):
                #     known = True
                # elif root.find("./U[@n='game_effect_modifier']//L[@n='score_multipliers']"):
                #     known = True
                known = True

            if not known:
                print("=" * 80)
                print("skipping (no mood): {}".format(buff_xml))
                print(ElementTree.dump(root))
                print()
            return None

        data['mood_type'] = mood_type
        mood_weight = root.find("./T[@n='mood_weight']")
        if mood_weight is None:
            # only acceptable if mood is 'fine'!
            if mood_type != 'Mood_Fine':
                raise RuntimeError("no mood_weight only allowed if mood is fine")
        else:
            data['mood_weight'] = mood_weight.text

        data["rawname"] = root.attrib["n"]
        enabled_data = root.find("./V[@t='enabled']/U[@n='enabled']")
        if enabled_data:
            categories = [x.text for x in
                          enabled_data.findall("./L[@n='categories']/E")]
            data['categories'] = categories
            duration = enabled_data.find("./T[@n='max_duration']")
            if duration is not None:
                data['duration'] = duration.text
        data['icon'] = root.find("./T[@n='icon']").attrib["p"]
        data['buff_name'] = get_T_comment('buff_name', 'String')
        data['buff_description'] = get_T_comment('buff_description', 'String',
                                                 allow_none=True)
    except Exception:
        print(buff_xml)
        print(ElementTree.dump(root))
        raise
    return data

def output_tsv(parsed_buffs, output_path):
    output_path = Path(output_path)

    print("outputting tsv to: {}".format(output_path))

def get_parser():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('dir',
        help='Base directory to search for moodlet / buff information',
        nargs="?", default=str(THIS_DIR / "Extracted"))
    parser.add_argument('output',
        help='Path to output tab-separated-value (.tsv) file',
        nargs="?", default="./md5_hashes.txt")
    return parser

def main(args=sys.argv[1:]):
    parser = get_parser()
    args = parser.parse_args(args)
    parse_and_output_tsv(args.dir, args.output)

if __name__ == '__main__':
    main()