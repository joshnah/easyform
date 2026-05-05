from typing import Optional, Any, List
import os
import sys
import subprocess
import tempfile
import time
import re
import logging
from typing import Optional

from back2.providers.base import LLMProvider

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 2.0
DEFAULT_TIMEOUT = 300  # 5 minutes
BEGIN_END_PATTERN = re.compile(r"\[BEGIN\s*\]:([\s\S]*?)\[END\]")


class LocalProvider(LLMProvider):
    """Local LLM provider that drives a bundled Genie executable (Windows-only)."""

    def __init__(
        self,
        model: Optional[str] = None,
        genie_dir: Optional[str] = None,
        genie_exe: Optional[str] = None,
        genie_config: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        timeout: int = DEFAULT_TIMEOUT,
        **kwargs,
    ):
        super().__init__(model or "local")
        self.genie_dir = genie_dir
        self.genie_exe = genie_exe
        self.genie_config = genie_config
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # Internal state
        self._initialized = False
        self._base_dir = None
        self._genie_path = None
        self._config_path = None

    def init_provider(self):
        """Initialize the local provider by locating and validating Genie files."""
        # Determine base directory
        self._base_dir = self._get_base_directory()

        # Set up paths
        self._genie_path = self.genie_exe or os.path.join(
            self._base_dir, "genie-t2t-run.exe"
        )
        self._config_path = self.genie_config or os.path.join(
            self._base_dir, "genie_config.json"
        )

        # Validate files exist
        missing_files = self._validate_model_files()
        if missing_files:
            error_msg = (
                "Local provider validation failed. Missing files:\n"
                + "\n".join(f"  - {f}" for f in missing_files)
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        self._initialized = True
        logger.info("LocalProvider initialized successfully")
        logger.debug(f"Genie executable: {self._genie_path}")
        logger.debug(f"Config file: {self._config_path}")
        logger.debug(f"Base directory: {self._base_dir}")

    def get_client(self):
        """Ensure provider is initialized and return readiness status."""
        if not self._initialized:
            self.init_provider()
        return True

    def _get_base_directory(self) -> str:
        """Get the correct base directory for PyInstaller/frozen or dev environment."""
        if self.genie_dir:
            return self.genie_dir

        if getattr(sys, "frozen", False):  # Running as PyInstaller executable
            # Look for model folder next to the executable
            exe_dir = os.path.dirname(sys.executable)
            model_dir = os.path.join(exe_dir, "model")

            if os.path.exists(model_dir):
                return model_dir

            # Fallback: check _MEIPASS (if model was included in build)
            if hasattr(sys, "_MEIPASS"):
                meipass_model = os.path.join(sys._MEIPASS, "model")
                if os.path.exists(meipass_model):
                    return meipass_model

            # Return attempted path for error reporting
            return model_dir

        # Development environment
        return os.path.dirname(os.path.abspath(__file__))

    def _validate_model_files(self) -> list[str]:
        """Validate that required model files exist. Returns list of missing files."""
        missing_files = []

        if not os.path.exists(self._base_dir):
            missing_files.append(f"Model directory not found: {self._base_dir}")
            return missing_files

        if not os.path.exists(self._genie_path):
            missing_files.append(f"Genie executable not found: {self._genie_path}")

        if not os.path.exists(self._config_path):
            missing_files.append(f"Config file not found: {self._config_path}")

        return missing_files

    def _run_genie_process(self, prompt_file_path: str) -> Optional[str]:
        """Run Genie executable with the given prompt file."""
        logger.debug(f"Running Genie with prompt file: {prompt_file_path}")

        try:
            process = subprocess.Popen(
                [
                    self._genie_path,
                    "-c",
                    self._config_path,
                    "--prompt_file",
                    prompt_file_path,
                ],
                cwd=self._base_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Get output with timeout
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                logger.error(f"Genie process timed out after {self.timeout} seconds")
                return None

            logger.debug(f"Genie return code: {process.returncode}")

            if process.returncode != 0:
                # Decode stderr for error reporting
                try:
                    stderr_text = stderr_bytes.decode("utf-8", errors="replace")
                except Exception:
                    stderr_text = str(stderr_bytes)
                logger.error(
                    f"Genie process failed (code {process.returncode}): {stderr_text[:500]}"
                )
                return None

            # Decode stdout with fallback encodings
            output_text = self._decode_output(stdout_bytes)
            if output_text is None:
                logger.error("Failed to decode Genie output")
                return None

            output_text = output_text.strip()
            logger.debug(f"Raw output length: {len(output_text)}")

            # Extract content between [BEGIN] and [END] markers
            match = BEGIN_END_PATTERN.search(output_text)
            if match:
                extracted = match.group(1).strip()
                logger.debug(f"Extracted content length: {len(extracted)}")
                return extracted
            else:
                logger.debug("No [BEGIN]...[END] markers found in output")
                # If no markers but we have output, return truncated version
                if output_text:
                    logger.debug(f"Returning truncated output (first 4096 chars)")
                    return output_text[:4096]
                return None

        except Exception as e:
            logger.exception(f"Exception running Genie process: {e}")
            return None

    def _decode_output(self, output_bytes: bytes) -> Optional[str]:
        """Decode output bytes with fallback encodings."""
        # Try multiple encodings
        for encoding in ["utf-8", "cp1252", "latin1"]:
            try:
                output_text = output_bytes.decode(encoding)
                logger.debug(f"Successfully decoded output with {encoding}")
                return output_text
            except UnicodeDecodeError:
                continue

        # Last resort: decode with error replacement
        try:
            output_text = output_bytes.decode("utf-8", errors="replace")
            logger.debug("Decoded output with error replacement")
            return output_text
        except Exception:
            return None

    def _create_prompt_file_and_run(self, formatted_prompt: str) -> Optional[str]:
        """Create temporary prompt file and run Genie."""
        # Use system temp directory when frozen, base directory in dev
        temp_dir = (
            tempfile.gettempdir() if getattr(sys, "frozen", False) else self._base_dir
        )

        temp_file = None
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                mode="w+",
                encoding="utf-8",
                suffix=".txt",
                dir=temp_dir,
                delete=False,  # Don't auto-delete for debugging
            )

            # Write formatted prompt
            temp_file.seek(0)
            temp_file.truncate(0)
            temp_file.write(formatted_prompt)
            temp_file.flush()
            temp_file.close()

            logger.debug(f"Created prompt file: {temp_file.name}")

            # Run Genie with the temporary file
            result = self._run_genie_process(temp_file.name)
            return result

        except Exception as e:
            logger.exception(f"Error creating prompt file or running Genie: {e}")
            return None
        finally:
            # Clean up temporary file
            if temp_file and os.path.exists(temp_file.name):
                try:
                    os.unlink(temp_file.name)
                    logger.debug(f"Cleaned up temporary file: {temp_file.name}")
                except Exception as e:
                    logger.warning(
                        f"Could not delete temporary file {temp_file.name}: {e}"
                    )

    def query_gpt(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """
        Query the local model using Genie executable.

        Args:
            prompt: The input prompt
            max_tokens: Ignored for local model
            temperature: Ignored for local model

        Returns:
            The model response text

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If the local model fails permanently
        """
        if not prompt:
            raise ValueError("Prompt must be provided for local model queries")

        # Ensure provider is ready
        self.get_client()

        # Format prompt for Llama3 chat template.
        formatted_prompt = (
            f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>"
            f"{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
        )

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                result = self._create_prompt_file_and_run(formatted_prompt)

                if result is None:
                    raise RuntimeError("Local model returned no content")

                response_text = result.strip()
                logger.debug(
                    f"LocalProvider received response (length: {len(response_text)})"
                )

                if not response_text:
                    logger.warning("Local model returned empty response")
                    return ""

                return response_text

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"LocalProvider attempt {attempt + 1}/{self.max_retries} failed: {e}"
                )

                if attempt >= self.max_retries - 1:
                    logger.error("LocalProvider permanently failed after all retries")
                    return ""

                # Exponential backoff
                backoff_time = self.backoff_factor**attempt
                logger.debug(f"Backing off for {backoff_time} seconds")
                time.sleep(backoff_time)

        # This should not be reached, but just in case
        logger.error("LocalProvider query failed unexpectedly")
        return ""
