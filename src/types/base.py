from typing import List

from pydantic import BaseModel


class BaseResponse(BaseModel):
    keywords: List[str]
