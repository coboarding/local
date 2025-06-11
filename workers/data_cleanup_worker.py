import asyncio
import schedule
import time
from datetime import datetime, timedelta
from core.storage.redis_client import RedisClient
import logging

logger = logging.getLogger(__name__)

class DataCleanupWorker:
    def __init__(self):
        self.redis_client = RedisClient()
        self.running = False
    
    async def start(self):
        """Start the cleanup worker"""
        self.running = True
        logger.info("Data cleanup worker started")
        
        # Schedule daily cleanup at 2 AM
        schedule.every().day.at("02:00").do(self.run_cleanup)
        
        # Schedule hourly quick cleanup
        schedule.every().hour.do(self.run_quick_cleanup)
        
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the cleanup worker"""
        self.running = False
        logger.info("Data cleanup worker stopped")
    
    async def run_cleanup(self):
        """Run comprehensive daily cleanup"""
        logger.info("Starting daily data cleanup")
        
        try:
            # Cleanup expired CV data
            cv_cleaned = await self.cleanup_cv_data()
            
            # Cleanup old form analysis cache
            form_cleaned = await self.cleanup_form_cache()
            
            # Cleanup expired subscriptions
            sub_cleaned = await self.cleanup_expired_subscriptions()
            
            # Cleanup old access records
            access_cleaned = await self.cleanup_old_access_records()
            
            # Run Redis cleanup
            redis_cleaned = await self.redis_client.cleanup_expired_data()
            
            logger.info(f"Daily cleanup completed: CV={cv_cleaned}, Forms={form_cleaned}, "
                       f"Subscriptions={sub_cleaned}, Access={access_cleaned}, Redis={redis_cleaned}")
            
        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")
    
    async def run_quick_cleanup(self):
        """Run quick hourly cleanup"""
        try:
            # Just cleanup obvious expired items
            await self.redis_client.cleanup_expired_data()
            logger.debug("Quick cleanup completed")
            
        except Exception as e:
            logger.error(f"Quick cleanup failed: {e}")
    
    async def cleanup_cv_data(self) -> int:
        """Remove CV data older than TTL"""
        cursor = 0
        cleaned = 0
        
        while True:
            cursor, keys = await self.redis_client.redis.scan(
                cursor, match="cv_data:*", count=100
            )
            
            for key in keys:
                # Check if key has expired
                ttl = await self.redis_client.redis.ttl(key)
                if ttl <= 0:
                    await self.redis_client.redis.delete(key)
                    cleaned += 1
            
            if cursor == 0:
                break
        
        return cleaned
    
    async def cleanup_form_cache(self) -> int:
        """Remove old form analysis cache"""
        cursor = 0
        cleaned = 0
        
        while True:
            cursor, keys = await self.redis_client.redis.scan(
                cursor, match="form_analysis:*", count=100
            )
            
            for key in keys:
                ttl = await self.redis_client.redis.ttl(key)
                if ttl <= 0:
                    await self.redis_client.redis.delete(key)
                    cleaned += 1
            
            if cursor == 0:
                break
        
        return cleaned
    
    async def cleanup_expired_subscriptions(self) -> int:
        """Remove expired subscription records"""
        cursor = 0
        cleaned = 0
        
        while True:
            cursor, keys = await self.redis_client.redis.scan(
                cursor, match="subscription:*", count=100
            )
            
            for key in keys:
                data = await self.redis_client.redis.get(key)
                if data:
                    import json
                    subscription = json.loads(data)
                    end_date = datetime.fromisoformat(subscription['end_date'])
                    
                    # Remove if expired more than 5 days ago (grace period)
                    if datetime.utcnow() > end_date + timedelta(days=5):
                        await self.redis_client.redis.delete(key)
                        cleaned += 1
            
            if cursor == 0:
                break
        
        return cleaned
    
    async def cleanup_old_access_records(self) -> int:
        """Remove access records older than 1 year"""
        cursor = 0
        cleaned = 0
        cutoff_date = datetime.utcnow() - timedelta(days=365)
        
        while True:
            cursor, keys = await self.redis_client.redis.scan(
                cursor, match="profile_access:*", count=100
            )
            
            for key in keys:
                data = await self.redis_client.redis.get(key)
                if data:
                    import json
                    access_record = json.loads(data)
                    access_date = datetime.fromisoformat(access_record['timestamp'])
                    
                    if access_date < cutoff_date:
                        await self.redis_client.redis.delete(key)
                        cleaned += 1
            
            if cursor == 0:
                break
        
        return cleaned

# Background worker main function
async def main():
    worker = DataCleanupWorker()
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        worker.stop()
        await worker.redis_client.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())