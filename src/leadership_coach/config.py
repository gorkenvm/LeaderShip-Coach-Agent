from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    tavily_api_key: str | None = Field(None, env="TAVILY_API_KEY")
    model_name: str = Field("gpt-4o-mini", env="MODEL_NAME")
    data_dir: str = Field("data", env="DATA_DIR")
    index_name: str = Field("leadership-coach", env="INDEX_NAME")

    class Config:
        env_file = ".env"

settings = Settings()
