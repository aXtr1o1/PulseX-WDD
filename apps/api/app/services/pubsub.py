"""
PulseX-WDD – Upstash Redis Pub/Sub Streaming
Handles serverless SSE distribution to decouple the LLM generation from the client socket.
"""
from __future__ import annotations

import json
import logging
import asyncio
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

async def stream_redis_sse(
    redis_url: str,
    redis_token: str,
    channel_id: str,
) -> AsyncGenerator[str, None]:
    """
    Subscribes to a Redis channel and yields SSE-formatted strings.
    If Upstash credentials are missing, this immediately exits (graceful degradation).
    """
    if not redis_url or not redis_token:
        logger.warning("Upstash credentials missing. Falling back to local generator.")
        return

    # Use native upstash_redis client for Serverless compatibility
    from upstash_redis.asyncio import Redis
    
    redis = Redis(url=redis_url, token=redis_token)
    logger.info(f"Subscribed to Upstash Redis channel: {channel_id}")
    
    # Simple polling subscription loop for serverless (REST-based)
    # Note: For true WebSockets you would use hiredis/aioredis, but Upstash REST
    # allows stateless Lambda-compatible polling.
    
    last_msg_id = 0
    while True:
        try:
            # We use a simple list as a queue for the REST API
            msgs = await redis.lrange(channel_id, 0, -1)
            
            if msgs:
                for msg in msgs:
                    if msg == "[DONE]":
                        yield "data: [DONE]\n\n"
                        await redis.delete(channel_id)
                        return
                    else:
                        yield msg
                
                # Clear read messages
                await redis.delete(channel_id)
                
            await asyncio.sleep(0.1) # 100ms poll rate
            
        except Exception as e:
            logger.error(f"Redis stream error: {e}")
            yield f"data: {json.dumps({'t': ' [Stream Connection Error] '})}\n\n"
            yield "data: [DONE]\n\n"
            break

async def publish_to_redis(
    redis_url: str,
    redis_token: str,
    channel_id: str,
    generator: AsyncGenerator[str, None]
):
    """
    Consumes a local Python generator and pushes tokens to Upstash Redis.
    """
    if not redis_url or not redis_token:
        # If no redis, consume silently (handled by fallback)
        async for _ in generator:
            pass
        return

    from upstash_redis.asyncio import Redis
    redis = Redis(url=redis_url, token=redis_token)
    
    # Clear any stale data
    await redis.delete(channel_id)
    
    try:
        async for chunk in generator:
            # chunk is expected to be raw 'data: {...}\n\n' or similar, we just push the core json
            # but since we formatted it already, let's keep it clean
            await redis.rpush(channel_id, chunk)
            
        await redis.rpush(channel_id, "[DONE]")
        # Set a 60 second TTL so dead streams auto-clean
        await redis.expire(channel_id, 60)
        
    except Exception as e:
        logger.error(f"Failed publishing to Redis: {e}")
        await redis.rpush(channel_id, "[DONE]")
