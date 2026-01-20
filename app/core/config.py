from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"

    database_url: str
    database_url_sync: str | None = None

    redis_url: str = "redis://localhost:6379/0"

    pinecone_api_key: str | None = None
    pinecone_index_host: str | None = None
    pinecone_namespace: str = "default"

    gdrive_service_account_json_path: str | None = None
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()