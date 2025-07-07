"""
Gestión optimizada de base de datos para el sistema de subastas
"""
import aiosqlite
import logging
import json
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AuctionDatabase:
    """Clase optimizada para manejar la base de datos de subastas"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
        
        # Pool de conexiones simulado con timeout
        self.connection_timeout = 30
        self.busy_timeout = 5000
    
    def _ensure_connection(self):
        """Verificar que la conexión esté disponible"""
        if not self.connection:
            raise RuntimeError("Base de datos no inicializada")
    
    async def initialize(self):
        """Inicializar la base de datos y crear tablas con optimizaciones"""
        try:
            self.connection = await aiosqlite.connect(
                self.db_path,
                timeout=self.connection_timeout
            )
            
            # Configurar optimizaciones de SQLite
            await self.connection.execute("PRAGMA journal_mode = WAL")
            await self.connection.execute("PRAGMA synchronous = NORMAL")
            await self.connection.execute("PRAGMA cache_size = 10000")
            await self.connection.execute("PRAGMA temp_store = MEMORY")
            await self.connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout}")
            
            await self._create_tables()
            await self._create_indexes()
            logger.info("Base de datos inicializada correctamente con optimizaciones")
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {e}")
            raise
    
    async def _safe_execute(self, query: str, params: tuple = ()):
        """Ejecutar query de forma segura con reintentos"""
        if not self.connection:
            raise RuntimeError("Base de datos no inicializada")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self.connection.execute(query, params)
            except aiosqlite.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Backoff exponencial
                    continue
                raise
            except Exception as e:
                logger.error(f"Error en query (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1)
                    continue
                raise
    
    async def _safe_commit(self):
        """Commit seguro con reintentos"""
        if not self.connection:
            raise RuntimeError("Base de datos no inicializada")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.connection.commit()
                return
            except aiosqlite.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))
                    continue
                raise
            except Exception as e:
                logger.error(f"Error en commit (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1)
                    continue
                raise
    
    async def _create_tables(self):
        """Crear las tablas necesarias"""
        if not self.connection:
            raise RuntimeError("Base de datos no inicializada")
            
        # Tabla de subastas optimizada
        await self._safe_execute("""
            CREATE TABLE IF NOT EXISTS auctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                starting_price REAL NOT NULL,
                current_price REAL NOT NULL,
                min_increment REAL NOT NULL,
                payment_material TEXT NOT NULL,
                image_urls TEXT,
                duration_hours INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                ends_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'active',
                winner_id INTEGER,
                message_id INTEGER,
                bid_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabla de pujas optimizada
        await self._safe_execute("""
            CREATE TABLE IF NOT EXISTS bids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                created_at TIMESTAMP NOT NULL,
                is_quick_bid BOOLEAN DEFAULT 0,
                FOREIGN KEY (auction_id) REFERENCES auctions (id)
            )
        """)
        
        # Tabla de configuración del servidor
        await self._safe_execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                auction_channel_id INTEGER,
                min_increment REAL DEFAULT 1.0,
                max_duration_hours INTEGER DEFAULT 24,
                config_data TEXT
            )
        """)
        
        await self._safe_commit()
    
    async def _create_indexes(self):
        """Crear índices para optimizar consultas"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_auctions_guild_id ON auctions(guild_id)",
            "CREATE INDEX IF NOT EXISTS idx_auctions_status ON auctions(status)",
            "CREATE INDEX IF NOT EXISTS idx_auctions_ends_at ON auctions(ends_at)",
            "CREATE INDEX IF NOT EXISTS idx_auctions_creator_id ON auctions(creator_id)",
            "CREATE INDEX IF NOT EXISTS idx_auctions_message_id ON auctions(message_id)",
            "CREATE INDEX IF NOT EXISTS idx_bids_auction_id ON bids(auction_id)",
            "CREATE INDEX IF NOT EXISTS idx_bids_user_id ON bids(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_bids_created_at ON bids(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_bids_auction_created ON bids(auction_id, created_at)"
        ]
        
        for index_query in indexes:
            try:
                await self._safe_execute(index_query)
            except Exception as e:
                logger.warning(f"Error creando índice: {e}")
        
        await self._safe_commit()
        logger.info("Índices de base de datos creados")
    
    async def create_auction(self, auction_data: Dict[str, Any]) -> int:
        """Crear una nueva subasta"""
        self._ensure_connection()
        try:
            cursor = await self._safe_execute("""
                INSERT INTO auctions (
                    guild_id, channel_id, creator_id, title, description,
                    starting_price, current_price, min_increment, payment_material,
                    image_urls, duration_hours, created_at, ends_at, message_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                auction_data['guild_id'],
                auction_data['channel_id'],
                auction_data['creator_id'],
                auction_data['title'],
                auction_data['description'],
                auction_data['starting_price'],
                auction_data['starting_price'],
                auction_data['min_increment'],
                auction_data['payment_material'],
                auction_data.get('image_urls'),
                auction_data['duration_hours'],
                auction_data['created_at'],
                auction_data['ends_at'],
                auction_data.get('message_id')
            ))
            
            await self._safe_commit()
            auction_id = cursor.lastrowid
            if auction_id is None:
                raise RuntimeError("No se pudo obtener ID de subasta")
            return auction_id
        except Exception as e:
            logger.error(f"Error al crear subasta: {e}")
            raise
    
    async def place_bid_optimized(self, auction_id: int, user_id: int, amount: float, is_quick_bid: bool = False) -> tuple[bool, dict]:
        """Realizar una puja optimizada con transacción atómica"""
        self._ensure_connection()
        
        try:
            # Usar transacción para garantizar atomicidad
            await self._safe_execute("BEGIN IMMEDIATE")
            
            # Obtener datos actuales de la subasta con lock (incluir guild_id, channel_id, payment_material)
            cursor = await self._safe_execute("""
                SELECT current_price, min_increment, status, ends_at, title, creator_id, guild_id, channel_id, payment_material
                FROM auctions 
                WHERE id = ? AND status = 'active'
            """, (auction_id,))
            
            auction_data = await cursor.fetchone()
            if not auction_data:
                await self._safe_execute("ROLLBACK")
                return False, {"error": "Subasta no encontrada o inactiva"}
            
            current_price, min_increment, status, ends_at, title, creator_id, guild_id, channel_id, payment_material = auction_data
            
            # Verificar que no sea el creador
            if user_id == creator_id:
                await self._safe_execute("ROLLBACK")
                return False, {"error": "No puedes pujar en tu propia subasta"}
            
            # Verificar tiempo límite
            ends_at_dt = datetime.fromisoformat(ends_at)
            if datetime.now() >= ends_at_dt:
                await self._safe_execute("ROLLBACK")
                return False, {"error": "Subasta expirada"}
            
            # Verificar cantidad mínima
            min_bid = current_price + min_increment
            if amount < min_bid:
                await self._safe_execute("ROLLBACK")
                return False, {"error": f"Puja mínima: {min_bid}"}
            
            # Obtener puja anterior para notificación
            cursor = await self._safe_execute("""
                SELECT user_id, amount FROM bids 
                WHERE auction_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (auction_id,))
            
            previous_bid = await cursor.fetchone()
            previous_user_id = previous_bid[0] if previous_bid else None
            previous_amount = previous_bid[1] if previous_bid else current_price
            
            # Insertar nueva puja
            await self._safe_execute("""
                INSERT INTO bids (auction_id, user_id, amount, created_at, is_quick_bid)
                VALUES (?, ?, ?, ?, ?)
            """, (auction_id, user_id, amount, datetime.now().isoformat(), is_quick_bid))
            
            # Actualizar precio actual y contador de pujas
            await self._safe_execute("""
                UPDATE auctions 
                SET current_price = ?, 
                    bid_count = bid_count + 1,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (amount, auction_id))
            
            # Confirmar transacción
            await self._safe_commit()
            
            # Información para notificaciones (incluir canal y material de pago)
            notification_info = {
                'previous_user_id': previous_user_id,
                'previous_amount': previous_amount,
                'new_amount': amount,
                'auction_title': title,
                'auction_id': auction_id,
                'user_id': user_id,
                'guild_id': guild_id,
                'channel_id': channel_id,
                'payment_material': payment_material
            }
            
            return True, notification_info
            
        except Exception as e:
            try:
                await self._safe_execute("ROLLBACK")
            except:
                pass
            logger.error(f"Error al realizar puja optimizada: {e}")
            return False, {"error": "Error interno del servidor"}
    
    async def get_auction(self, auction_id: int) -> Optional[Dict[str, Any]]:
        """Obtener una subasta por ID con consulta optimizada"""
        self._ensure_connection()
        try:
            cursor = await self._safe_execute("""
                SELECT * FROM auctions WHERE id = ? LIMIT 1
            """, (auction_id,))
            
            row = await cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
        except Exception as e:
            logger.error(f"Error al obtener subasta: {e}")
            return None
    
    async def get_auction_bids(self, auction_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Obtener pujas con consulta optimizada"""
        self._ensure_connection()
        try:
            cursor = await self._safe_execute("""
                SELECT id, auction_id, user_id, amount, created_at, is_quick_bid
                FROM bids 
                WHERE auction_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (auction_id, limit))
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener pujas: {e}")
            return []
    
    async def get_active_auctions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Obtener subastas activas con consulta optimizada"""
        self._ensure_connection()
        try:
            cursor = await self._safe_execute("""
                SELECT * FROM auctions 
                WHERE guild_id = ? AND status = 'active'
                ORDER BY ends_at ASC
                LIMIT 50
            """, (guild_id,))
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener subastas activas: {e}")
            return []
    
    async def end_auction(self, auction_id: int, winner_id: Optional[int] = None) -> bool:
        """Finalizar una subasta"""
        self._ensure_connection()
        try:
            await self._safe_execute("""
                UPDATE auctions 
                SET status = 'ended', winner_id = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (winner_id, auction_id))
            
            await self._safe_commit()
            return True
        except Exception as e:
            logger.error(f"Error al finalizar subasta: {e}")
            return False
    
    async def get_expired_auctions(self) -> List[Dict[str, Any]]:
        """Obtener subastas expiradas"""
        self._ensure_connection()
        try:
            current_time = datetime.now().isoformat()
            cursor = await self._safe_execute("""
                SELECT * FROM auctions 
                WHERE status = 'active' AND ends_at <= ?
            """, (current_time,))
            
            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error al obtener subastas expiradas: {e}")
            return []
    
    async def update_auction_message_id(self, auction_id: int, message_id: int):
        """Actualizar el ID del mensaje de una subasta"""
        self._ensure_connection()
        try:
            await self._safe_execute("""
                UPDATE auctions SET message_id = ?, last_updated = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (message_id, auction_id))
            await self._safe_commit()
        except Exception as e:
            logger.error(f"Error al actualizar message_id: {e}")
    
    async def get_auction_stats(self, auction_id: int) -> Dict[str, int]:
        """Obtener estadísticas rápidas de una subasta"""
        self._ensure_connection()
        try:
            cursor = await self._safe_execute("""
                SELECT 
                    bid_count,
                    (SELECT COUNT(*) FROM bids WHERE auction_id = ? AND is_quick_bid = 1) as quick_bid_count
                FROM auctions 
                WHERE id = ?
            """, (auction_id, auction_id))
            
            row = await cursor.fetchone()
            if row:
                return {
                    'total_bids': row[0] or 0,
                    'quick_bids': row[1] or 0
                }
            return {'total_bids': 0, 'quick_bids': 0}
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            return {'total_bids': 0, 'quick_bids': 0}
