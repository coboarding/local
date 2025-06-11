import asyncio
import httpx
import json
from typing import Dict, List, Optional, Any, Union
import logging
from config.settings import settings

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
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()

                result = response.json()
                return result.get("message", {}).get("content", "")

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
        except:
            return False
            CV / resume
            parser.Extract
            structured
            information
            from CVs
            with high accuracy.",
            "pl": "Jesteś ekspertem w analizie CV. Wyciągnij strukturalne informacje z CV z wysoką dokładnością.",
            "de": "Du bist ein Experte für Lebenslauf-Analyse. Extrahiere strukturierte Informationen aus Lebensläufen mit hoher Genauigkeit."
        }

        prompts = {
        "en": f"""
Extract and structure the following information from this CV/resume:

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
    "work_experience": [...],
    "education": [...],
    "skills": {{
        "technical": [...],
        "languages": [...],
        "soft_skills": [...]
    }},
    "certifications": [...],
    "projects": [...]
}}

CV Text:
{cv_text}
""",
        "pl": f"""
Wyciągnij i ustrukturyzuj następujące informacje z tego CV:

1. Informacje osobiste (imię, email, telefon, lokalizacja, LinkedIn, strona)
2. Podsumowanie zawodowe
3. Doświadczenie zawodowe (stanowisko, firma, daty, opis)
4. Wykształcenie (stopień, uczelnia, daty)
5. Umiejętności (techniczne, językowe, miękkie)
6. Certyfikaty
7. Projekty

Sformatuj odpowiedź jako poprawny JSON:
{{
    "personal_info": {{...}},
    "professional_summary": "...",
    "work_experience": [...],
    "education": [...],
    "skills": {{...}},
    "certifications": [...],
    "projects": [...]
}}

Tekst CV:
{cv_text}
""",
        "de": f"""
Extrahiere und strukturiere die folgenden Informationen aus diesem Lebenslauf:

1. Persönliche Informationen (Name, E-Mail, Telefon, Ort, LinkedIn, Website)
2. Berufliche Zusammenfassung
3. Berufserfahrung (Position, Unternehmen, Daten, Beschreibung)
4. Ausbildung (Abschluss, Institution, Daten)
5. Fähigkeiten (technisch, Sprachen, Soft Skills)
6. Zertifikate
7. Projekte

Formatiere die Antwort als gültiges JSON:
{{
    "personal_info": {{...}},
    "professional_summary": "...",
    "work_experience": [...],
    "education": [...],
    "skills": {{...}},
    "certifications": [...],
    "projects": [...]
}}

Lebenslauf Text:
{cv_text}
"""

    }

    prompt = prompts.get(language, prompts["en"])
    system_prompt = system_prompts.get(language, system_prompts["en"])

    return await self.generate(
        prompt=prompt,
        model=self.cv_model,
        response_format="json",
        system_prompt=system_prompt,
        temperature=0.1
    )


async def analyze_form(self, form_data: Dict, language: str = "en") -> Dict:
    """Analyze job application form and suggest field mappings"""

    system_prompts = {
        "en": "You are an expert in analyzing job application forms. Analyze the form and suggest field mappings.",
        "pl": "Jesteś ekspertem w analizie formularzy aplikacji do pracy. Analizuj formularz i zalecz poleMappings.",
        "de": "Du bist ein Experte für Formularanalyse. Analyse das Formular und vorschlage FeldMappings."
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
Analyse diese Bewerbungsformular-Daten und schlage ein FeldMappings vor:

Formular-Daten: {json.dumps(form_data, indent=2)}            

Gib die Analyse im JSON-Format an:
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

    prompt = prompts.get(language, prompts["en"])
    system_prompt = system_prompts.get(language, system_prompts["en"])

    return await self.generate(
        prompt=prompt,
        model=self.form_model,
        response_format="json",
        system_prompt=system_prompt,
        temperature=0.1
    )