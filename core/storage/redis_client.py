import redis.asyncio as redis
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
        self.ttl_hours = settings.DATA_TTL_HOURS
    
    async def store_cv_data(self, session_id: str, cv_data: Dict) -> bool:
        """Store CV data with TTL for GDPR compliance"""
        try:
            key = f"cv_data:{session_id}"
            serialized_data = json.dumps(cv_data, ensure_ascii=False)
            
            # Store with TTL
            await self.redis.setex(
                key, 
                timedelta(hours=self.ttl_hours),
                serialized_data
            )
            
            logger.info(f"CV data stored for session {session_id} with {self.ttl_hours}h TTL")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store CV data: {e}")
            return False
    
    async def get_cv_data(self, session_id: str) -> Optional[Dict]:
        """Retrieve CV data"""
        try:
            key = f"cv_data:{session_id}"
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve CV data: {e}")
            return None
    
    async def store_employer_subscription(self, employer_id: str, subscription: Dict) -> bool:
        """Store employer subscription data"""
        try:
            key = f"subscription:{employer_id}"
            serialized_data = json.dumps(subscription, ensure_ascii=False)
            
            # Store with 35-day TTL (5 days grace period)
            await self.redis.setex(
                key,
                timedelta(days=35),
                serialized_data
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store subscription: {e}")
            return False
    
    async def get_employer_subscription(self, employer_id: str) -> Optional[Dict]:
        """Get employer subscription"""
        try:
            key = f"subscription:{employer_id}"
            data = await self.redis.get(key)
            
            if data:
                subscription = json.loads(data)
                # Check if still active
                end_date = datetime.fromisoformat(subscription['end_date'])
                if datetime.utcnow() <= end_date:
                    return subscription
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve subscription: {e}")
            return None
    
    async def store_pay_per_view_credit(self, employer_id: str, candidate_id: str, credit: Dict) -> bool:
        """Store pay-per-view credit"""
        try:
            key = f"ppv_credit:{employer_id}:{candidate_id}"
            serialized_data = json.dumps(credit, ensure_ascii=False)
            
            # Store with 7-day TTL
            await self.redis.setex(
                key,
                timedelta(days=7),
                serialized_data
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store pay-per-view credit: {e}")
            return False
    
    async def get_pay_per_view_credit(self, employer_id: str, candidate_id: str) -> Optional[Dict]:
        """Get pay-per-view credit"""
        try:
            key = f"ppv_credit:{employer_id}:{candidate_id}"
            data = await self.redis.get(key)
            
            if data:
                credit = json.loads(data)
                if not credit.get('used', False):
                    return credit
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve pay-per-view credit: {e}")
            return None
    
    async def record_profile_access(self, access_record: Dict) -> bool:
        """Record profile access for billing"""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            key = f"profile_access:{access_record['employer_id']}:{timestamp}"
            
            serialized_data = json.dumps(access_record, ensure_ascii=False)
            
            # Store for 1 year for billing records
            await self.redis.setex(
                key,
                timedelta(days=365),
                serialized_data
            )
            
            # Also update usage counter
            usage_key = f"usage:{access_record['employer_id']}:profiles"
            await self.redis.incr(usage_key)
            await self.redis.expire(usage_key, timedelta(days=365))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record profile access: {e}")
            return False
    
    async def store_linkedin_token(self, token: str) -> bool:
        """Store LinkedIn access token"""
        try:
            key = "linkedin_token"
            # Store with 60-day TTL (LinkedIn tokens typically last 60 days)
            await self.redis.setex(
                key,
                timedelta(days=60),
                token
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store LinkedIn token: {e}")
            return False
    
    async def get_linkedin_token(self) -> Optional[str]:
        """Get LinkedIn access token"""
        try:
            key = "linkedin_token"
            token = await self.redis.get(key)
            return token.decode() if token else None
            
        except Exception as e:
            logger.error(f"Failed to retrieve LinkedIn token: {e}")
            return None
    
    async def cache_form_analysis(self, url_hash: str, analysis: Dict) -> bool:
        """Cache form analysis results"""
        try:
            key = f"form_analysis:{url_hash}"
            serialized_data = json.dumps(analysis, ensure_ascii=False)
            
            # Cache for 1 hour
            await self.redis.setex(
                key,
                timedelta(hours=1),
                serialized_data
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache form analysis: {e}")
            return False
    
    async def get_cached_form_analysis(self, url_hash: str) -> Optional[Dict]:
        """Get cached form analysis"""
        try:
            key = f"form_analysis:{url_hash}"
            data = await self.redis.get(key)
            
            if data:
                return json.loads(data)
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve cached form analysis: {e}")
            return None
    
    async def cleanup_expired_data(self) -> int:
        """Manual cleanup of expired data (backup for TTL)"""
        try:
            cursor = 0
            cleaned_count = 0
            
            while True:
                cursor, keys = await self.redis.scan(cursor, match="*", count=1000)
                
                for key in keys:
                    ttl = await self.redis.ttl(key)
                    if ttl == -1:  # Key exists but has no TTL
                        # Set default TTL based on key type
                        if key.startswith(b"cv_data:"):
                            await self.redis.expire(key, timedelta(hours=self.ttl_hours))
                        elif key.startswith(b"form_analysis:"):
                            await self.redis.expire(key, timedelta(hours=1))
                        elif key.startswith(b"subscription:"):
                            await self.redis.expire(key, timedelta(days=35))
                        
                        cleaned_count += 1
                
                if cursor == 0:
                    break
            
            logger.info(f"Cleaned up {cleaned_count} keys without TTL")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0
    
    async def get_usage_stats(self, employer_id: str) -> Dict:
        """Get usage statistics for employer"""
        try:
            stats = {}
            
            # Profile accesses this month
            profile_key = f"usage:{employer_id}:profiles"
            profile_count = await self.redis.get(profile_key)
            stats['profiles_accessed'] = int(profile_count) if profile_count else 0
            
            # Subscription status
            subscription = await self.get_employer_subscription(employer_id)
            stats['subscription_active'] = subscription is not None
            
            if subscription:
                stats['subscription_end'] = subscription['end_date']
                stats['candidates_accessed'] = subscription.get('candidates_accessed', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    async def close(self):
        """Close Redis connection"""
        await self.redis.close()