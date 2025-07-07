"""
Configuración del bot de subastas optimizado
"""
import os
from typing import List

class BotConfig:
    """Configuración centralizada del bot"""
    
    # Configuración de imágenes
    MAX_IMAGE_SIZE_MB = 8
    ALLOWED_IMAGE_FORMATS = ['PNG', 'JPG', 'JPEG', 'GIF', 'WEBP']
    MAX_IMAGES_PER_AUCTION = 10
    
    # Configuración de subastas
    MIN_AUCTION_DURATION_HOURS = 1
    MAX_AUCTION_DURATION_HOURS = 48
    DEFAULT_MIN_INCREMENT = 1.0
    
    # Configuración de cooldowns (en segundos)
    BID_COOLDOWN = 1.0  # Cooldown entre pujas del mismo usuario
    QUICK_BID_COOLDOWN = 0.5  # Cooldown específico para pujas rápidas
    UPDATE_THROTTLE = 1.0  # Throttle para actualizaciones de mensajes
    
    # Configuración de cache
    AUCTION_CACHE_TTL = 30  # Tiempo de vida del cache de subastas (segundos)
    BID_CACHE_TTL = 10  # Tiempo de vida del cache de pujas (segundos)
    USER_CACHE_TTL = 300  # Tiempo de vida del cache de usuarios (segundos)
    
    # Configuración de base de datos (optimizada para Railway)
    DB_CONNECTION_TIMEOUT = 30
    DB_BUSY_TIMEOUT = 5000  # milisegundos
    DB_PATH = "auctions.db"  # Railway persistent filesystem
    
    # Configuración específica de Railway
    RAILWAY_ENVIRONMENT = True  # Indicador de entorno Railway
    LOG_TO_STDOUT = True  # Railway log aggregation
    ENABLE_HEALTH_CHECK = True  # Para monitoring de Railway
    
    # Configuración de paginación
    MAX_AUCTIONS_PER_PAGE = 10
    MAX_BIDS_DISPLAY = 5
    
    # Colores para embeds
    COLOR_ACTIVE = 0x00ff00
    COLOR_URGENT = 0xff9900  # Menos de 1 hora
    COLOR_EXPIRED = 0xff0000
    COLOR_ERROR = 0xff0000
    COLOR_SUCCESS = 0x00ff00
    COLOR_WARNING = 0xffff00
    
    # Emojis personalizados
    EMOJI_HAMMER = "🔨"
    EMOJI_MONEY = "💰"
    EMOJI_CHART = "📈"
    EMOJI_CLOCK = "⏰"
    EMOJI_TARGET = "🎯"
    EMOJI_CROWN = "👑"
    EMOJI_ID = "🆔"
    EMOJI_CAMERA = "📷"
    EMOJI_FIRE = "🔥"
    EMOJI_LIGHTNING = "⚡"
    
    @classmethod
    def get_bid_cooldown(cls, is_quick_bid: bool = False) -> float:
        """Obtener cooldown apropiado según el tipo de puja"""
        return cls.QUICK_BID_COOLDOWN if is_quick_bid else cls.BID_COOLDOWN
    
    @classmethod
    def get_color_for_time_left(cls, seconds_left: int) -> int:
        """Obtener color según tiempo restante"""
        if seconds_left <= 0:
            return cls.COLOR_EXPIRED
        elif seconds_left <= 3600:  # Menos de 1 hora
            return cls.COLOR_URGENT
        else:
            return cls.COLOR_ACTIVE
