"""
Bot optimizado de subastas de Discord con mejoras de latencia
"""
import discord
from discord.ext import commands
import asyncio
import logging
import os
from datetime import datetime

from database import AuctionDatabase
from commands import AuctionCommands
from utils import AuctionUtils
from timer_manager import TimerManager
from views import AuctionView
from cache_manager import CacheManager
from config import BotConfig

# Configurar logging optimizado para Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Solo stdout para Railway log aggregation
    ]
)
logger = logging.getLogger(__name__)

class OptimizedAuctionBot(commands.Bot):
    """Bot optimizado de subastas con mejoras de rendimiento"""
    
    def __init__(self):
        # Configurar intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Inicializar componentes
        self.config = BotConfig()
        self.db = None
        self.utils = None
        self.timer_manager = None
        self.cache_manager = None
        
        # Cooldowns para prevenir spam
        self.user_cooldowns = {}
        self.bid_processing = set()  # IDs de usuarios actualmente procesando pujas
        
    async def setup_hook(self):
        """Configuración inicial del bot"""
        try:
            # Inicializar base de datos
            self.db = AuctionDatabase('auctions.db')
            await self.db.initialize()
            
            # Inicializar cache manager
            self.cache_manager = CacheManager(self.db)
            
            # Inicializar utilidades
            self.utils = AuctionUtils(self)
            
            # Inicializar timer manager
            self.timer_manager = TimerManager(self)
            
            # Añadir comandos
            await self.add_cog(AuctionCommands(self))
            
            # Sincronizar comandos slash
            await self.tree.sync()
            logger.info("Comandos sincronizados exitosamente")
            
        except Exception as e:
            logger.error(f"Error en setup_hook: {e}")
            raise
    
    async def on_ready(self):
        """Evento cuando el bot está listo"""
        logger.info(f'{self.user} está conectado y listo!')
        logger.info(f'Bot conectado a {len(self.guilds)} servidores')
        
        # Recuperar subastas activas
        if self.timer_manager:
            await self.timer_manager.recover_active_auctions()
        
        # Limpiar cache periodicamente
        if self.cache_manager:
            asyncio.create_task(self.cache_manager.cleanup_task())
    
    async def on_error(self, event, *args, **kwargs):
        """Manejo de errores globales"""
        logger.error(f'Error en evento {event}', exc_info=True)
    
    def is_admin(self, user: discord.Member) -> bool:
        """Verificar si un usuario es administrador"""
        return user.guild_permissions.administrator
    
    def get_auction_member_role(self, guild: discord.Guild) -> discord.Role:
        """Obtener rol de miembros de subasta"""
        try:
            # Buscar por varios nombres posibles del rol
            role_names = ["Auction member", "auction member", "Auction Member", "AUCTION MEMBER", "Miembros de Subasta"]
            for role_name in role_names:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    return role
            return None
        except Exception as e:
            logger.warning(f"Error obteniendo rol Auction member: {e}")
            return None
    
    async def is_user_on_cooldown(self, user_id: int) -> bool:
        """Verificar si un usuario está en cooldown"""
        current_time = datetime.now()
        if user_id in self.user_cooldowns:
            cooldown_end = self.user_cooldowns[user_id]
            if current_time < cooldown_end:
                return True
        return False
    
    async def set_user_cooldown(self, user_id: int, seconds: float = 2.0):
        """Establecer cooldown para un usuario"""
        from datetime import timedelta
        self.user_cooldowns[user_id] = datetime.now() + timedelta(seconds=seconds)
    
    async def is_bid_processing(self, user_id: int) -> bool:
        """Verificar si el usuario está procesando una puja"""
        return user_id in self.bid_processing
    
    async def set_bid_processing(self, user_id: int, processing: bool = True):
        """Marcar/desmarcar usuario como procesando puja"""
        if processing:
            self.bid_processing.add(user_id)
        else:
            self.bid_processing.discard(user_id)
    
    async def close(self):
        """Limpiar recursos al cerrar el bot"""
        try:
            if self.timer_manager:
                await self.timer_manager.cleanup()
            
            if self.cache_manager:
                await self.cache_manager.cleanup()
                
            if self.db and self.db.connection:
                await self.db.connection.close()
            
            await super().close()
            logger.info("Bot cerrado correctamente")
        except Exception as e:
            logger.error(f"Error al cerrar el bot: {e}")

async def main():
    """Función principal"""
    try:
        # Obtener token del bot
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            logger.error("Token de Discord no encontrado en variables de entorno")
            return
        
        # Crear y ejecutar bot
        bot = OptimizedAuctionBot()
        async with bot:
            await bot.start(token)
            
    except KeyboardInterrupt:
        logger.info("Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")

if __name__ == "__main__":
    asyncio.run(main())
