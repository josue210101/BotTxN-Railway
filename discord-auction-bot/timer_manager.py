"""
Gestor optimizado de temporizadores para subastas
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class TimerManager:
    """Gestor optimizado de temporizadores para finalización automática de subastas"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_timers: Dict[int, asyncio.Task] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Configuración de limpieza optimizada
        self.cleanup_interval = 300  # 5 minutos
        
        # Iniciar tarea de limpieza
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_auctions())
    
    async def schedule_auction_end(self, auction_id: int, end_time: datetime):
        """Programar el final de una subasta de forma optimizada"""
        try:
            # Cancelar timer existente si hay uno
            await self._cancel_timer(auction_id)
            
            # Calcular tiempo hasta el final
            time_until_end = (end_time - datetime.now()).total_seconds()
            
            if time_until_end <= 0:
                # La subasta ya debería haber terminado
                asyncio.create_task(self.end_auction(auction_id))
                return
            
            # Optimización: si queda muy poco tiempo, usar un delay más corto
            if time_until_end < 60:  # Menos de 1 minuto
                time_until_end = max(time_until_end, 1)  # Mínimo 1 segundo
            
            # Crear nueva tarea
            task = asyncio.create_task(self._auction_timer(auction_id, time_until_end))
            self.active_timers[auction_id] = task
            
            logger.info(f"Timer programado para subasta {auction_id}: {time_until_end:.0f} segundos")
            
        except Exception as e:
            logger.error(f"Error al programar timer para subasta {auction_id}: {e}")
    
    async def _auction_timer(self, auction_id: int, delay: float):
        """Timer interno optimizado para una subasta"""
        try:
            # Para delays largos, usar chunks más pequeños para mayor responsividad
            if delay > 300:  # Más de 5 minutos
                while delay > 300:
                    await asyncio.sleep(300)
                    delay -= 300
                    
                    # Verificar si la subasta sigue activa
                    if not await self._is_auction_still_active(auction_id):
                        return
            
            # Sleep final
            if delay > 0:
                await asyncio.sleep(delay)
            
            # Finalizar subasta
            await self.end_auction(auction_id)
            
        except asyncio.CancelledError:
            logger.debug(f"Timer cancelado para subasta {auction_id}")
        except Exception as e:
            logger.error(f"Error en timer de subasta {auction_id}: {e}")
        finally:
            # Limpiar timer de la lista activa
            self.active_timers.pop(auction_id, None)
    
    async def _is_auction_still_active(self, auction_id: int) -> bool:
        """Verificar si una subasta sigue activa"""
        try:
            if not self.bot.cache_manager:
                return True  # Asumir activa si no hay cache
            
            auction = await self.bot.cache_manager.get_auction_cached(auction_id)
            return auction and auction.get('status') == 'active'
        except:
            return True  # En caso de error, asumir activa
    
    async def end_auction(self, auction_id: int) -> bool:
        """Finalizar una subasta de forma optimizada"""
        try:
            # Verificar dependencias
            if not self.bot.db:
                logger.error("Base de datos no inicializada")
                return False
            if not self.bot.utils:
                logger.error("Utilidades no inicializadas")
                return False
            
            # Obtener información de la subasta desde cache
            auction = await self.bot.cache_manager.get_auction_cached(auction_id)
            if not auction:
                logger.warning(f"Subasta {auction_id} no encontrada en cache, verificando DB...")
                auction = await self.bot.db.get_auction(auction_id)
                if not auction:
                    logger.warning(f"Subasta {auction_id} no encontrada")
                    return False
            
            if auction['status'] != 'active':
                logger.debug(f"Subasta {auction_id} ya no está activa (estado: {auction['status']})")
                return True  # Considerar éxito si ya está finalizada
            
            # Obtener ganador (usuario con la puja más alta)
            bids = await self.bot.cache_manager.get_auction_bids_cached(auction_id, 1)
            winner_id = bids[0]['user_id'] if bids else None
            
            # Marcar subasta como finalizada en la base de datos
            success = await self.bot.db.end_auction(auction_id, winner_id)
            if not success:
                logger.error(f"Error al finalizar subasta {auction_id} en la base de datos")
                return False
            
            # Invalidar cache para reflejar el nuevo estado
            await self.bot.cache_manager.invalidate_auction_cache(auction_id)
            
            # Notificar finalización de forma asíncrona
            asyncio.create_task(self._notify_auction_end_async(auction_id))
            
            # Limpiar timer
            await self._cancel_timer(auction_id)
            
            logger.info(f"Subasta {auction_id} finalizada exitosamente. Ganador: {winner_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error al finalizar subasta {auction_id}: {e}")
            return False
    
    async def _notify_auction_end_async(self, auction_id: int):
        """Notificar finalización de subasta de forma asíncrona"""
        try:
            await self.bot.utils.notify_auction_end(auction_id)
        except Exception as e:
            logger.error(f"Error notificando fin de subasta {auction_id}: {e}")
    
    async def _cancel_timer(self, auction_id: int):
        """Cancelar timer de una subasta específica"""
        if auction_id in self.active_timers:
            self.active_timers[auction_id].cancel()
            del self.active_timers[auction_id]
            logger.debug(f"Timer cancelado para subasta {auction_id}")
    
    async def cancel_auction_timer(self, auction_id: int):
        """Cancelar el timer de una subasta (interfaz pública)"""
        await self._cancel_timer(auction_id)
    
    async def recover_active_auctions(self):
        """Recuperar y reprogramar subastas activas al iniciar el bot"""
        try:
            if not self.bot.db:
                logger.error("Base de datos no inicializada para recuperar subastas")
                return
            
            recovered_count = 0
            finalized_count = 0
            
            # Obtener y finalizar subastas expiradas
            expired_auctions = await self.bot.db.get_expired_auctions()
            for auction in expired_auctions:
                await self.end_auction(auction['id'])
                finalized_count += 1
            
            # Obtener subastas aún activas
            for guild in self.bot.guilds:
                try:
                    guild_auctions = await self.bot.db.get_active_auctions(guild.id)
                    
                    for auction in guild_auctions:
                        end_time = datetime.fromisoformat(auction['ends_at'])
                        
                        if end_time > datetime.now():
                            await self.schedule_auction_end(auction['id'], end_time)
                            recovered_count += 1
                        else:
                            await self.end_auction(auction['id'])
                            finalized_count += 1
                            
                except Exception as e:
                    logger.error(f"Error recuperando subastas del servidor {guild.id}: {e}")
            
            logger.info(f"Recuperación completada: {recovered_count} subastas reprogramadas, {finalized_count} finalizadas")
            
        except Exception as e:
            logger.error(f"Error al recuperar subastas activas: {e}")
    
    async def _cleanup_expired_auctions(self):
        """Tarea optimizada de limpieza periódica para subastas expiradas"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                if not self.bot.db:
                    continue
                
                # Obtener y finalizar subastas expiradas
                expired_auctions = await self.bot.db.get_expired_auctions()
                
                finalized_count = 0
                for auction in expired_auctions:
                    if await self.end_auction(auction['id']):
                        finalized_count += 1
                
                if finalized_count > 0:
                    logger.info(f"Limpieza automática: {finalized_count} subastas expiradas finalizadas")
                
            except asyncio.CancelledError:
                logger.info("Tarea de limpieza cancelada")
                break
            except Exception as e:
                logger.error(f"Error en tarea de limpieza: {e}")
    
    async def get_active_timer_count(self) -> int:
        """Obtener número de timers activos"""
        return len(self.active_timers)
    
    async def get_timer_info(self) -> Dict[str, any]:
        """Obtener información detallada de los timers"""
        return {
            'active_timers': len(self.active_timers),
            'cleanup_running': self.cleanup_task and not self.cleanup_task.done(),
            'auction_ids': list(self.active_timers.keys())
        }
    
    async def cleanup(self):
        """Limpiar todos los timers al cerrar el bot"""
        try:
            # Cancelar tarea de limpieza
            if self.cleanup_task and not self.cleanup_task.done():
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Cancelar todos los timers activos
            cleanup_tasks = []
            for auction_id, task in self.active_timers.items():
                task.cancel()
                cleanup_tasks.append(task)
                logger.debug(f"Timer cancelado para subasta {auction_id}")
            
            # Esperar a que todos los timers terminen
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            
            self.active_timers.clear()
            logger.info("Todos los timers han sido limpiados exitosamente")
            
        except Exception as e:
            logger.error(f"Error al limpiar timers: {e}")
