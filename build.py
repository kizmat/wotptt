# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from xml.sax.saxutils import escape as xml_escape

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src', 'mod_toggle_ptt.py')
BUILD = os.path.join(HERE, 'build')
STAGE = os.path.join(BUILD, 'stage')
DIST = os.path.join(HERE, 'dist')
MOD_JSON = os.path.join(HERE, 'mod.json')
LOCAL_JSON = os.path.join(HERE, 'build.local.json')

ARCHIVE_PYC = 'res/scripts/client/gui/mods/mod_toggle_ptt.pyc'

META_TEMPLATE = (
    '<root>\n'
    '    <id>{id}</id>\n'
    '    <version>{version}</version>\n'
    '    <name>{name}</name>\n'
    '    <description>{description}</description>\n'
    '    <author>{author}</author>\n'
    '    <website>{website}</website>\n'
    '</root>\n'
)


def load_json(path):
    with open(path, 'r') as handle:
        return json.load(handle)


def clean():
    if os.path.isdir(BUILD):
        shutil.rmtree(BUILD)
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)


def command_works(command):
    try:
        subprocess.check_call(
            command + ['-c', 'import sys; assert sys.version_info[:2] == (2, 7)'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return True
    except Exception:
        return False


def find_python27():
    if sys.version_info[:2] == (2, 7):
        return [sys.executable]

    env_python = os.environ.get('PYTHON27')
    if env_python and os.path.isfile(env_python):
        command = [env_python]
        if command_works(command):
            return command

    candidates = []
    if os.name == 'nt':
        candidates.extend([
            ['py', '-2.7'],
            [r'C:\Python27\python.exe'],
        ])
    candidates.extend([
        ['python2.7'],
        ['python2'],
    ])

    for command in candidates:
        if command_works(command):
            return command

    raise SystemExit(
        '\nPython 2.7.18 is required to compile WoT bytecode.\n'
        'Install Python 2.7.18 or set the PYTHON27 environment variable to python.exe.\n'
        'Example:\n'
        '  set PYTHON27=C:\\Python27\\python.exe\n'
    )



def verify_source_version(mod):
    with open(SRC, 'r') as handle:
        source = handle.read()
    expected = "MOD_VERSION = '%s'" % mod['version']
    if expected not in source:
        raise SystemExit(
            'Version mismatch: mod.json says %s but src/mod_toggle_ptt.py does not.'
            % mod['version']
        )


def xml_text(value):
    return xml_escape(str(value))

def compile_mod(python27):
    stage_dir = os.path.join(STAGE, 'res', 'scripts', 'client', 'gui', 'mods')
    if not os.path.isdir(stage_dir):
        os.makedirs(stage_dir)

    staged_py = os.path.join(stage_dir, 'mod_toggle_ptt.py')
    staged_pyc = staged_py + 'c'
    shutil.copyfile(SRC, staged_py)

    subprocess.check_call(python27 + ['-m', 'py_compile', staged_py])

    if not os.path.isfile(staged_pyc):
        raise SystemExit('Compilation failed: %s was not created.' % staged_pyc)

    return staged_pyc


def build_wotmod(mod, compiled_pyc):
    if not os.path.isdir(DIST):
        os.makedirs(DIST)

    filename = '%s_%s.wotmod' % (mod['id'], mod['version'])
    output = os.path.join(DIST, filename)

    meta = META_TEMPLATE.format(
        id=xml_text(mod['id']),
        version=xml_text(mod['version']),
        name=xml_text(mod['name']),
        description=xml_text(mod['description']),
        author=xml_text(mod['author']),
        website=xml_text(mod.get('website', ''))
    )

    with zipfile.ZipFile(output, 'w', zipfile.ZIP_STORED) as archive:
        archive.writestr('meta.xml', meta)
        archive.write(compiled_pyc, ARCHIVE_PYC)

    verify_wotmod(output)
    return output


def verify_wotmod(path):
    with zipfile.ZipFile(path, 'r') as archive:
        names = set(archive.namelist())
        required = set(['meta.xml', ARCHIVE_PYC])
        missing = required - names
        if missing:
            raise SystemExit('Invalid .wotmod; missing: %s' % ', '.join(sorted(missing)))

        pyc = archive.read(ARCHIVE_PYC)
        if len(pyc) < 8:
            raise SystemExit('Invalid .pyc payload.')

    print('verified -> %s' % path)


def install_wotmod(wotmod):
    if not os.path.isfile(LOCAL_JSON):
        raise SystemExit(
            'build.local.json not found.\n'
            'Copy build.local.example.json to build.local.json and fill in game_version.'
        )

    local = load_json(LOCAL_JSON)
    game_dir = local.get('game_dir', '').strip()
    game_version = local.get('game_version', '').strip()

    if not game_dir or not game_version:
        raise SystemExit(
            'build.local.json requires both "game_dir" and "game_version".\n'
            'game_version is the exact folder name under World of Tanks\\mods.'
        )

    destination_dir = os.path.join(game_dir, 'mods', game_version)
    if not os.path.isdir(destination_dir):
        os.makedirs(destination_dir)

    destination = os.path.join(destination_dir, os.path.basename(wotmod))
    shutil.copyfile(wotmod, destination)
    print('installed -> %s' % destination)


def main():
    parser = argparse.ArgumentParser(description='Build Toggle Platoon PTT .wotmod')
    parser.add_argument('--install', action='store_true',
                        help='install after building using build.local.json')
    parser.add_argument('--clean', action='store_true',
                        help='clean build/dist and exit')
    args = parser.parse_args()

    if args.clean:
        clean()
        print('cleaned.')
        return

    mod = load_json(MOD_JSON)
    verify_source_version(mod)
    clean()

    python27 = find_python27()
    print('Python 2.7 -> %s' % ' '.join(python27))

    compiled = compile_mod(python27)
    output = build_wotmod(mod, compiled)
    print('built -> %s' % output)

    if args.install:
        install_wotmod(output)

    print('done.')


if __name__ == '__main__':
    main()
