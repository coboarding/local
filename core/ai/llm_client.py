import asyncio
import httpx
import json
from typing import Dict, List, Optional, Any, Union
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with local Ollama LLM models"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.default_model = settings.FORM_ANALYZER_MODEL
        self.cv_model = settings.CV_PARSER_MODEL
        self.timeout = 300  # 5 minutes for large models

    async def generate(self,
                       prompt: str,
                       model: Optional[str] = None,
                       response_format: str = "text",
                       temperature: float = 0.1,
                       max_tokens: Optional[int] = None,
                       system_prompt: Optional[str] = None) -> Union[str, Dict]:
        """Generate response using Ollama model"""

        model = model or self.default_model

        # Prepare the request payload
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens or 2048,
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                generated_text = result.get("response", "")

                # Handle JSON response format
                if response_format == "json":
                    try:
                        return json.loads(generated_text)
                    except json.JSONDecodeError:
                        # Try to extract JSON from the response
                        import re
                        json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
                        if json_match:
                            return json.loads(json_match.group())
                        else:
                            logger.warning(f"Failed to parse JSON from response: {generated_text}")
                            return {"error": "Invalid JSON response", "raw_response": generated_text}

                return generated_text

        except httpx.TimeoutException:
            logger.error(f"Timeout waiting for model {model}")
            raise Exception(f"Model {model} timeout")
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"Failed to connect to Ollama: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise

    async def analyze_cv(self, cv_text: str) -> Dict[str, Any]:
        """Analyze a CV and extract structured information.
        
        Args:
            cv_text: The text content of the CV to analyze
            
        Returns:
            Dict containing structured CV information
            
        Raises:
            Exception: If there's an error during analysis
        """
        prompt = f"""Analyze the following CV and extract the following information in JSON format:
        - skills: List of skills mentioned
        - experience: Years of experience (as a number)
        - role: Current or most recent role
        - education: List of education entries
        
        CV:
        {cv_text}
        
        Return only the JSON object, no other text."""
        
        try:
            result = await self.generate(
                prompt=prompt,
                model=self.cv_model,
                response_format="json",
                temperature=0.1
            )
            
            # Ensure we have the expected structure
            if not isinstance(result, dict):
                return {"error": "Invalid response format from CV analysis"}
                
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing CV: {str(e)}")
            raise Exception(f"Failed to analyze CV: {str(e)}")

    async def chat(self,
                   messages: List[Dict[str, str]],
                   model: Optional[str] = None,
                   temperature: float = 0.1) -> str:
        """Chat interface with conversation history"""

        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Convert chat messages to a single prompt for the generate endpoint
                prompt = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages])
                
                # Use the generate endpoint instead of chat
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model or self.default_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature
                        }
                    }
                )
                response.raise_for_status()

                result = response.json()
                return result.get("response", "")

        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise

    async def analyze_cv(self, cv_text: str, language: str = "en") -> Dict:
        """Specialized CV analysis using structured prompts"""

        system_prompts = {
            "en": "You are an expert form analyzer specialized in job application forms. Identify field types, purposes, and requirements.",
            "pl": "Jesteś ekspertem w analizie formularzy specjalizującym się w formularzach aplikacji o pracę.",
            "de": "Du bist ein Experte für Formularanalyse, spezialisiert auf Bewerbungsformulare."
        }

        prompts = {
            "en": f"""
Analyze this job application form data and provide structured analysis:

Form Data: {json.dumps(form_data, indent=2)}

Provide analysis in JSON format:
{{
    "form_type": "job_application",
    "required_fields": [...],
    "optional_fields": [...],
    "field_mappings": {{
        "selector": {{"type": "...", "purpose": "...", "required": true/false}}
    }},
    "file_upload_fields": [...],
    "submit_buttons": [...],
    "captcha_present": true/false,
    "estimated_completion_time": "...",
    "complexity_level": "simple/medium/complex",
    "special_requirements": [...]
}}
""",
            "pl": f"""
Przeanalizuj dane tego formularza aplikacji o pracę:

Dane formularza: {json.dumps(form_data, indent=2)}

Podaj analizę w formacie JSON:
{{
    "form_type": "job_application",
    "required_fields": [...],
    "optional_fields": [...],
    "field_mappings": {{...}},
    "file_upload_fields": [...],
    "submit_buttons": [...],
    "captcha_present": true/false,
    "estimated_completion_time": "...",
    "complexity_level": "simple/medium/complex",
    "special_requirements": [...]
}}
""",
            "de": f"""
Analysiere diese Bewerbungsformular-Daten:

Formulardaten: {json.dumps(form_data, indent=2)}

Gib die Analyse im JSON-Format aus:
{{
    "form_type": "job_application",
    "required_fields": [...],
    "optional_fields": [...],
    "field_mappings": {{...}},
    "file_upload_fields": [...],
    "submit_buttons": [...],
    "captcha_present": true/false,
    "estimated_completion_time": "...",
    "complexity_level": "simple/medium/complex",
    "special_requirements": [...]
}}
"""
        }

        prompt = prompts.get(language, prompts["en"])
        system_prompt = system_prompts.get(language, system_prompts["en"])

        return await self.generate(
            prompt=prompt,
            model=self.default_model,
            response_format="json",
            system_prompt=system_prompt,
            temperature=0.1
        )

    async def map_cv_to_form(self, cv_data: Dict, form_analysis: Dict, language: str = "en") -> Dict:
        """Map CV data to form fields intelligently"""

        system_prompts = {
            "en": "You are an expert at mapping CV data to job application form fields. Create accurate field mappings.",
            "pl": "Jesteś ekspertem w mapowaniu danych CV na pola formularzy aplikacji o pracę.",
            "de": "Du bist ein Experte im Mapping von Lebenslaufdaten auf Bewerbungsformular-Felder."
        }

        prompts = {
            "en": f"""
Map the CV data to the form fields based on the form analysis.

CV Data: {json.dumps(cv_data, indent=2)}

Form Analysis: {json.dumps(form_analysis, indent=2)}

Create a mapping in JSON format:
{{
    "field_mappings": {{
        "form_field_selector": {{
            "value": "data_from_cv",
            "source": "cv_field_path",
            "confidence": 0.0-1.0,
            "notes": "explanation"
        }}
    }},
    "unmapped_cv_data": [...],
    "unmapped_form_fields": [...],
    "recommendations": [...]
}}
""",
            "pl": f"""
Zmapuj dane CV na pola formularza na podstawie analizy formularza.

Dane CV: {json.dumps(cv_data, indent=2)}

Analiza formularza: {json.dumps(form_analysis, indent=2)}

Utwórz mapowanie w formacie JSON:
{{
    "field_mappings": {{...}},
    "unmapped_cv_data": [...],
    "unmapped_form_fields": [...],
    "recommendations": [...]
}}
""",
            "de": f"""
Mappe die Lebenslaufdaten auf die Formularfelder basierend auf der Formularanalyse.

Lebenslaufdaten: {json.dumps(cv_data, indent=2)}

Formularanalyse: {json.dumps(form_analysis, indent=2)}

Erstelle ein Mapping im JSON-Format:
{{
    "field_mappings": {{...}},
    "unmapped_cv_data": [...],
    "unmapped_form_fields": [...],
    "recommendations": [...]
}}
"""
        }

        prompt = prompts.get(language, prompts["en"])
        system_prompt = system_prompts.get(language, system_prompts["en"])

        return await self.generate(
            prompt=prompt,
            model=self.default_model,
            response_format="json",
            system_prompt=system_prompt,
            temperature=0.2
        )

    async def generate_chat_response(self, user_message: str, cv_data: Dict, conversation_history: List[Dict],
                                     language: str = "en") -> str:
        """Generate contextual chat responses"""

        system_prompts = {
            "en": f"""You are a helpful job application assistant. Help the user with their CV and job search process.
Current CV data: {json.dumps(cv_data, indent=2) if cv_data else 'No CV uploaded yet'}

Be conversational, helpful, and provide specific advice. You can:
1. Review and suggest improvements to CV data
2. Answer questions about job applications
3. Provide career advice
4. Help with form filling strategies
5. Explain the application process

Keep responses concise but informative.""",
            "pl": f"""Jesteś pomocnym asystentem aplikacji o pracę. Pomagaj użytkownikowi z CV i procesem poszukiwania pracy.
Aktualne dane CV: {json.dumps(cv_data, indent=2) if cv_data else 'Nie wgrano jeszcze CV'}

Bądź konwersacyjny, pomocny i udzielaj konkretnych rad.""",
            "de": f"""Du bist ein hilfsreicher Bewerbungsassistent. Hilf dem Benutzer mit seinem Lebenslauf und der Jobsuche.
Aktuelle CV-Daten: {json.dumps(cv_data, indent=2) if cv_data else 'Noch kein CV hochgeladen'}

Sei gesprächig, hilfreich und gib spezifische Ratschläge."""
        }

        # Prepare conversation context
        messages = [{"role": "system", "content": system_prompts.get(language, system_prompts["en"])}]

        # Add conversation history
        for msg in conversation_history[-5:]:  # Last 5 messages for context
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return await self.chat(messages=messages, temperature=0.3)

    async def check_model_availability(self, model: str) -> bool:
        """Check if a model is available in Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()

                models = response.json().get("models", [])
                available_models = [m.get("name", "") for m in models]

                return model in available_models

        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            return False

    async def list_available_models(self) -> List[str]:
        """List all available models in Ollama"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()

                models = response.json().get("models", [])
                return [m.get("name", "") for m in models]

        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def health_check(self) -> bool:
        """Check if Ollama service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def _get_cv_system_prompt(self, cv_text: str, language: str = "en") -> tuple[str, str]:
        """Get the system prompt for CV parsing in the specified language.
        
        Args:
            cv_text: The text content of the CV to analyze
            language: Language code (en, pl, de)
            
        Returns:
            tuple: (system_prompt, prompt) where system_prompt is the system message
                  and prompt is the user message with the CV text
        """
        # System prompts for different languages
        system_prompts = {
            "en": "You are an expert CV/resume parser. Extract structured information from CVs with high accuracy.",
            "pl": "Jesteś ekspertem w analizie CV. Wyciągnij strukturalne informacje z CV z wysoką dokładnością.",
            "de": "Du bist ein Experte für Lebenslauf-Analyse. Extrahiere strukturierte Informationen aus Lebensläufen mit hoher Genauigkeit."
        }

        # Get the system prompt for the specified language, defaulting to English
        system_prompt = system_prompts.get(language, system_prompts["en"])
        
        # Create the user prompt with the CV text
        prompt = f"""Extract and structure the following information from this CV/resume:

