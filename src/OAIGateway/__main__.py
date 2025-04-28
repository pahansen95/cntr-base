"""
The Package Entrypoint
"""
from __future__ import annotations
from typing import *
from collections.abc import *
from types import *

import logging
import os
import sys
import contextlib
import pathlib
import uvicorn
import ssl
from collections import deque

SCRIPT = pathlib.Path(__file__)
CONTEXT = SCRIPT.parent  # The context of Script
logger = logging.getLogger(__package__ if __name__ == '__main__' else __name__)

from OAIGateway.gateway import app

def main(
  args: deque[str],
  kwargs: dict[str, str],
  remainder: deque[str],
  env: dict[str, str],
  stdin: TextIO,
  stdout: TextIO,
) -> bool:

  class E(Exception): ...

  def _pop_arg(name: str) -> str:
    try: return args.popleft()
    except IndexError: raise E(f'missing positional arg: `{name.upper()}`')
  NO_DEFAULT = type('NO_DEFAULT', (), {})
  def _get_kwarg(k: str, default: str | bool | type[NO_DEFAULT] = NO_DEFAULT) -> str:
    assert default is NO_DEFAULT or isinstance(default, (str, bool))
    try: return kwargs.get(k, default) if default is not NO_DEFAULT else kwargs[k]
    except KeyError: raise E(f'Missing Expected Flag: `--{k}`')

  try:
    subcmd = _pop_arg('subcmd') if args else 'serve'

    if subcmd == 'serve':
      # Use command line args with fallback to environment variables
      host = _get_kwarg('listen-host', env.get('LISTEN_HOST', '127.0.0.1'))
      port = int(_get_kwarg('listen-port', env.get('LISTEN_PORT', '8000')))
      log_level = _get_kwarg('log-level', env.get('LOG_LEVEL', 'info').lower())
      
      # Get SSL certificate paths from environment or default location
      cert_path = pathlib.Path(_get_kwarg('cert-path', env.get('CERT_PATH', './cert.pem')))
      key_path = pathlib.Path(_get_kwarg('cert-key', env.get('KEY_PATH', './cert.key')))
      
      if not cert_path.exists() or not key_path.exists():
        logger.warning(f"SSL certificates not found at {cert_path.as_posix()} and {key_path.as_posix()}. Run certs.sh to generate them.")
        raise E('SSL certificates not found')
            
      try:
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_path, key_path)
        logger.info(f"Using SSL certificates from {cert_path} and {key_path}")
        
        logger.info(f"Starting OpenAI API Gateway on https://{host}:{port}")

        uvicorn.run(
          "OAIGateway.gateway:app",
          host=host,
          port=port,
          ssl_keyfile=key_path.as_posix(),
          ssl_certfile=cert_path.as_posix(),
          log_level=log_level.lower(),
        )
      except Exception as e:
        raise E(f'Failed to start server: {str(e)}') from e

    else:
      raise E(f'Unknown Subcommand: {subcmd}')

  except E as e:
    logger.info('CLI Error', exc_info=True)
    logger.critical(str(e))
    return False
  return True

class CLI:

  @classmethod
  @contextlib.contextmanager
  def session(cls):
    try:
      try:
        logging.basicConfig(
          stream=sys.stderr,
          level=os.environ.get('LOG_LEVEL', 'INFO'),
          format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
      except Exception as e:
        logging.basicConfig(stream=sys.stderr, level='INFO')
        logger.critical(f'Bad Log Configuration: {e}')
        yield False
      else:
        logger.debug('inizio')
        yield True  # Any CLI Exceptions will be raised here
    except:
      logger.critical('Unhandled Exception', exc_info=True)
    finally:
      logger.debug('fin')
      logging.shutdown()
      sys.stdout.flush()
      sys.stderr.flush()
  
  @classmethod
  def parse_flag(cls, flag: str) -> tuple[str, str]:
    assert flag.startswith('-')
    if '=' in flag: return flag.lstrip('-').split('=', maxsplit=1)
    else: return flag.lstrip('-'), True

  @classmethod
  def parse_argv(cls, argv: list[str]) -> tuple[deque[str], dict[str, str], deque[str]]:
    """Parses Argv returning ( args, kwargs, remainder )"""
    remainder = []
    if '--' in argv:
      idx = argv.index('--')
      remainder = argv[idx+1:]
      argv = argv[:idx]
    logger.debug(f'{remainder=}')

    args = deque(a for a in argv if not a.startswith('-'))
    logger.debug(f'{args=}')
    flags = dict(CLI.parse_flag(f) for f in argv if f.startswith('-'))
    logger.debug(f'{flags=}')
    return (args, flags, deque(remainder))

if __name__ == "__main__":
  RC = 2
  with CLI.session() as _ok:
    if _ok: RC = 0 if main(
      *CLI.parse_argv(sys.argv[1:]),
      dict(os.environ),
      sys.stdin,
      sys.stdout,
    ) else 1
  exit(RC)
  