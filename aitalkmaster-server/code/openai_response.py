from pydantic import BaseModel, Field

class CharacterResponse(BaseModel):
    text_response: str = Field(description="character response")

