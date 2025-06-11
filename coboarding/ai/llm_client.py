from typing import Dict, Any, Optional
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

class LLMClient:
    """A simple LLM client using LLaMA 7B for handling job application form analysis."""
    
    def __init__(self, model_name: str = "meta-llama/Llama-2-7b-chat-hf"):
        """Initialize the LLaMA model client.
        
        Args:
            model_name: Name or path of the LLaMA model to use.
        """
        load_dotenv()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = model_name
        self.model = None
        self.tokenizer = None
        
    def _load_model(self):
        """Lazily load the LLaMA model and tokenizer."""
        if self.model is None or self.tokenizer is None:
            print(f"Loading {self.model_name}...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None
            )
            if self.device == "cuda":
                self.model = self.model.to(self.device)
    
    async def analyze_form(self, form_data: Dict[str, Any], language: str = "en") -> Dict[str, Any]:
        """Analyze a job application form and suggest field mappings using LLaMA.
        
        Args:
            form_data: Dictionary containing form field data
            language: Language code (en, de, pl)
            
        Returns:
            Dictionary containing form analysis
        """
        self._load_model()
        
        prompt = f"""Analyze the following job application form fields and suggest appropriate field mappings.
        Form fields: {json.dumps(form_data, indent=2)}
        
        Return a JSON object with these fields:
        - form_type: Type of form (e.g., job_application)
        - required_fields: List of required field names
        - field_mappings: Dictionary mapping field names to their types and purposes
        - status: Analysis status
        
        Example:
        {{
            "form_type": "job_application",
            "required_fields": ["first_name", "last_name", "email"],
            "field_mappings": {{
                "first_name": {{"type": "text", "purpose": "Given name"}},
                "last_name": {{"type": "text", "purpose": "Family name"}},
                "email": {{"type": "email", "purpose": "Email address"}}
            }},
            "status": "analysis_complete"
        }}"""
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.7,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract JSON from the response
        try:
            # Find the first { and last } in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
            
        # Fallback to default if parsing fails
        return {
            "form_type": "job_application",
            "required_fields": ["first_name", "last_name", "email"],
            "field_mappings": {
                "first_name": {"type": "text", "purpose": "Given name"},
                "last_name": {"type": "text", "purpose": "Family name"},
                "email": {"type": "email", "purpose": "Email address"}
            },
            "status": "analysis_complete"
        }
    
    async def generate_cover_letter(self, job_description: str, profile: Dict[str, Any]) -> str:
        """Generate a cover letter based on job description and profile using LLaMA.
        
        Args:
            job_description: The job description text
            profile: Dictionary containing user profile information
            
        Returns:
            Generated cover letter text
        """
        self._load_model()
        
        prompt = f"""Generate a professional cover letter based on the following job description and candidate profile.
        
        Job Description:
        {job_description}
        
        Candidate Profile:
        {json.dumps(profile, indent=2)}
        
        The cover letter should be professional, highlight relevant experience, and be tailored to the job description.
        """
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=1024,
            temperature=0.7,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id
        )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test():
        client = LLMClient()
        result = await client.analyze_form({"fields": []})
        print(json.dumps(result, indent=2))
    
    asyncio.run(test())
