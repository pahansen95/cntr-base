import os, pathlib, logging
from DevAgent.AgentCtx import Spec
from DevAgent.AgentCtx.CtxUtils import load_filemap, load_project_stats, load_python_stats, load_git_stats

logger = logging.getLogger(__name__)

WORKTREE = pathlib.Path(os.environ['WORK_DIR'])
assert WORKTREE.is_dir()
SRC_DIR = pathlib.Path(os.environ['WORK_SRC'])
assert SRC_DIR.is_dir()
PKG_DIR = SRC_DIR / 'Package'
assert PKG_DIR.is_dir()
DOC_DIR = WORKTREE / 'docs'
assert DOC_DIR.is_dir()

def spec_factory() -> Spec:
  pkg_src = load_filemap(PKG_DIR, frozenset({'*.py', '*.pyi'}))
  assert pkg_src
  requirements = load_filemap(SRC_DIR, frozenset({'requirements.txt',}))
  assert requirements
  src = {
    p.relative_to(SRC_DIR): f for p, f in {
      **dict((PKG_DIR / p, f) for p, f in pkg_src.items()),
      **dict((SRC_DIR / p, f) for p, f in requirements.items()),
    }.items()
  }
  docs = load_filemap(DOC_DIR, frozenset({'*.md', '*.rst', '*.txt'}))

  return {
    'about': {
      'Project': load_project_stats(WORKTREE),
      'Python': load_python_stats(),
      'Git': load_git_stats(WORKTREE),
    },
    'src': src,
    'docs': docs,
    # 'other': [
    #   {
    #     'title': ...,
    #     'content': ...,
    #     'files': load_filemap( WORKTREE / ..., frozenset({ ... }) )
    #   }
    # ]
  }
