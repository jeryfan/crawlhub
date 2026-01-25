"""Abstract interface for document loader implementations."""

from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """Interface for extract files."""

    @abstractmethod
    async def extract(self):
        raise NotImplementedError
