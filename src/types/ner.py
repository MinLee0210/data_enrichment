from typing import List

from pydantic import BaseModel


class NER(BaseModel):
    persons: List[str]
    organizations: List[str]
    locations: List[str]
    dates: List[str]
    others: List[str]