1. Personal Information (name, email, phone, location, LinkedIn, website)
2. Professional Summary
3. Work Experience (position, company, dates, description)
4. Education (degree, institution, dates)
5. Skills (technical, languages, soft skills)
6. Certifications
7. Projects

Format the response as valid JSON with the following structure:
{{
    "personal_info": {{
        "name": "...",
        "email": "...",
        "phone": "...",
        "location": "...",
        "linkedin": "...",
        "website": "..."
    }},
    "professional_summary": "...",
    "work_experience": [{{
        "position": "...",
        "company": "...",
        "start_date": "...",
        "end_date": "...",
        "description": "..."
    }}],
    "education": [{{
        "degree": "...",
        "institution": "...",
        "start_date": "...",
        "end_date": "..."
    }}],
    "skills": {{
        "technical": ["...", "..."],
        "languages": ["..."],
        "soft_skills": ["..."]
    }},
    "certifications": ["...", "..."],
    "projects": ["..."]
}}

CV Text:
{cv_text}"""
        
        return system_prompt, prompt

    async def analyze_cv(self, cv_text: str, language: str = "en") -> Dict[str, Any]:
        """
        Analyze a CV/resume and extract structured information.
        
        Args:
            cv_text: The text content of the CV/resume
            language: Language code (en, pl, de)
            
        Returns:
            Dict containing structured CV information
        """
        try:
            system_prompt, prompt = await self._get_cv_system_prompt(cv_text, language)
            
            response = await self.generate(
                prompt=prompt,
                model=self.cv_model,
                response_format="json",
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            # Parse the response if it's a string
            if isinstance(response, str):
                return json.loads(response)
            return response
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CV analysis response: {e}")
            raise ValueError("Failed to parse CV analysis response")
        except Exception as e:
            logger.error(f"Error analyzing CV: {e}")
            raise

    async def analyze_form(self, form_data: Dict, language: str = "en") -> Dict:
        """
        Analyze job application form and suggest field mappings.
        
        Args:
            form_data: Form data to analyze
            language: Language code (en, pl, de)
            
        Returns:
            Dict containing form analysis and field mappings
        """
        # Define system prompts for different languages
        system_prompts = {
            "en": "You are an expert in analyzing job application forms. Analyze the form and suggest field mappings.",
            "pl": "Jesteś ekspertem w analizie formularzy aplikacji do pracy. Analizuj formularz i zalecz poleMappings.",
            "de": "Du bist ein Experte für Formularanalyse. Analyse das Formular und vorschlage FeldMappings."
        }
        
        # Define user prompts for different languages
        prompts = {
            "en": f"""    
