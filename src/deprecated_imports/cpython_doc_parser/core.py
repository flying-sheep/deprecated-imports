from __future__ import annotations

from typing import ClassVar

from docutils import nodes
from docutils.parsers.rst import Directive
from sphinx import addnodes
from sphinx.util.docutils import SphinxDirective


def make_extract_directive_class() -> type[Directive]:
    # sphinx.domains.changeset:VersionChange
    class VersionChange(SphinxDirective):
        deprecations: ClassVar[list[str]] = []

        has_content = True
        required_arguments = 1
        optional_arguments = 1
        final_argument_whitespace = True

        def run(self) -> list[nodes.Element]:
            if (
                self.state.parent
                and (desc := self.state.parent.parent)
                and isinstance(desc, addnodes.desc)
            ):
                self.handle_desc_level_deprecation(desc)
            else:
                self.handle_module_level_deprecation()
            return []

        def handle_desc_level_deprecation(self, desc: addnodes.desc):
            pass  # TODO

        def handle_module_level_deprecation(self):
            mod_name = self.env.ref_context.get('py:module')
            tag_name = self.state.parent.tagname
            if not mod_name:
                return  # not present e.g. in windows.rst
            elif tag_name == 'section':
                # TODO: does not necessarily mean deprecating the whole module, see ast.rst
                type(self).deprecations.append(mod_name)
            elif tag_name == 'list_item' and mod_name == 'email.errors':
                type(self).deprecations += [
                    'email.errors:BoundaryError',
                    'email.errors:MalformedHeaderDefect',
                ]
            elif tag_name == 'block_quote' and mod_name == 'unittest':
                type(self).deprecations += []
            else:
                assert False, f'Unexpected parent tag {tag_name} in {mod_name}'

    return VersionChange
