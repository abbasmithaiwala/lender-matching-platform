"""LLM-based policy extraction service using OpenRouter."""

import asyncio
import json
import logging
from typing import Any, Optional

from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError

from app.config import settings

logger = logging.getLogger(__name__)


class LLMExtractor:
    """Service for extracting structured policy data from text using LLMs via OpenRouter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        """
        Initialize the LLM extractor.

        Args:
            api_key: OpenRouter API key (defaults to settings)
            base_url: OpenRouter base URL (defaults to settings)
            model: Model to use (defaults to settings)
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Initial delay between retries in seconds (exponential backoff)
        """
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = base_url or settings.OPENROUTER_BASE_URL
        self.model = model or settings.OPENROUTER_MODEL
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            logger.warning(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY in environment."
            )

        # Initialize OpenAI client configured for OpenRouter
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                "HTTP-Referer": "https://github.com/yourusername/lender-matching",
                "X-Title": "Lender Matching Platform",
            },
        )

        logger.info(f"Initialized LLMExtractor with model: {self.model}")

    async def extract_with_prompt(
        self,
        content: str,
        prompt: str,
        response_format: Optional[dict] = None,
        temperature: float = 0.2,
        max_tokens: int = 8000,
    ) -> dict[str, Any]:
        """
        Extract structured data from content using a custom prompt.

        Args:
            content: The text content to extract from
            prompt: The extraction prompt template
            response_format: Optional response format specification (e.g., {"type": "json_object"})
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens in response

        Returns:
            Extracted data as dictionary

        Raises:
            ValueError: If API key not configured
            Exception: For API errors after all retries exhausted
        """
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            raise ValueError(
                "OpenRouter API key not configured. Set OPENROUTER_API_KEY environment variable."
            )

        formatted_prompt = prompt.format(content=content)

        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Sending extraction request to {self.model} (attempt {attempt + 1}/{self.max_retries})"
                )

                # Prepare request parameters
                request_params = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a policy extraction assistant that extracts structured data from documents.",
                        },
                        {"role": "user", "content": formatted_prompt},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

                # Add response format if specified
                if response_format:
                    request_params["response_format"] = response_format

                # Make API request
                response = await self.client.chat.completions.create(**request_params)

                # Extract content
                content_text = response.choices[0].message.content

                if not content_text:
                    raise ValueError("Empty response from LLM")

                # Parse JSON response
                try:
                    result = json.loads(content_text)
                    logger.info(f"Successfully extracted data (tokens used: {response.usage.total_tokens})")
                    return result
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Response content: {content_text}")
                    # If JSON parsing fails, return the raw text in a structured format
                    return {"raw_content": content_text, "parsing_error": str(e)}

            except RateLimitError as e:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached for rate limit error")
                    raise

            except APITimeoutError as e:
                logger.warning(f"API timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached for timeout error")
                    raise

            except APIError as e:
                logger.error(f"API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1 and e.status_code >= 500:
                    # Only retry on server errors (5xx)
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("API error not retryable or max retries reached")
                    raise

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries reached for unexpected error")
                    raise

        raise Exception(f"Failed to extract data after {self.max_retries} attempts")

    async def test_connection(self) -> bool:
        """
        Test the connection to OpenRouter API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_prompt = "Respond with a simple JSON object containing a 'status' field set to 'ok'."
            result = await self.extract_with_prompt(
                content="Test connection",
                prompt=test_prompt,
                response_format={"type": "json_object"},
                max_tokens=100,
            )

            if result.get("status") == "ok" or "raw_content" in result:
                logger.info("OpenRouter connection test successful")
                return True
            else:
                logger.warning(f"Unexpected test response: {result}")
                return False

        except Exception as e:
            logger.error(f"OpenRouter connection test failed: {e}")
            return False

    def get_available_models(self) -> list[str]:
        """
        Get a list of recommended models available on OpenRouter.

        Returns:
            List of model identifiers
        """
        return [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "anthropic/claude-3-sonnet",
            "openai/gpt-4-turbo",
            "openai/gpt-4o",
            "meta-llama/llama-3.1-70b-instruct",
            "meta-llama/llama-3.1-405b-instruct",
        ]

    async def switch_model(self, model: str) -> None:
        """
        Switch to a different LLM model.

        Args:
            model: Model identifier (e.g., 'anthropic/claude-3.5-sonnet')
        """
        old_model = self.model
        self.model = model
        logger.info(f"Switched model from {old_model} to {model}")
