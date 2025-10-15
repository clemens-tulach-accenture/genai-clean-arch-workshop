import os
from pydantic import BaseModel

class Settings(BaseModel):
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    kb_dir: str = os.getenv("KB_DIR", "/app/knowledge-base")
    model: str = os.getenv("MODEL", "gpt-4.1-nano")
    top_k: int = int(os.getenv("TOP_K", "5"))
    fixed_dir: str = os.getenv("FIXED_DIR", "/data/dummy-project/fixed")

settings = Settings()
