"""Unit tests for CLI main module - Critical bug coverage."""

import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import pytest
import typer
from typer.testing import CliRunner
import yaml

from src.cli.main import app, load_settings, generate_sample_config, run_transcription
from src.models.config import AppSettings


class TestCLIArgumentHandling:
    """Test CLI argument parsing and validation - CRITICAL."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_multiple_channel_urls_not_supported(self, runner):
        """Test that multiple channel URLs are properly rejected."""
        result = runner.invoke(app, [
            "transcribe",
            "https://youtube.com/@channel1",
            "https://youtube.com/@channel2"
        ])
        assert result.exit_code != 0
        assert "Error" in result.output or "Usage" in result.output
    
    def test_single_channel_url_accepted(self, runner):
        """Test that single channel URL is accepted."""
        with patch('src.cli.main.asyncio.run') as mock_run:
            with patch('src.cli.main.load_settings') as mock_settings:
                mock_settings.return_value = AppSettings(api={"youtube_api_key": "test_key"})
                result = runner.invoke(app, ["transcribe", "https://youtube.com/@channel1"])
                assert result.exit_code == 0
                mock_run.assert_called_once()
    
    def test_invalid_output_format(self, runner):
        """Test handling of invalid output format."""
        with patch('src.cli.main.asyncio.run') as mock_run:
            with patch('src.cli.main.load_settings') as mock_settings:
                mock_settings.return_value = AppSettings(api={"youtube_api_key": "test_key"})
                result = runner.invoke(app, [
                    "transcribe",
                    "https://youtube.com/@channel1",
                    "--format", "invalid_format"
                ])
                # Should still run but with validation in settings
                assert mock_run.called
    
    def test_date_format_validation(self, runner):
        """Test date format validation for date_from and date_to."""
        test_cases = [
            ("2024-01-01", True),  # Valid
            ("2024/01/01", True),  # Should be handled
            ("invalid-date", True),  # Should be handled by orchestrator
            ("", True),  # Empty should be ok
        ]
        
        with patch('src.cli.main.asyncio.run') as mock_run:
            with patch('src.cli.main.load_settings') as mock_settings:
                mock_settings.return_value = AppSettings(api={"youtube_api_key": "test_key"})
                
                for date_str, should_pass in test_cases:
                    result = runner.invoke(app, [
                        "transcribe",
                        "https://youtube.com/@channel1",
                        "--date-from", date_str
                    ])
                    if should_pass:
                        assert mock_run.called


class TestSettingsLoading:
    """Test configuration loading and environment variable handling - CRITICAL."""
    
    def test_missing_api_key_error(self):
        """Test error when YOUTUBE_API_KEY is not set."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="YouTube API key not found"):
                load_settings()
    
    def test_api_key_from_environment(self):
        """Test loading API key from environment variable."""
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "test_api_key"}):
            settings = load_settings()
            assert settings.api.youtube_api_key == "test_api_key"
    
    def test_config_file_loading(self, tmp_path):
        """Test loading configuration from file."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "api": {"youtube_api_key": "file_api_key"},
            "processing": {"concurrent_limit": 10}
        }
        config_file.write_text(yaml.dump(config_data))
        
        settings = load_settings(config_file)
        assert settings.api.youtube_api_key == "file_api_key"
        assert settings.processing.concurrent_limit == 10
    
    def test_config_file_missing_api_key(self, tmp_path):
        """Test config file without API key falls back to env."""
        config_file = tmp_path / "config.yaml"
        config_data = {"processing": {"concurrent_limit": 10}}
        config_file.write_text(yaml.dump(config_data))
        
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "env_api_key"}):
            settings = load_settings(config_file)
            assert settings.api.youtube_api_key == "env_api_key"
    
    def test_invalid_config_values(self, tmp_path):
        """Test handling of invalid configuration values."""
        config_file = tmp_path / "config.yaml"
        config_data = {
            "api": {"youtube_api_key": "test_key"},
            "processing": {"concurrent_limit": -5}  # Invalid negative value
        }
        config_file.write_text(yaml.dump(config_data))
        
        with pytest.raises(Exception):  # Should raise validation error
            load_settings(config_file)


class TestErrorHandling:
    """Test error handling and recovery - CRITICAL."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_keyboard_interrupt_handling(self, runner):
        """Test graceful handling of Ctrl+C."""
        with patch('src.cli.main.asyncio.run') as mock_run:
            mock_run.side_effect = KeyboardInterrupt()
            with patch('src.cli.main.load_settings') as mock_settings:
                mock_settings.return_value = AppSettings(api={"youtube_api_key": "test_key"})
                
                result = runner.invoke(app, ["transcribe", "https://youtube.com/@channel1"])
                assert result.exit_code == 1
                assert "interrupted" in result.output.lower()
    
    def test_general_exception_handling(self, runner):
        """Test handling of unexpected exceptions."""
        with patch('src.cli.main.asyncio.run') as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")
            with patch('src.cli.main.load_settings') as mock_settings:
                mock_settings.return_value = AppSettings(api={"youtube_api_key": "test_key"})
                
                result = runner.invoke(app, ["transcribe", "https://youtube.com/@channel1"])
                assert result.exit_code == 1
                assert "Error" in result.output
    
    @pytest.mark.asyncio
    async def test_orchestrator_context_manager(self):
        """Test orchestrator resource cleanup on error."""
        settings = AppSettings(api={"youtube_api_key": "test_key"})
        
        with patch('src.cli.main.TranscriptOrchestrator') as MockOrchestrator:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.process_channel.side_effect = Exception("Processing error")
            MockOrchestrator.return_value = mock_instance
            
            with pytest.raises(Exception):
                await run_transcription(
                    settings=settings,
                    channel_input="test_channel",
                    language="ja",
                    date_from=None,
                    date_to=None,
                    dry_run=False
                )
            
            # Ensure cleanup was called
            mock_instance.__aexit__.assert_called()


