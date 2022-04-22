from __future__ import annotations

from typing import ClassVar

from docutils.nodes import Node
from docutils.parsers.rst import Directive
from sphinx.util.docutils import SphinxDirective


def make_extract_directive_class() -> type[Directive]:
    # sphinx.domains.changeset:VersionChange
    class VersionChange(SphinxDirective):
        mod_name: ClassVar[str | None] = None

        has_content = True
        required_arguments = 1
        optional_arguments = 1
        final_argument_whitespace = True

        def run(self) -> list[Node]:
            if self.state.parent and (desc := self.state.parent.parent) and desc.tagname == 'desc':
                assert desc
            else:
                # not present e.g. in windows.rst
                if mod_name := self.env.ref_context.get('py:module'):
                    type(self).mod_name = mod_name

                tag_name = self.state.parent.tagname
                assert (
                    tag_name == 'section'
                    or (tag_name == 'list_item' and mod_name == 'email.errors')
                    or (tag_name == 'block_quote' and mod_name == 'unittest')
                ), f'Unexpected parent tag {tag_name} in {mod_name}'

                # TODO: handle deprecated aliases in unittest manually if possible
            return []

    return VersionChange
