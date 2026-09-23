"""Application settings, loaded from environment variables.

Both providers issued at the hackathon (OpenAI and NVIDIA) expose an
OpenAI-compatible chat-completions API, so switching between them is a base URL
and a model name - no code change.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Known OpenAI-compatible endpoints. Add one here rather than in the code.
PROVIDERS = {
    "openai": {"base_url": "https://api.openai.com/v1", "default_model": "gpt-4.1-mini"},
    "nvidia": {"base_url": "https://integrate.api.nvidia.com/v1", "default_model": "meta/llama-3.3-70b-instruct"},
    "custom": {"base_url": "", "default_model": ""},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "kairos"
    app_env: str = "local"
    log_level: str = "INFO"

    # "openai", "nvidia" or "custom". With "custom", set both fields below.
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    agent_max_steps: int = 8
    agent_timeout_seconds: int = 60
    agent_temperature: float = 0.2

    # Protects an organiser-issued key when the service is publicly deployed.
    rate_limit_per_minute: int = 0  # 0 disables the limiter
    # Only enable behind a platform proxy (Render, Fly.io, Railway). When the
    # service is directly reachable, a caller can forge X-Forwarded-For.
    trust_proxy_headers: bool = False
    # The header the platform's own edge sets and a client cannot forge, e.g.
    # "fly-client-ip" on Fly.io. Strongly preferred over X-Forwarded-For: Fly
    # APPENDS the real address to a client-supplied list rather than replacing
    # it, so the first entry is attacker-controlled. Verified against the live
    # deployment, where spoofing that header reset the rate-limit bucket.
    client_ip_header: str = ""

    @property
    def provider_defaults(self) -> dict:
        return PROVIDERS.get(self.llm_provider.lower(), PROVIDERS["custom"])

    @property
    def base_url(self) -> str:
        return self.llm_base_url or self.provider_defaults["base_url"]

    @property
    def model(self) -> str:
        return self.llm_model or self.provider_defaults["default_model"]

    @property
    def llm_enabled(self) -> bool:
        """False when no usable key is configured, so the app still boots for reviewers."""
        key = self.llm_api_key.strip()
        return bool(key) and not key.lower().startswith(("replace", "sk-replace", "your-"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
