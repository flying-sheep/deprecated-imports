from __future__ import annotations

import re
from argparse import ArgumentParser
from pathlib import Path
from typing import Sequence, cast

from docutils import nodes
from sphinx.io import SphinxBaseReader

from .core import make_extract_directive_class
from .sphinx import SphinxWrapper


IGNORED_ROLES = {'source', 'issue', 'opcode', 'pdbcmd'}
IGNORED_DIRECTIVES = {
    '2to3fixer',
    'audit-event-table',
    'doctest',
    'availability',
    'awaitablefunction',
    'coroutinefunction',
    'abstractmethod',
    'coroutinemethod',
    'awaitablemethod',
    'audit-event',
    'impl-detail',
    'deprecated-removed',
    'doctest',
    'testsetup',
    'testcode',
    'testcleanup',
    'testoutput',
    'opcode',
    'pdbcommand',
}


def make_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    return parser


def suppress_role_messages(reader: SphinxBaseReader) -> None:
    re_role = re.compile(f'Unknown interpreted text role "({"|".join(IGNORED_ROLES)})"')
    re_domain = re.compile(f'Unknown directive type "({"|".join(IGNORED_DIRECTIVES)})"')

    reader_cls = type(reader)

    def new_doc() -> nodes.document:
        doc = reader_cls.new_document(reader)
        stream_cls = type(doc.reporter.stream)

        def maybe_write(msg: str) -> int:
            if 'ERROR' in msg and (re_role.search(msg) or re_domain.search(msg)):
                return 0
            return stream_cls.write(doc.reporter.stream, msg)

        doc.reporter.stream.write = maybe_write
        return doc

    reader.new_document = new_doc


def main(args: Sequence[str] | None = None) -> None:
    arg_parser = make_arg_parser()
    opts = arg_parser.parse_args(args)
    path = cast(Path, opts.path)

    with SphinxWrapper(path) as parser:
        suppress_role_messages(parser.reader)

        for file in path.rglob('*.rst'):
            ExtractDirective = make_extract_directive_class()
            parser.sphinx.add_directive('deprecated', ExtractDirective, override=True)

            try:
                parser.parse(file)
                if ExtractDirective.deprecations:
                    print(ExtractDirective.deprecations)
            except Exception:
                raise RuntimeError(f'Error processing {file.relative_to(path)}')