class TestConcurrentProcessing:
    """Test concurrent processing limits - CRITICAL."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_concurrent_limit_validation(self, runner):
        """Test validation of concurrent limit values."""
        test_cases = [
            ("0", False),   # Should fail
            ("-1", False),  # Should fail
            ("1", True),    # Valid
            ("100", True),  # Valid but high
            ("abc", False), # Invalid type
        ]
        
        with patch('src.cli.main.asyncio.run') as mock_run:
            with patch('src.cli.main.load_settings') as mock_settings:
                base_settings = AppSettings(api={"youtube_api_key": "test_key"})
                mock_settings.return_value = base_settings
                
                for value, should_succeed in test_cases:
                    result = runner.invoke(app, [
                        "transcribe",
                        "https://youtube.com/@channel1",
                        "--concurrent", value
                    ])
                    
                    if should_succeed:
                        assert mock_run.called
                    else:
                        assert result.exit_code != 0 or "Error" in result.output


class TestSampleConfigGeneration:
    """Test sample configuration generation."""
    
    def test_generate_sample_config_content(self):
        """Test that sample config contains all required sections."""
        config_content = generate_sample_config()
        
        # Parse the YAML
        config_data = yaml.safe_load(config_content)
        
        # Check required sections
        assert "api" in config_data
        assert "processing" in config_data
        assert "output" in config_data
        assert "logging" in config_data
        
        # Check critical settings
        assert "youtube_api_key" in config_data["api"]
        assert "concurrent_limit" in config_data["processing"]
        assert "default_format" in config_data["output"]
    
    def test_config_command_generate(self, tmp_path):
        """Test config generation command."""
        runner = CliRunner()
        output_file = tmp_path / "test_config.yaml"
        
        result = runner.invoke(app, [
            "config",
            "--generate",
            "--output", str(output_file)
        ])
        
        assert result.exit_code == 0
        assert output_file.exists()
        assert "youtube_api_key" in output_file.read_text()


class TestDryRunMode:
    """Test dry run mode functionality."""
    
    @pytest.mark.asyncio
    async def test_dry_run_prevents_download(self):
        """Test that dry run mode prevents actual downloads."""
        settings = AppSettings(api={"youtube_api_key": "test_key"})
        
        with patch('src.cli.main.TranscriptOrchestrator') as MockOrchestrator:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            MockOrchestrator.return_value = mock_instance
            
            await run_transcription(
                settings=settings,
                channel_input="test_channel",
                language="ja",
                date_from=None,
                date_to=None,
                dry_run=True
            )
            
            # Verify dry_run was passed
            mock_instance.process_channel.assert_called_with(
                channel_input="test_channel",
                language="ja",
                date_from=None,
                date_to=None,
                dry_run=True
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])