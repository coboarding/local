import requests
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class LinkedInAPI:
    def __init__(self):
        self.client_id = settings.LINKEDIN_CLIENT_ID
        self.client_secret = settings.LINKEDIN_CLIENT_SECRET
        self.access_token = None
        self.base_url = "https://api.linkedin.com/v2"
        
    async def authenticate(self, authorization_code: str) -> bool:
        """Exchange authorization code for access token"""
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': 'http://localhost:8501/callback',  # Streamlit callback
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Store token securely (implement proper token storage)
            await self._store_access_token(self.access_token)
            
            return True
            
        except Exception as e:
            logger.error(f"LinkedIn authentication failed: {e}")
            return False
    
    async def get_open_to_work_candidates(self, filters: Dict = None) -> List[Dict]:
        """Get candidates marked as 'Open to Work'"""
        if not self.access_token:
            raise ValueError("Not authenticated with LinkedIn")
        
        # Note: This requires LinkedIn Talent Solutions partnership
        endpoint = f"{self.base_url}/people"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'q': 'openToWork',
            'start': 0,
            'count': 50
        }
        
        # Add filters if provided
        if filters:
            if filters.get('location'):
                params['location'] = filters['location']
            if filters.get('industry'):
                params['industry'] = filters['industry']
            if filters.get('skills'):
                params['skills'] = filters['skills']
        
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            candidates = []
            
            for element in data.get('elements', []):
                candidate = {
                    'id': element.get('id'),
                    'name': f"{element.get('firstName', '')} {element.get('lastName', '')}",
                    'headline': element.get('headline', ''),
                    'location': element.get('location', {}).get('name', ''),
                    'industry': element.get('industry', ''),
                    'summary': element.get('summary', ''),
                    'profile_url': element.get('siteStandardProfileRequest', {}).get('url', ''),
                    'last_updated': element.get('lastModifiedTime', ''),
                    'open_to_work': True,
                    'preview_only': True  # Full data requires payment
                }
                candidates.append(candidate)
            
            return candidates
            
        except Exception as e:
            logger.error(f"Failed to fetch candidates: {e}")
            return []
    
    async def get_candidate_full_profile(self, candidate_id: str, employer_id: str) -> Dict:
        """Get full candidate profile (requires payment)"""
        
        # Check if employer has valid subscription or pay-per-view credit
        payment_valid = await self._verify_payment(employer_id, candidate_id)
        if not payment_valid:
            raise ValueError("Payment required for full profile access")
        
        endpoint = f"{self.base_url}/people/{candidate_id}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'fields': 'id,firstName,lastName,headline,location,industry,summary,positions,educations,skills,certifications,languages,contactInfo'
        }
        
        try:
            response = requests.get(endpoint, headers=headers, params=params)
            response.raise_for_status()
            
            profile_data = response.json()
            
            # Process and structure the data
            full_profile = {
                'personal_info': {
                    'name': f"{profile_data.get('firstName', '')} {profile_data.get('lastName', '')}",
                    'headline': profile_data.get('headline', ''),
                    'location': profile_data.get('location', {}).get('name', ''),
                    'industry': profile_data.get('industry', ''),
                    'email': profile_data.get('contactInfo', {}).get('emailAddress', ''),
                    'phone': profile_data.get('contactInfo', {}).get('phoneNumbers', [{}])[0].get('number', '')
                },
                'professional_summary': profile_data.get('summary', ''),
                'work_experience': self._format_positions(profile_data.get('positions', {})),
                'education': self._format_education(profile_data.get('educations', {})),
                'skills': self._format_skills(profile_data.get('skills', {})),
                'certifications': self._format_certifications(profile_data.get('certifications', {})),
                'languages': self._format_languages(profile_data.get('languages', {}))
            }
            
            # Record the transaction
            await self._record_profile_access(employer_id, candidate_id)
            
            return full_profile
            
        except Exception as e:
            logger.error(f"Failed to fetch full profile: {e}")
            raise
    
    async def send_connection_request(self, candidate_id: str, message: str) -> bool:
        """Send connection request to candidate"""
        endpoint = f"{self.base_url}/people/{candidate_id}/invitations"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'message': message,
            'invitationType': 'CONNECTION'
        }
        
        try:
            response = requests.post(endpoint, headers=headers, json=data)
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send connection request: {e}")
            return False
    
    async def _verify_payment(self, employer_id: str, candidate_id: str) -> bool:
        """Verify if employer has paid for access"""
        from core.storage.redis_client import RedisClient
        
        redis_client = RedisClient()
        
        # Check monthly subscription
        subscription = await redis_client.get_employer_subscription(employer_id)
        if subscription and subscription['active']:
            return True
        
        # Check pay-per-view credit
        credit = await redis_client.get_pay_per_view_credit(employer_id, candidate_id)
        if credit:
            return True
        
        return False
    
    async def _record_profile_access(self, employer_id: str, candidate_id: str):
        """Record profile access for billing"""
        from core.storage.redis_client import RedisClient
        
        redis_client = RedisClient()
        
        access_record = {
            'employer_id': employer_id,
            'candidate_id': candidate_id,
            'timestamp': datetime.utcnow().isoformat(),
            'cost_usd': settings.PER_CANDIDATE_USD
        }
        
        await redis_client.record_profile_access(access_record)
    
    def _format_positions(self, positions_data: Dict) -> List[Dict]:
        """Format work experience data"""
        positions = []
        for position in positions_data.get('values', []):
            pos = {
                'position': position.get('title', ''),
                'company': position.get('company', {}).get('name', ''),
                'location': position.get('location', {}).get('name', ''),
                'start_date': self._format_date(position.get('startDate')),
                'end_date': self._format_date(position.get('endDate')) or 'Present',
                'description': position.get('description', '')
            }
            positions.append(pos)
        return positions
    
    def _format_education(self, education_data: Dict) -> List[Dict]:
        """Format education data"""
        education = []
        for edu in education_data.get('values', []):
            ed = {
                'degree': edu.get('degree', ''),
                'field': edu.get('fieldOfStudy', ''),
                'institution': edu.get('schoolName', ''),
                'graduation_date': self._format_date(edu.get('endDate'))
            }
            education.append(ed)
        return education
    
    def _format_skills(self, skills_data: Dict) -> Dict:
        """Format skills data"""
        skills = {
            'technical': [],
            'languages': [],
            'soft_skills': []
        }
        
        for skill in skills_data.get('values', []):
            skill_name = skill.get('skill', {}).get('name', '')
            # Simple categorization - could be enhanced with ML
            if any(tech in skill_name.lower() for tech in ['python', 'java', 'javascript', 'sql', 'aws', 'docker']):
                skills['technical'].append(skill_name)
            elif any(lang in skill_name.lower() for lang in ['english', 'spanish', 'french', 'german', 'polish']):
                skills['languages'].append(skill_name)
            else:
                skills['soft_skills'].append(skill_name)
        
        return skills
    
    def _format_certifications(self, cert_data: Dict) -> List[str]:
        """Format certifications data"""
        certifications = []
        for cert in cert_data.get('values', []):
            cert_name = cert.get('name', '')
            cert_year = self._format_date(cert.get('startDate'), year_only=True)
            if cert_year:
                certifications.append(f"{cert_name} - {cert_year}")
            else:
                certifications.append(cert_name)
        return certifications
    
    def _format_languages(self, lang_data: Dict) -> List[str]:
        """Format languages data"""
        languages = []
        for lang in lang_data.get('values', []):
            lang_name = lang.get('language', {}).get('name', '')
            proficiency = lang.get('proficiency', {}).get('name', '')
            if proficiency:
                languages.append(f"{lang_name} ({proficiency})")
            else:
                languages.append(lang_name)
        return languages
    
    def _format_date(self, date_obj: Dict, year_only: bool = False) -> str:
        """Format LinkedIn date object"""
        if not date_obj:
            return ""
        
        year = date_obj.get('year', '')
        month = date_obj.get('month', '')
        
        if year_only:
            return str(year) if year else ""
        
        if year and month:
            return f"{year}-{month:02d}"
        elif year:
            return str(year)
        
        return ""
    
    async def _store_access_token(self, token: str):
        """Store access token securely"""
        from core.storage.redis_client import RedisClient
        
        redis_client = RedisClient()
        await redis_client.store_linkedin_token(token)

