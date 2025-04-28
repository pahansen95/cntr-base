
from . import Provider
import importlib

PROVIDER_PREFIX = ['backend']

def load_provider(
  provider_name: str,
) -> Provider:
  provider_module = [*PROVIDER_PREFIX, provider_name]
  # TODO: Attempt to dynamically import the provider by name from  using importlib
  raise NotImplementedError