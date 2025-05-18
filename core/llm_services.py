"""
Module for interacting with different LLM services.
"""
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

class LLMService:
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = AsyncOpenAI(api_key=self.api_key)
        
    async def generate_response(self, messages: list[dict], **kwargs) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional parameters for the LLM
            
        Returns:
            str: The generated response
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 500)
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}" 