# Business Model Implementation
class LinkedInBusinessModel:
    def __init__(self):
        self.monthly_price = settings.MONTHLY_SUBSCRIPTION_USD
        self.per_candidate_price = settings.PER_CANDIDATE_USD
        
    async def process_monthly_subscription(self, employer_id: str, payment_method: str) -> bool:
        """Process monthly subscription payment"""
        from core.storage.redis_client import RedisClient
        
        # Here you would integrate with payment processor (Stripe, PayPal, etc.)
        payment_successful = await self._process_payment(
            amount=self.monthly_price,
            currency="USD",
            payment_method=payment_method,
            description=f"coBoarding Monthly Subscription - {employer_id}"
        )
        
        if payment_successful:
            redis_client = RedisClient()
            subscription = {
                'employer_id': employer_id,
                'active': True,
                'start_date': datetime.utcnow().isoformat(),
                'end_date': (datetime.utcnow() + timedelta(days=30)).isoformat(),
                'price_paid': self.monthly_price,
                'candidates_accessed': 0
            }
            
            await redis_client.store_employer_subscription(employer_id, subscription)
            return True
        
        return False
    
    async def process_per_candidate_payment(self, employer_id: str, candidate_id: str, payment_method: str) -> bool:
        """Process pay-per-candidate payment"""
        
        payment_successful = await self._process_payment(
            amount=self.per_candidate_price,
            currency="USD", 
            payment_method=payment_method,
            description=f"coBoarding Candidate Access - {candidate_id}"
        )
        
        if payment_successful:
            from core.storage.redis_client import RedisClient
            
            redis_client = RedisClient()
            credit = {
                'employer_id': employer_id,
                'candidate_id': candidate_id,
                'purchased_at': datetime.utcnow().isoformat(),
                'price_paid': self.per_candidate_price,
                'used': False
            }
            
            await redis_client.store_pay_per_view_credit(employer_id, candidate_id, credit)
            return True
        
        return False
    
    async def _process_payment(self, amount: float, currency: str, payment_method: str, description: str) -> bool:
        """Mock payment processing - integrate with real payment processor"""
        # TODO: Integrate with Stripe, PayPal, or other payment processor
        logger.info(f"Processing payment: {amount} {currency} - {description}")
        return True  # Mock success