"""Prompt template base class with version tracking."""


class PromptTemplate:
    """Base class for versioned prompt templates."""

    template_id: str = ""
    version: str = "1.0"

    def __init__(self, template_id: str = "", version: str = "1.0"):
        self.template_id = template_id or self.__class__.__name__
        self.version = version

    def render(self, **kwargs: str) -> str:
        raise NotImplementedError

    @property
    def metadata(self) -> dict:
        return {"template_id": self.template_id, "version": self.version}
