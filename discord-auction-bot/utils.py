"""
Utilidades optimizadas para el bot de subastas
"""
import discord
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import json

logger = logging.getLogger(__name__)

class AuctionUtils:
    """Utilidades optimizadas para el manejo de subastas"""
    
    def __init__(self, bot):
        self.bot = bot
        self._update_throttle = {}  # Cache para evitar actualizaciones muy frecuentes
    
    @staticmethod
    def format_number(num):
        """Formatear números con K para miles"""
        if num >= 1000:
            k_value = num / 1000
            if k_value == int(k_value):
                return f"{int(k_value)}K"
            else:
                # Formatear sin decimales innecesarios
                formatted = f"{k_value:.1f}K"
                return formatted.replace('.0K', 'K')
        else:
            return f"{int(num)}" if num == int(num) else f"{num:.0f}"
    
    @staticmethod
    def format_time_remaining(seconds: int) -> str:
        """Formatear tiempo restante de forma optimizada"""
        if seconds <= 0:
            return "⏰ Expirada"
        
        hours, remainder = divmod(seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m restantes"
        elif minutes > 0:
            return f"{minutes}m restantes"
        else:
            return "⚡ Menos de 1 minuto"
    
    async def create_auction_embed(self, auction_id: int) -> discord.Embed:
        """Crear embed optimizado para mostrar una subasta"""
        try:
            # Obtener datos desde cache
            auction = await self.bot.cache_manager.get_auction_cached(auction_id)
            if not auction:
                return self._create_error_embed("Subasta no encontrada")
            
            # Calcular tiempo restante y color
            ends_at = datetime.fromisoformat(auction['ends_at'])
            time_left_seconds = int((ends_at - datetime.now()).total_seconds())
            color = self.bot.config.get_color_for_time_left(time_left_seconds)
            time_str = self.format_time_remaining(time_left_seconds)
            
            # Crear embed base
            embed = discord.Embed(
                title=f"{self.bot.config.EMOJI_HAMMER} **{auction['title']}**",
                description=f"{auction['description']}\n{'─' * 30}",
                color=color,
                timestamp=datetime.now()
            )
            
            # Información básica con formato optimizado
            embed.add_field(
                name=f"{self.bot.config.EMOJI_MONEY} Precio Actual",
                value=f"**{self.format_number(auction['current_price'])}** {auction['payment_material']}",
                inline=True
            )
            
            embed.add_field(
                name=f"{self.bot.config.EMOJI_CHART} Incremento Mínimo",
                value=f"{self.format_number(auction['min_increment'])} {auction['payment_material']}",
                inline=True
            )
            
            embed.add_field(
                name=f"{self.bot.config.EMOJI_CLOCK} Tiempo Restante",
                value=time_str,
                inline=True
            )
            
            # Separador visual
            embed.add_field(name="\u200b", value="\u200b", inline=False)
            
            # Próxima puja mínima con emoji de objetivo
            next_min_bid = auction['current_price'] + auction['min_increment']
            embed.add_field(
                name=f"{self.bot.config.EMOJI_TARGET} Próxima Puja Mínima",
                value=f"**{self.format_number(next_min_bid)}** {auction['payment_material']}",
                inline=True
            )
            
            # Obtener y mostrar ganador actual
            winner_info = await self._get_current_winner_info(auction_id, auction['guild_id'])
            embed.add_field(
                name=f"{self.bot.config.EMOJI_CROWN} Ganador Actual",
                value=winner_info,
                inline=True
            )
            
            # ID de la subasta
            embed.add_field(
                name=f"{self.bot.config.EMOJI_ID} ID de Subasta",
                value=f"`{auction_id}`",
                inline=True
            )
            
            # Agregar imagen si existe
            await self._add_auction_image(embed, auction, 0)
            
            # Agregar historial de pujas recientes
            await self._add_recent_bids_info(embed, auction_id, auction['guild_id'])
            
            # Footer con información del creador
            await self._add_creator_footer(embed, auction)
            
            return embed
            
        except Exception as e:
            logger.error(f"Error al crear embed de subasta: {e}")
            return self._create_error_embed("No se pudo cargar la información de la subasta")
    
    async def create_auction_embed_with_image(self, auction_id: int, image_index: int = 0) -> discord.Embed:
        """Crear embed con imagen específica"""
        try:
            auction = await self.bot.cache_manager.get_auction_cached(auction_id)
            if not auction:
                return self._create_error_embed("Subasta no encontrada")
            
            # Crear embed base
            embed = await self.create_auction_embed(auction_id)
            
            # Reemplazar imagen con índice específico
            await self._add_auction_image(embed, auction, image_index)
            
            return embed
            
        except Exception as e:
            logger.error(f"Error al crear embed con imagen específica: {e}")
            return self._create_error_embed("Error al cargar imagen")
    
    async def _get_current_winner_info(self, auction_id: int, guild_id: int) -> str:
        """Obtener información del ganador actual optimizada"""
        try:
            bids = await self.bot.cache_manager.get_auction_bids_cached(auction_id, 1)
            if not bids:
                return "Sin pujas aún"
            
            user_id = bids[0]['user_id']
            guild = self.bot.get_guild(guild_id)
            
            if guild:
                member = guild.get_member(user_id)
                if member:
                    return member.display_name
            
            # Fallback: intentar obtener usuario directamente
            try:
                user = await self.bot.fetch_user(user_id)
                return user.display_name if user else f"Usuario {user_id}"
            except:
                return f"Usuario {user_id}"
                
        except Exception as e:
            logger.warning(f"Error obteniendo ganador actual: {e}")
            return "Error al cargar"
    
    async def _add_auction_image(self, embed: discord.Embed, auction: Dict[str, Any], image_index: int = 0):
        """Agregar imagen al embed de forma optimizada"""
        try:
            if not auction.get('image_urls'):
                return
            
            image_urls = json.loads(auction['image_urls'])
            if not image_urls or image_index >= len(image_urls):
                return
            
            embed.set_image(url=image_urls[image_index])
            
            # Agregar indicador optimizado si hay múltiples imágenes
            if len(image_urls) > 1:
                embed.add_field(
                    name=f"{self.bot.config.EMOJI_CAMERA} Carrusel",
                    value=f"📷 Imagen {image_index + 1} de {len(image_urls)}\n◀️ ▶️ Navega con los botones",
                    inline=True
                )
                
        except (json.JSONDecodeError, TypeError, IndexError) as e:
            logger.warning(f"Error agregando imagen: {e}")
    
    async def _add_recent_bids_info(self, embed: discord.Embed, auction_id: int, guild_id: int):
        """Agregar información de pujas recientes"""
        try:
            recent_bids = await self.bot.cache_manager.get_auction_bids_cached(auction_id, 15)
            if not recent_bids:
                return
            
            bid_text = ""
            guild = self.bot.get_guild(guild_id)
            
            for i, bid in enumerate(recent_bids[:5], 1):  # Mostrar las 5 más recientes
                user_name = "Usuario desconocido"
                
                if guild:
                    member = guild.get_member(bid['user_id'])
                    if member:
                        user_name = member.display_name
                    else:
                        try:
                            user = await self.bot.fetch_user(bid['user_id'])
                            user_name = user.display_name if user else f"Usuario {bid['user_id']}"
                        except:
                            user_name = f"Usuario {bid['user_id']}"
                
                # Obtener material de pago de la subasta
                auction = await self.bot.cache_manager.get_auction_cached(auction_id)
                material = auction['payment_material'] if auction else 'unidades'
                
                bid_text += f"**{user_name}**: {self.format_number(bid['amount'])} {material}\n"
            
            if bid_text:
                embed.add_field(
                    name="📋 Últimas Pujas",
                    value=bid_text.strip(),
                    inline=False
                )
                
        except Exception as e:
            logger.warning(f"Error agregando historial de pujas: {e}")
    
    async def _add_creator_footer(self, embed: discord.Embed, auction: Dict[str, Any]):
        """Agregar footer con información del creador"""
        try:
            guild = self.bot.get_guild(auction['guild_id'])
            if not guild:
                return
            
            creator = guild.get_member(auction['creator_id'])
            if creator:
                embed.set_footer(
                    text=f"Creado por {creator.display_name}",
                    icon_url=creator.display_avatar.url
                )
            else:
                # Intentar obtener información del usuario desde Discord API
                try:
                    user = await self.bot.fetch_user(auction['creator_id'])
                    embed.set_footer(
                        text=f"Creado por {user.display_name}",
                        icon_url=user.display_avatar.url if user.avatar else None
                    )
                except:
                    embed.set_footer(text=f"Creado por usuario ID: {auction['creator_id']}")
                
        except Exception as e:
            logger.warning(f"Error agregando footer: {e}")
            embed.set_footer(text=f"Creado por usuario ID: {auction['creator_id']}")
    
    def _create_error_embed(self, message: str) -> discord.Embed:
        """Crear embed de error estandarizado"""
        return discord.Embed(
            title="❌ Error",
            description=message,
            color=self.bot.config.COLOR_ERROR
        )
    
    async def update_auction_message(self, auction_id: int):
        """Actualizar mensaje de subasta con throttling"""
        try:
            current_time = datetime.now()
            last_update = self._update_throttle.get(auction_id)
            
            # Throttle: no actualizar más de una vez cada 1 segundo
            if last_update and (current_time - last_update).total_seconds() < 1:
                return
            
            self._update_throttle[auction_id] = current_time
            
            # Obtener datos de la subasta
            auction = await self.bot.cache_manager.get_auction_cached(auction_id)
            if not auction or not auction.get('message_id'):
                return
            
            guild = self.bot.get_guild(auction['guild_id'])
            if not guild:
                return
            
            channel = guild.get_channel(auction['channel_id'])
            if not channel:
                return
            
            try:
                message = await channel.fetch_message(auction['message_id'])
                embed = await self.create_auction_embed(auction_id)
                await message.edit(embed=embed)
                
                logger.debug(f"Mensaje de subasta {auction_id} actualizado")
                
            except discord.NotFound:
                logger.warning(f"Mensaje de subasta {auction_id} no encontrado")
            except discord.HTTPException as e:
                logger.warning(f"Error HTTP al actualizar mensaje: {e}")
            
        except Exception as e:
            logger.error(f"Error actualizando mensaje de subasta {auction_id}: {e}")
    
    async def notify_auction_end(self, auction_id: int):
        """Notificar finalización de subasta con manejo robusto de errores"""
        auction = None
        guild = None
        channel = None
        
        try:
            # Obtener datos de subasta con fallback a base de datos
            auction = await self.bot.cache_manager.get_auction_cached(auction_id)
            if not auction:
                # Fallback: obtener directamente de la base de datos
                auction = await self.bot.db.get_auction(auction_id)
                if not auction:
                    logger.warning(f"Subasta {auction_id} no encontrada para notificación")
                    return
            
            # Obtener guild con validación
            guild = self.bot.get_guild(auction['guild_id'])
            if not guild:
                logger.warning(f"Guild {auction['guild_id']} no encontrado para subasta {auction_id}")
                return
            
            # Obtener canal con validación
            channel = guild.get_channel(auction['channel_id'])
            if not channel:
                logger.warning(f"Canal {auction['channel_id']} no encontrado para subasta {auction_id}")
                return
            
            # Obtener ganador con fallback a base de datos
            bids = await self.bot.cache_manager.get_auction_bids_cached(auction_id, 1)
            if not bids:
                # Fallback: obtener directamente de la base de datos
                bids = await self.bot.db.get_auction_bids(auction_id, 1)
            
            # Crear embed de finalización robusto
            embed = discord.Embed(
                title=f"🔨 Subasta Finalizada",
                description=f"**{auction.get('title', 'Subasta')}** ha terminado.",
                color=0xff0000,  # Color rojo para finalizada
                timestamp=datetime.now()
            )
            
            if bids and len(bids) > 0:
                winner_id = bids[0]['user_id']
                winning_amount = bids[0]['amount']
                
                # Obtener nombre del ganador con múltiples fallbacks
                winner_name = f"Usuario {winner_id}"
                try:
                    winner = guild.get_member(winner_id)
                    if winner:
                        winner_name = winner.display_name
                    else:
                        # Intentar fetch si no está en cache
                        winner = await guild.fetch_member(winner_id)
                        winner_name = winner.display_name if winner else f"Usuario {winner_id}"
                except:
                    # Intentar obtener usuario global
                    try:
                        user = await self.bot.fetch_user(winner_id)
                        winner_name = user.display_name if user else f"Usuario {winner_id}"
                    except:
                        winner_name = f"Usuario {winner_id}"
                
                embed.add_field(
                    name="👑 Ganador",
                    value=f"**{winner_name}**",
                    inline=True
                )
                
                embed.add_field(
                    name="💰 Precio Final",
                    value=f"**{self.format_number(winning_amount)}** {auction.get('payment_material', 'unidades')}",
                    inline=True
                )
                
                # Notificar al ganador por DM de forma segura
                try:
                    winner = guild.get_member(winner_id)
                    if winner:
                        dm_embed = discord.Embed(
                            title="🎉 ¡Has ganado una subasta!",
                            description=f"Has ganado la subasta **{auction.get('title', 'Subasta')}**",
                            color=0x00ff00
                        )
                        dm_embed.add_field(
                            name="Precio Final",
                            value=f"{self.format_number(winning_amount)} {auction.get('payment_material', 'unidades')}",
                            inline=False
                        )
                        dm_embed.add_field(
                            name="Próximos pasos",
                            value="Contacta con el vendedor para coordinar la entrega.",
                            inline=False
                        )
                        
                        await winner.send(embed=dm_embed)
                        logger.info(f"DM enviado al ganador {winner_id} de la subasta {auction_id}")
                except Exception as dm_error:
                    logger.debug(f"No se pudo enviar DM al ganador {winner_id}: {dm_error}")
            else:
                embed.add_field(
                    name="📭 Resultado",
                    value="Sin pujas - subasta sin ganador",
                    inline=False
                )
            
            embed.add_field(
                name="🆔 ID de Subasta",
                value=f"`{auction_id}`",
                inline=True
            )
            
            # Agregar información del creador
            try:
                creator = guild.get_member(auction['creator_id'])
                if creator:
                    embed.set_footer(
                        text=f"Creado por {creator.display_name}",
                        icon_url=creator.display_avatar.url
                    )
            except:
                pass
            
            # Intentar actualizar mensaje original con múltiples intentos
            message_updated = False
            if auction.get('message_id'):
                for attempt in range(3):  # 3 intentos
                    try:
                        message = await channel.fetch_message(auction['message_id'])
                        await message.edit(embed=embed, view=None)  # Remover botones
                        message_updated = True
                        break
                    except discord.NotFound:
                        logger.warning(f"Mensaje {auction['message_id']} no encontrado (intento {attempt + 1})")
                        break
                    except discord.HTTPException as e:
                        logger.warning(f"Error HTTP actualizando mensaje (intento {attempt + 1}): {e}")
                        if attempt == 2:  # Último intento
                            break
                        await asyncio.sleep(1)  # Esperar 1 segundo antes del siguiente intento
                    except Exception as e:
                        logger.warning(f"Error general actualizando mensaje (intento {attempt + 1}): {e}")
                        if attempt == 2:
                            break
                        await asyncio.sleep(1)
            
            # Si no se pudo actualizar el mensaje original, enviar uno nuevo
            if not message_updated:
                try:
                    await channel.send(embed=embed)
                    logger.info(f"Nuevo mensaje de finalización enviado para subasta {auction_id}")
                except Exception as send_error:
                    logger.error(f"Error enviando nuevo mensaje de finalización: {send_error}")
                    raise send_error
            
            logger.info(f"Subasta {auction_id} finalizada y notificada exitosamente")
            
        except Exception as e:
            logger.error(f"Error crítico notificando fin de subasta {auction_id}: {e}")
            
            # Enviar mensaje de error simplificado como último recurso
            try:
                if channel:
                    error_embed = discord.Embed(
                        title="⚠️ Error de Finalización",
                        description=f"La subasta #{auction_id} ha terminado, pero ocurrió un error al mostrar los detalles.",
                        color=0xffaa00
                    )
                    error_embed.add_field(
                        name="¿Qué hacer?",
                        value=f"Usa `/subastas_activas` para verificar el estado o contacta a un administrador.",
                        inline=False
                    )
                    await channel.send(embed=error_embed)
                    logger.info(f"Mensaje de error de finalización enviado para subasta {auction_id}")
            except Exception as final_error:
                logger.error(f"Error final enviando mensaje de error: {final_error}")
                # Como último recurso, enviar mensaje de texto simple
                try:
                    if channel:
                        await channel.send(f"⚠️ La subasta #{auction_id} ha terminado. Contacta a un administrador para detalles.")
                except:
                    logger.error(f"No se pudo enviar ningún tipo de notificación para subasta {auction_id}")
