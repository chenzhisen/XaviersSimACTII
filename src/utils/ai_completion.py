from anthropic import Anthropic
from openai import OpenAI
from typing import Optional

class AICompletion:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def get_completion(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        max_tokens: int = 2000, 
        temperature: float = 0.7
    ) -> Optional[str]:
        """Get completion from the language model with unified interface for all providers."""
        try:
            if isinstance(self.client, Anthropic):
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{
                        "role": "user",
                        "content": user_prompt
                    }]
                )
                return response.content[0].text

            elif isinstance(self.client, OpenAI):
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content

            else:
                raise ValueError(f"Unsupported client type: {type(self.client)}")

        except Exception as e:
            print(f"Error in API call: {str(e)}")
            print(f"Model: {self.model}")
            print(f"System prompt: {system_prompt[:100]}...")
            print(f"User prompt: {user_prompt[:100]}...")
            
            if hasattr(e, 'response'):
                print(f"Response status: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            
            raise 