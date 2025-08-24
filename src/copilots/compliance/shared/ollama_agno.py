# src/copilots/compliance/shared/ollama_agno.py
"""
Ollama integration for Agno framework
Fixed version with proper id parameter
"""

import requests
import json
import uuid
from typing import Optional, List, Dict, Any, Iterator, AsyncIterator
from agno.models.base import Model


class OllamaForAgno(Model):
    """
    Ollama wrapper for Agno framework
    Properly implements all required methods
    """
    
    def __init__(self, 
                 model: str = "mistral",
                 base_url: str = "http://localhost:11434",
                 temperature: float = 0.7,
                 max_tokens: int = 2000):
        """
        Initialize Ollama for Agno
        
        Args:
            model: Ollama model name
            base_url: Ollama server URL
            temperature: Response creativity (0-1)
            max_tokens: Maximum response length
        """
        # Store configuration
        self.model_name = model
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Generate unique ID for this instance
        instance_id = str(uuid.uuid4())[:8]
        
        # Initialize parent class with both name and id
        # Both parameters are required by Agno Model class
        super().__init__(
            name=f"ollama/{model}",
            id=f"ollama_{model}_{instance_id}"  # Add required id parameter
        )
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test if Ollama is running and model exists"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                
                # Check for exact match or with :latest suffix
                if self.model_name in model_names:
                    print(f"Ollama model '{self.model_name}' ready")
                elif f"{self.model_name}:latest" in model_names:
                    # Update model name to include :latest
                    self.model_name = f"{self.model_name}:latest"
                    print(f"Ollama model '{self.model_name}' ready")
                else:
                    if model_names:
                        # Use first available model
                        self.model_name = model_names[0]
                        print(f"Using available model: {self.model_name}")
                    else:
                        print("No Ollama models found")
            else:
                print("Cannot connect to Ollama")
        except Exception as e:
            print(f"Ollama connection error: {e}")
    
    def invoke(self, messages: Any, **kwargs) -> str:
        """
        Get response from Ollama
        
        Args:
            messages: Input (string, list, or dict)
            **kwargs: Additional parameters
            
        Returns:
            String response from model
        """
        try:
            # Convert input to prompt string
            if isinstance(messages, str):
                prompt = messages
            elif isinstance(messages, list):
                prompt = self._messages_to_prompt(messages)
            elif isinstance(messages, dict):
                prompt = messages.get("content", str(messages))
            else:
                prompt = str(messages)
            
            # Call Ollama API
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False
                },
                # timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                return f"Ollama error: status {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "Ollama timeout - try shorter prompt"
        except Exception as e:
            return f"Ollama error: {str(e)}"
    
    def invoke_stream(self, messages: Any, **kwargs) -> Iterator[str]:
        """Stream responses (returns full response as single chunk)"""
        response = self.invoke(messages, **kwargs)
        yield response
    
    async def ainvoke(self, messages: Any, **kwargs) -> str:
        """Async invoke (uses sync version)"""
        return self.invoke(messages, **kwargs)
    
    async def ainvoke_stream(self, messages: Any, **kwargs) -> AsyncIterator[str]:
        """Async stream (uses sync version)"""
        response = self.invoke(messages, **kwargs)
        yield response
    
    def parse_provider_response(self, response: Any) -> str:
        """Parse provider response"""
        if isinstance(response, str):
            return response
        elif isinstance(response, dict):
            return response.get("response", "")
        return str(response)
    
    def parse_provider_response_delta(self, delta: Any) -> str:
        """Parse streaming delta"""
        return self.parse_provider_response(delta)
    
    def _messages_to_prompt(self, messages: List) -> str:
        """Convert messages to prompt string"""
        if not messages:
            return ""
        
        prompt = ""
        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                if role == "system":
                    prompt += f"System: {content}\n\n"
                elif role == "user":
                    prompt += f"User: {content}\n\n"
                elif role == "assistant":
                    prompt += f"Assistant: {content}\n\n"
            else:
                prompt += str(msg) + "\n\n"
        
        if prompt and not prompt.endswith("Assistant:"):
            prompt += "Assistant:"
        
        return prompt
    
    def run(self, prompt: str) -> str:
        """Simple run method for direct prompts"""
        return self.invoke(prompt)
    
    def response(self, messages: Any) -> str:
        """Response method for compatibility"""
        return self.invoke(messages)