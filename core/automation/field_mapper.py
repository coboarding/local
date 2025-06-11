import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from core.ai.llm_client import LLMClient

logger = logging.getLogger(__name__)

class FieldType(Enum):
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    DATE = "date"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    FILE = "file"
    PASSWORD = "password"
    NUMBER = "number"
    URL = "url"

@dataclass
class FormField:
    selector: str
    field_type: FieldType
    label: str
    placeholder: str
    required: bool
    value: str = ""
    options: List[str] = None
    validation_pattern: str = ""
    purpose: str = ""
    confidence: float = 0.0

@dataclass
class FieldMapping:
    form_field: FormField
    cv_value: Any
    cv_source_path: str
    mapping_confidence: float
    transformation_needed: bool = False
    transformation_rule: str = ""

class FieldMapper:
    """Intelligent field mapping between CV data and form fields"""
    
    def __init__(self):
        self.llm_client = LLMClient()
        
        # Predefined mapping rules for common patterns
        self.field_patterns = {
            # Personal Information
            r'(first.*name|given.*name|fname)': 'personal_info.name',
            r'(last.*name|family.*name|surname|lname)': 'personal_info.name',
            r'(full.*name|complete.*name|name)': 'personal_info.name',
            r'(email|e-mail|mail)': 'personal_info.email',
            r'(phone|telephone|mobile|cell)': 'personal_info.phone',
            r'(address|location|city|street)': 'personal_info.location',
            r'(linkedin|linked.in)': 'personal_info.linkedin',
            r'(website|portfolio|url|homepage)': 'personal_info.website',
            
            # Professional Information
            r'(current.*position|job.*title|role|position)': 'work_experience.0.position',
            r'(current.*company|employer|organization)': 'work_experience.0.company',
            r'(summary|objective|profile|about)': 'professional_summary',
            r'(experience|work.*history)': 'work_experience',
            r'(education|degree|university|school)': 'education',
            r'(skills|competencies|abilities)': 'skills.technical',
            r'(languages|language.*skills)': 'skills.languages',
            r'(certifications|certificates|certs)': 'certifications',
            
            # Application Specific
            r'(cover.*letter|motivation.*letter)': 'cover_letter',
            r'(salary|compensation|expected.*salary)': 'salary_expectation',
            r'(availability|start.*date|notice.*period)': 'availability',
            r'(references|referees)': 'references',
            r'(cv|resume|curriculum)': 'cv_file'
        }
        
        # Value transformation rules
        self.transformation_rules = {
            'phone_normalize': r'[\s\-\(\)]+',
            'email_normalize': r'\s+',
            'name_split': r'\s+',
            'date_format': r'(\d{4})-(\d{2})-(\d{2})',
            'skills_join': ', ',
            'experience_format': '{position} at {company} ({start_date} - {end_date})'
        }
    
    async def map_cv_to_form(self, cv_data: Dict, form_fields: List[Dict], language: str = "en") -> List[FieldMapping]:
        """Map CV data to form fields using multiple strategies"""
        
        # Convert form fields to structured format
        structured_fields = self._structure_form_fields(form_fields)
        
        # Strategy 1: Pattern-based mapping
        pattern_mappings = self._map_by_patterns(structured_fields, cv_data)
        
        # Strategy 2: AI-powered semantic mapping
        ai_mappings = await self._map_by_ai(structured_fields, cv_data, language)
        
        # Strategy 3: Field type inference
        type_mappings = self._map_by_field_types(structured_fields, cv_data)
        
        # Combine and score mappings
        combined_mappings = self._combine_mappings(pattern_mappings, ai_mappings, type_mappings)
        
        # Apply confidence filtering and ranking
        final_mappings = self._filter_and_rank_mappings(combined_mappings)
        
        return final_mappings
    
    def _structure_form_fields(self, form_fields: List[Dict]) -> List[FormField]:
        """Convert raw form field data to structured FormField objects"""
        
        structured_fields = []
        
        for field in form_fields:
            try:
                # Determine field type
                field_type = self._infer_field_type(field)
                
                # Extract field information
                structured_field = FormField(
                    selector=field.get('selector', ''),
                    field_type=field_type,
                    label=field.get('label', field.get('nearby_text', '')),
                    placeholder=field.get('placeholder', ''),
                    required=field.get('required', False),
                    options=field.get('options', []),
                    validation_pattern=field.get('pattern', ''),
                    purpose=self._infer_field_purpose(field)
                )
                
                structured_fields.append(structured_field)
                
            except Exception as e:
                logger.warning(f"Failed to structure field {field}: {e}")
                continue
        
        return structured_fields
    
    def _infer_field_type(self, field: Dict) -> FieldType:
        """Infer field type based on label and placeholder"""

        label = field.get('label', field.get('nearby_text', ''))
        placeholder = field.get('placeholder', '')

        # TODO: Add more field type inference logic here
        if 'email' in label.lower() or 'email' in placeholder.lower():
            return FieldType.EMAIL
        elif 'phone' in label.lower() or 'phone' in placeholder.lower():
            return FieldType.PHONE
        elif 'name' in label.lower() or 'name' in placeholder.lower():
            return FieldType.NAME
        elif 'address' in label.lower() or 'address' in placeholder.lower():
            return FieldType.ADDRESS
        elif 'linkedin' in label.lower() or 'linkedin' in placeholder.lower():
            return FieldType.LINKEDIN
        elif 'website' in label.lower() or 'website' in placeholder.lower():
            return FieldType.WEBSITE
        elif 'summary' in label.lower() or 'summary' in placeholder.lower():
            return FieldType.SUMMARY
        elif 'experience' in label.lower() or 'experience' in placeholder.lower():
            return FieldType.EXPERIENCE
        elif 'education' in label.lower() or 'education' in placeholder.lower():
            return FieldType.EDUCATION
        elif 'skills' in label.lower() or 'skills' in placeholder.lower():
            return FieldType.SKILLS
        elif 'certifications' in label.lower() or 'certifications' in placeholder.lower():
            return FieldType.CERTIFICATIONS
        else:
            return FieldType.UNKNOWN