Analyze this job application form data and provide structured analysis:

Form Data: {json.dumps(form_data, indent=2)}

Provide analysis in JSON format:
{{
"form_type": "job_application",
"required_fields": [...],
"optional_fields": [...],
"field_mappings": {{
    "selector": {{"type": "...", "purpose": "...", "required": true/false}}
}},
"file_upload_fields": [...],
"submit_buttons": [...],
"captcha_present": true/false,
"estimated_completion_time": "...",
"complexity_level": "simple/medium/complex",
"special_requirements": [...]
}}""",
            "pl": f"""
Analizuj dane formularza aplikacji do pracy i zaproponuj mapowanie pola:    

Dane formularza: {json.dumps(form_data, indent=2)}

Podaj analizę w formacie JSON:
{{
"form_type": "job_application",
"required_fields": [...],
"optional_fields": [...],
"field_mappings": {{
    "selector": {{"type": "...", "purpose": "...", "required": true/false}}
}},
"file_upload_fields": [...],
"submit_buttons": [...],
"captcha_present": true/false,
"estimated_completion_time": "...",
"complexity_level": "simple/medium/complex",
"special_requirements": [...]
}}""",
            "de": f"""
Analysieren Sie die Daten des Bewerbungsformulars und schlagen Sie Feldzuordnungen vor:

Formulardaten: {json.dumps(form_data, indent=2)}

Geben Sie die Analyse im JSON-Format an:
{{
"form_type": "job_application",
"required_fields": [...],
"optional_fields": [...],
"field_mappings": {{
    "selector": {{"type": "...", "purpose": "...", "required": true/false}}
}},
"file_upload_fields": [...],
"submit_buttons": [...],
"captcha_present": true/false,
"estimated_completion_time": "...",
"complexity_level": "simple/medium/complex",
"special_requirements": [...]
}}"""
        }

        try:
            prompt = prompts.get(language, prompts["en"])
            system_prompt = system_prompts.get(language, system_prompts["en"])

            response = await self.generate(
                prompt=prompt,
                model=self.default_model,
                response_format="json",
                system_prompt=system_prompt,
                temperature=0.1
            )
            
            # Parse the response if it's a string
            if isinstance(response, str):
                return json.loads(response)
            return response
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse form analysis response: {e}")
            raise ValueError("Failed to parse form analysis response")
        except Exception as e:
            logger.error(f"Error analyzing form: {e}")
            raise