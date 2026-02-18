from pydantic import BaseModel


class Image(BaseModel):
    filename: str
    data: str  # base64-encoded


class GenerateRequest(BaseModel):
    selected_text: str
    book_title: str = ""
    chapter_title: str = ""
    toc: str = ""
    images: list[Image] = []
    feedback: str = ""


class Flashcard(BaseModel):
    card_type: str  # "basic" or "cloze"
    front: str
    back: str
    tags: list[str] = []


class GenerateResponse(BaseModel):
    flashcards: list[Flashcard]
    deck_name: str
    images: list[Image] = []


class AddToAnkiRequest(BaseModel):
    flashcards: list[Flashcard]
    deck_name: str
    images: list[Image] = []


class AddToAnkiResponse(BaseModel):
    added: int
    errors: list[str] = []


class RephraseRequest(BaseModel):
    text: str


class RephraseResponse(BaseModel):
    rephrased_text: str
