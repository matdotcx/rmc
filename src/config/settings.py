"""Configuration management for RMC application."""

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class AppleDeveloperConfig(BaseModel):
    """Apple Developer credentials for Music API."""
    key_id: Optional[str] = None
    team_id: Optional[str] = None
    key_file_path: Optional[str] = None


class UIConfig(BaseModel):
    """UI preferences."""
    theme: str = "dark"
    show_album_art: bool = True
    update_interval: float = 1.0  # seconds
    inactivity_timeout: int = 30  # seconds (0 = disabled, options: 5, 15, 30)


class IndexConfig(BaseModel):
    """Library index configuration."""
    auto_index_on_launch: bool = True
    auto_index_interval_hours: int = 24  # 0 = disabled
    stale_warning_hours: int = 48


class APIConfig(BaseModel):
    """API configuration."""
    storefront: str = "us"
    developer_token: Optional[str] = None
    developer_token_expiry: Optional[int] = None  # Unix timestamp
    music_user_token: Optional[str] = None


class DaemonConfig(BaseModel):
    """rmcd daemon connection configuration."""
    host: str = "127.0.0.1"
    port: int = 18895
    enabled: bool = True


class AppConfig(BaseModel):
    """Main application configuration."""
    developer: AppleDeveloperConfig = Field(default_factory=AppleDeveloperConfig)
    ui: UIConfig = Field(default_factory=UIConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    index: IndexConfig = Field(default_factory=IndexConfig)
    daemon: DaemonConfig = Field(default_factory=DaemonConfig)


class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file. Defaults to ~/.config/rmc/config.json
        """
        if config_path is None:
            config_dir = Path.home() / ".config" / "rmc"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"

        self.config_path = config_path
        self._config: Optional[AppConfig] = None

    def load(self) -> AppConfig:
        """Load configuration from file.

        Returns:
            Loaded configuration

        If the config file doesn't exist, returns default configuration.
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            self._config = AppConfig()
            return self._config

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                self._config = AppConfig(**data)
                return self._config
        except (json.JSONDecodeError, ValueError) as e:
            # If config is corrupted, return default
            self._config = AppConfig()
            return self._config

    def save(self, config: Optional[AppConfig] = None) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save. If None, saves current config.
        """
        if config is not None:
            self._config = config

        if self._config is None:
            return

        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, 'w') as f:
            json.dump(
                self._config.model_dump(),
                f,
                indent=2
            )

    @property
    def config(self) -> AppConfig:
        """Get current configuration, loading if necessary."""
        if self._config is None:
            return self.load()
        return self._config

    def update_developer_config(
        self,
        key_id: Optional[str] = None,
        team_id: Optional[str] = None,
        key_file_path: Optional[str] = None
    ) -> None:
        """Update developer configuration.

        Args:
            key_id: Apple Music API key ID
            team_id: Apple Developer team ID
            key_file_path: Path to .p8 private key file
        """
        config = self.config

        if key_id is not None:
            config.developer.key_id = key_id
        if team_id is not None:
            config.developer.team_id = team_id
        if key_file_path is not None:
            config.developer.key_file_path = key_file_path

        self.save(config)

    def update_api_tokens(
        self,
        developer_token: Optional[str] = None,
        developer_token_expiry: Optional[int] = None,
        music_user_token: Optional[str] = None
    ) -> None:
        """Update API tokens.

        Args:
            developer_token: JWT developer token
            developer_token_expiry: Expiry timestamp
            music_user_token: Music user token
        """
        config = self.config

        if developer_token is not None:
            config.api.developer_token = developer_token
        if developer_token_expiry is not None:
            config.api.developer_token_expiry = developer_token_expiry
        if music_user_token is not None:
            config.api.music_user_token = music_user_token

        self.save(config)

    def is_configured(self) -> bool:
        """Check if basic configuration is complete.

        Returns:
            True if developer credentials are set
        """
        config = self.config
        return bool(
            config.developer.key_id and
            config.developer.team_id and
            config.developer.key_file_path
        )
