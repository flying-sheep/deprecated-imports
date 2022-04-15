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
from docutils.nodes import Node
from docutils.parsers.rst import Directive
from sphinx.application import Sphinx
from sphinx.testing.restructuredtext import parse
from sphinx.util.docutils import docutils_namespace, patch_docutils


def make_arg_parser() -> ArgumentParser:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    return parser


def make_extract_mod_directive_class() -> type[Directive]:
    # sphinx.domains.python:PyModule
    class ExtractMod(Directive):
        has_content = False
        final_argument_whitespace = False

        mod_name: ClassVar[str | None] = None

        def run(self) -> list[Node]:
            assert self.mod_name is None
            ExtractMod.mod_name = self.arguments[0].strip()
            return []

    return ExtractMod


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

    def parse(self, file: Path):
        # ExtractMod = make_extract_mod_directive_class()

        # register_directives(module=ExtractMod)

        docname = str(file.relative_to(self.src_path).with_suffix(''))
        self.sphinx.env.prepare_settings(docname)
        parse(self.sphinx, file.read_text(), docname)

        # print(ExtractMod.mod_name)


def main(args: Sequence[str] | None = None):
    arg_parser = make_arg_parser()
    opts = arg_parser.parse_args(args)
    path = cast(Path, opts.path)

    with SphinxWrapper(path) as parser:
        for file in path.rglob('*.rst'):
            try:
                parser.parse(file)
            except Exception:
                raise RuntimeError(f'Error processing {file.relative_to(path)}')


if __name__ == '__main__':
    main()
