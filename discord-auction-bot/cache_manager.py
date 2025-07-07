"""
Gestor de cache optimizado para el bot de subastas
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class CacheManager:
    """Gestor de cache en memoria para optimizar consultas frecuentes"""
    
    def __init__(self, database):
        self.db = database
        
        # Caches con TTL
        self.auction_cache: Dict[int, Dict[str, Any]] = {}
        self.auction_cache_ttl: Dict[int, datetime] = {}
        
        self.bid_cache: Dict[int, List[Dict[str, Any]]] = {}
        self.bid_cache_ttl: Dict[int, datetime] = {}
        
        self.user_cache: Dict[int, Dict[str, Any]] = {}
        self.user_cache_ttl: Dict[int, datetime] = {}
        
        # Cache de contadores
        self.bid_counts: Dict[int, int] = {}
        
        # Configuración de TTL
        self.auction_ttl = timedelta(seconds=30)
        self.bid_ttl = timedelta(seconds=10)
        self.user_ttl = timedelta(seconds=300)
        
        self.cleanup_interval = 60  # Limpiar cache cada 60 segundos
        
    async def get_auction_cached(self, auction_id: int) -> Optional[Dict[str, Any]]:
        """Obtener subasta desde cache o base de datos"""
        current_time = datetime.now()
        
        # Verificar cache
        if (auction_id in self.auction_cache and 
            auction_id in self.auction_cache_ttl and
            current_time < self.auction_cache_ttl[auction_id]):
            return self.auction_cache[auction_id].copy()
        
        # Obtener de base de datos
        try:
            auction = await self.db.get_auction(auction_id)
            if auction:
                # Guardar en cache
                self.auction_cache[auction_id] = auction.copy()
                self.auction_cache_ttl[auction_id] = current_time + self.auction_ttl
                return auction
        except Exception as e:
            logger.error(f"Error al obtener subasta {auction_id} del cache: {e}")
        
        return None
    
    async def get_auction_bids_cached(self, auction_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """Obtener pujas desde cache o base de datos"""
        current_time = datetime.now()
        
        # Verificar cache
        if (auction_id in self.bid_cache and 
            auction_id in self.bid_cache_ttl and
            current_time < self.bid_cache_ttl[auction_id]):
            cached_bids = self.bid_cache[auction_id]
            return cached_bids[:limit]
        
        # Obtener de base de datos
        try:
            bids = await self.db.get_auction_bids(auction_id, max(limit * 3, 20))  # Obtener más para cache
            if bids:
                # Guardar en cache
                self.bid_cache[auction_id] = bids
                self.bid_cache_ttl[auction_id] = current_time + self.bid_ttl
                return bids[:limit]
        except Exception as e:
            logger.error(f"Error al obtener pujas {auction_id} del cache: {e}")
        
        return []
    
    async def invalidate_auction_cache(self, auction_id: int):
        """Invalidar cache de una subasta específica"""
        self.auction_cache.pop(auction_id, None)
        self.auction_cache_ttl.pop(auction_id, None)
        self.bid_cache.pop(auction_id, None)
        self.bid_cache_ttl.pop(auction_id, None)
        self.bid_counts.pop(auction_id, None)
    
    async def invalidate_bid_cache(self, auction_id: int):
        """Invalidar solo cache de pujas"""
        self.bid_cache.pop(auction_id, None)
        self.bid_cache_ttl.pop(auction_id, None)
        self.bid_counts.pop(auction_id, None)
    
    async def update_auction_cache(self, auction_id: int, auction_data: Dict[str, Any]):
        """Actualizar cache de subasta con nuevos datos"""
        current_time = datetime.now()
        self.auction_cache[auction_id] = auction_data.copy()
        self.auction_cache_ttl[auction_id] = current_time + self.auction_ttl
    
    async def increment_bid_count(self, auction_id: int) -> int:
        """Incrementar contador de pujas en cache"""
        if auction_id not in self.bid_counts:
            # Obtener conteo actual de la base de datos
            try:
                bids = await self.db.get_auction_bids(auction_id, 1000)  # Obtener todas
                self.bid_counts[auction_id] = len(bids)
            except:
                self.bid_counts[auction_id] = 0
        
        self.bid_counts[auction_id] += 1
        return self.bid_counts[auction_id]
    
    async def get_bid_count(self, auction_id: int) -> int:
        """Obtener conteo de pujas desde cache"""
        if auction_id in self.bid_counts:
            return self.bid_counts[auction_id]
        
        # Obtener de base de datos
        try:
            bids = await self.db.get_auction_bids(auction_id, 1000)
            count = len(bids)
            self.bid_counts[auction_id] = count
            return count
        except:
            return 0
    
    async def preload_auction_data(self, auction_id: int):
        """Precargar datos de subasta en cache"""
        try:
            # Precargar subasta
            await self.get_auction_cached(auction_id)
            
            # Precargar pujas
            await self.get_auction_bids_cached(auction_id, 10)
            
            logger.debug(f"Datos precargados para subasta {auction_id}")
        except Exception as e:
            logger.error(f"Error al precargar datos de subasta {auction_id}: {e}")
    
    async def cleanup_expired_cache(self):
        """Limpiar entradas de cache expiradas"""
        current_time = datetime.now()
        
        # Limpiar cache de subastas
        expired_auctions = [
            auction_id for auction_id, ttl in self.auction_cache_ttl.items()
            if current_time >= ttl
        ]
        for auction_id in expired_auctions:
            self.auction_cache.pop(auction_id, None)
            self.auction_cache_ttl.pop(auction_id, None)
        
        # Limpiar cache de pujas
        expired_bids = [
            auction_id for auction_id, ttl in self.bid_cache_ttl.items()
            if current_time >= ttl
        ]
        for auction_id in expired_bids:
            self.bid_cache.pop(auction_id, None)
            self.bid_cache_ttl.pop(auction_id, None)
        
        # Limpiar cache de usuarios
        expired_users = [
            user_id for user_id, ttl in self.user_cache_ttl.items()
            if current_time >= ttl
        ]
        for user_id in expired_users:
            self.user_cache.pop(user_id, None)
            self.user_cache_ttl.pop(user_id, None)
        
        if expired_auctions or expired_bids or expired_users:
            logger.debug(f"Cache limpiado: {len(expired_auctions)} subastas, {len(expired_bids)} pujas, {len(expired_users)} usuarios")
    
    async def cleanup_task(self):
        """Tarea de limpieza periódica"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_expired_cache()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error en tarea de limpieza de cache: {e}")
    
    async def get_cache_stats(self) -> Dict[str, int]:
        """Obtener estadísticas del cache"""
        return {
            'auctions_cached': len(self.auction_cache),
            'bids_cached': len(self.bid_cache),
            'users_cached': len(self.user_cache),
            'bid_counts_cached': len(self.bid_counts)
        }
    
    async def cleanup(self):
        """Limpiar todos los caches"""
        self.auction_cache.clear()
        self.auction_cache_ttl.clear()
        self.bid_cache.clear()
        self.bid_cache_ttl.clear()
        self.user_cache.clear()
        self.user_cache_ttl.clear()
        self.bid_counts.clear()
        logger.info("Cache completamente limpiado")
