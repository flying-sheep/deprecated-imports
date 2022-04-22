from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from types import TracebackType

from docutils import nodes
from docutils.core import publish_doctree
from sphinx.application import Sphinx
from sphinx.io import SphinxStandaloneReader
from sphinx.parsers import RSTParser
from sphinx.util.docutils import docutils_namespace, patch_docutils, sphinx_domains


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
        self.reader = SphinxStandaloneReader()
        self.reader.setup(self.sphinx)
        self.parser = RSTParser()
        self.parser.set_application(self.sphinx)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> bool:
        self.contexts.close()
        self.tmp_dir = None
        self.sphinx = self.reader = self.parser = None
        return False  # don’t suppress

    def parse(self, file: Path) -> nodes.document:
        """Parse a string as reStructuredText with Sphinx application.

        Adapted from sphinx.testing.restructuredtext:parse
        """
        docname = str(file.relative_to(self.src_path).with_suffix(''))
        self.sphinx.env.prepare_settings(docname)
        try:
            self.sphinx.env.temp_data['docname'] = docname
            with sphinx_domains(self.sphinx.env):
                return publish_doctree(
                    file.read_text(),
                    str(file),
                    reader=self.reader,
                    parser=self.parser,
                    settings_overrides=dict(env=self.sphinx.env, gettext_compact=True),
                )
        finally:
            self.sphinx.env.temp_data.pop('docname', None)
