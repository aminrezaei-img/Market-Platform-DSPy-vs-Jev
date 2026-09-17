"""Internal tool set wrapper - for future extension"""
from ..providers.internal_provider import SyntheticInternalDataProvider

class InternalToolSet:
    def __init__(self, provider: SyntheticInternalDataProvider = None):
        self.provider = provider or SyntheticInternalDataProvider()

    def list_clients(self):
        return self.provider.list_clients()
