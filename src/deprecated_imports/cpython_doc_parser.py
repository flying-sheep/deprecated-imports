"""Parses the CPython docs’ ``.. deprecated:: ver`` directives."""
from __future__ import annotations

from argparse import ArgumentParser
from collections.abc import Sequence
from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType
from typing import ClassVar, cast

# from sphinx.util.nodes import nested_parse_with_titles
from docutils import nodes
from docutils.nodes import Node
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx
from sphinx.testing.restructuredtext import parse
from sphinx.util.docutils import SphinxDirective, docutils_namespace, patch_docutils


def make_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    return parser


def make_extract_directive_class() -> type[Directive]:
    # sphinx.domains.changeset:VersionChange
    class VersionChange(SphinxDirective):
        mod_name: ClassVar[str | None] = None

        has_content = True
        required_arguments = 1
        optional_arguments = 1
        final_argument_whitespace = True

        def run(self) -> list[Node]:
            if self.state.parent and (desc := self.state.parent.parent).tagname == 'desc':
                print(desc)
            else:
                assert self.state.parent.tagname == 'section'
                if mod_name := self.env.ref_context.get(
                    'py:module'
                ):  # not present e.g. in windows.rst
                    type(self).mod_name = mod_name
            return []

    return VersionChange


@dataclass
class SphinxWrapper:
    src_path: Path
    tmp_dir: Path | None = None
    sphinx: Sphinx | None = None
    contexts: ExitStack = field(default_factory=ExitStack)

    def __enter__(self):
        tmp_dir_mgr = TemporaryDirectory()
        self.tmp_dir = Path(tmp_dir_mgr.name)
        self.contexts.enter_context(tmp_dir_mgr)
        self.contexts.enter_context(patch_docutils(str(self.tmp_dir)))
        self.contexts.enter_context(docutils_namespace())
        (self.tmp_dir / 'conf.py').write_text('project = "extract-deprecated"')
        self.sphinx = Sphinx(
            str(self.src_path), str(self.tmp_dir), str(self.tmp_dir), str(self.tmp_dir), None
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        self.contexts.close()
        self.tmp_dir = None
        self.sphinx = None
        return False  # don’t suppress

    def parse(self, file: Path) -> nodes.document:
        docname = str(file.relative_to(self.src_path).with_suffix(''))
        self.sphinx.env.prepare_settings(docname)
        return parse(self.sphinx, file.read_text(), docname)


def main(args: Sequence[str] | None = None):
    arg_parser = make_arg_parser()
    opts = arg_parser.parse_args(args)
    path = cast(Path, opts.path)

    with SphinxWrapper(path) as parser:
        for file in path.rglob('*.rst'):
            try:
                Extract = make_extract_directive_class()
                parser.sphinx.add_directive('deprecated', Extract, override=True)
                parser.parse(file)
                if Extract.mod_name:
                    print(Extract.mod_name)
            except Exception:
                raise RuntimeError(f'Error processing {file.relative_to(path)}')


if __name__ == '__main__':
    main()
