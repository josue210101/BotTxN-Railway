"""
Views optimizadas para interacciones del bot de subastas
"""
import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class OptimizedAuctionView(discord.ui.View):
    """Vista optimizada para subastas con manejo mejorado de botones"""
    
    def __init__(self, bot, auction_id: int):
        super().__init__(timeout=None)  # Vista persistente
        self.bot = bot
        self.auction_id = auction_id
        self.current_image_index = 0
        
        # Botones principales: Puja Rápida y Puja Personalizada (diseño original)
        self.add_item(QuickBidButton(bot, auction_id, "quick_bid"))
        self.add_item(CustomBidButton(bot, auction_id, "custom_bid"))
        
        # Navegación de imágenes
        self.add_item(ImageNavigationButton(bot, auction_id, "prev_image", "◀️", -1))
        self.add_item(ImageNavigationButton(bot, auction_id, "next_image", "▶️", 1))

class QuickBidButton(discord.ui.Button):
    """Botón de puja rápida (incremento mínimo)"""
    
    def __init__(self, bot, auction_id: int, custom_id: str):
        self.bot = bot
        self.auction_id = auction_id
        
        super().__init__(
            style=discord.ButtonStyle.green,
            label="⚡ Puja Rápida",
            custom_id=f"{custom_id}_{auction_id}",
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Callback optimizado para puja rápida"""
        user_id = interaction.user.id
        
        try:
            # Verificar cooldown inmediatamente (sin defer)
            if await self.bot.is_user_on_cooldown(user_id):
                await interaction.response.send_message(
                    "⏳ Debes esperar un momento antes de pujar nuevamente.", 
                    ephemeral=True
                )
                return
            
            # Verificar si ya está procesando
            if await self.bot.is_bid_processing(user_id):
                await interaction.response.send_message(
                    "⚡ Tu puja anterior aún se está procesando.", 
                    ephemeral=True
                )
                return
            
            # Respuesta inmediata sin defer para evitar "thinking"
            await interaction.response.send_message(
                f"⚡ Procesando puja rápida x{self.increment_multiplier}...", 
                ephemeral=True
            )
            
            # Marcar como procesando
            await self.bot.set_bid_processing(user_id, True)
            
            # Procesar puja en background
            asyncio.create_task(self._process_quick_bid(interaction, user_id))
            
        except Exception as e:
            logger.error(f"Error en callback de puja rápida: {e}")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "❌ Error al procesar la puja. Intenta de nuevo.", 
                        ephemeral=True
                    )
                await self.bot.set_bid_processing(user_id, False)
            except:
                pass
    
    async def _process_quick_bid(self, interaction: discord.Interaction, user_id: int):
        """Procesar puja rápida en background"""
        try:
            # Obtener datos de subasta desde cache
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if not auction:
                await interaction.edit_original_response(content="❌ Subasta no encontrada.")
                return
            
            if auction['status'] != 'active':
                await interaction.edit_original_response(content="❌ Esta subasta ya no está activa.")
                return
            
            # Verificar que no sea el creador
            if user_id == auction['creator_id']:
                await interaction.edit_original_response(content="❌ No puedes pujar en tu propia subasta.")
                return
            
            # Calcular cantidad de puja
            increment = auction['min_increment'] * self.increment_multiplier
            bid_amount = auction['current_price'] + increment
            
            # Verificar tiempo límite
            ends_at = datetime.fromisoformat(auction['ends_at'])
            if datetime.now() >= ends_at:
                await interaction.edit_original_response(content="❌ Esta subasta ya ha terminado.")
                return
            
            # Realizar puja optimizada
            success, result = await self.bot.db.place_bid_optimized(
                self.auction_id, user_id, bid_amount, is_quick_bid=True
            )
            
            if not success:
                error_msg = result.get('error', 'Error desconocido')
                await interaction.edit_original_response(content=f"❌ {error_msg}")
                return
            
            # Establecer cooldown específico para pujas rápidas
            await self.bot.set_user_cooldown(user_id, self.bot.config.get_bid_cooldown(is_quick_bid=True))
            
            # Invalidar cache para forzar actualización
            await self.bot.cache_manager.invalidate_auction_cache(self.auction_id)
            
            # Notificar éxito
            formatted_amount = self.bot.utils.format_number(bid_amount)
            await interaction.edit_original_response(
                content=f"✅ Puja realizada: **{formatted_amount}** {auction['payment_material']}"
            )
            
            # Actualizar mensaje de subasta en background
            asyncio.create_task(self._update_auction_message())
            
            # Enviar notificación al usuario anterior
            if result.get('previous_user_id') and result['previous_user_id'] != user_id:
                asyncio.create_task(self._notify_previous_bidder(result))
            
            logger.info(f"Puja rápida exitosa: Usuario={user_id}, Subasta={self.auction_id}, Cantidad={bid_amount}")
            
        except Exception as e:
            logger.error(f"Error procesando puja rápida: {e}")
            try:
                await interaction.edit_original_response(content="❌ Error interno. Intenta de nuevo.")
            except:
                pass
        finally:
            # Siempre liberar el estado de procesamiento
            await self.bot.set_bid_processing(user_id, False)
    
    async def _update_auction_message(self):
        """Actualizar mensaje de subasta de forma optimizada"""
        try:
            # Precargar datos en cache
            await self.bot.cache_manager.preload_auction_data(self.auction_id)
            
            # Obtener datos actualizados
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if not auction or not auction.get('message_id'):
                return
            
            # Obtener mensaje y actualizarlo
            guild = self.bot.get_guild(auction['guild_id'])
            if not guild:
                return
            
            channel = guild.get_channel(auction['channel_id'])
            if not channel:
                return
            
            try:
                message = await channel.fetch_message(auction['message_id'])
                embed = await self.bot.utils.create_auction_embed(self.auction_id)
                await message.edit(embed=embed)
            except discord.NotFound:
                logger.warning(f"Mensaje de subasta {self.auction_id} no encontrado")
            except discord.HTTPException as e:
                logger.warning(f"Error HTTP al actualizar mensaje: {e}")
            
        except Exception as e:
            logger.error(f"Error actualizando mensaje de subasta: {e}")
    
    async def _notify_previous_bidder(self, notification_info: dict):
        """Notificar al pujador anterior"""
        try:
            previous_user_id = notification_info['previous_user_id']
            user = await self.bot.fetch_user(previous_user_id)
            if not user:
                return
            
            embed = discord.Embed(
                title="🔔 Tu puja ha sido superada",
                description=f"Tu puja en **{notification_info['auction_title']}** ha sido superada.",
                color=0xff9900
            )
            
            embed.add_field(
                name="Detalles",
                value=f"Tu puja: {self.bot.utils.format_number(notification_info['previous_amount'])}\n"
                      f"Nueva puja: {self.bot.utils.format_number(notification_info['new_amount'])}\n"
                      f"ID Subasta: #{notification_info['auction_id']}",
                inline=False
            )
            
            embed.set_footer(text="¡Puedes pujar de nuevo!")
            await user.send(embed=embed)
            
        except discord.Forbidden:
            logger.debug(f"No se pudo enviar DM a usuario {previous_user_id}")
        except Exception as e:
            logger.warning(f"Error enviando notificación DM: {e}")

class ImageNavigationButton(discord.ui.Button):
    """Botón para navegación de imágenes"""
    
    def __init__(self, bot, auction_id: int, custom_id: str, emoji: str, direction: int):
        self.bot = bot
        self.auction_id = auction_id
        self.direction = direction
        
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            custom_id=f"{custom_id}_{auction_id}",
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Navegar entre imágenes"""
        try:
            # Obtener datos de subasta
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if not auction:
                await interaction.response.send_message("❌ Subasta no encontrada.", ephemeral=True)
                return
            
            # Verificar si hay imágenes
            import json
            if not auction.get('image_urls'):
                await interaction.response.send_message("❌ Esta subasta no tiene imágenes.", ephemeral=True)
                return
            
            try:
                image_urls = json.loads(auction['image_urls'])
                if not image_urls:
                    await interaction.response.send_message("❌ Esta subasta no tiene imágenes.", ephemeral=True)
                    return
            except (json.JSONDecodeError, TypeError):
                await interaction.response.send_message("❌ Error al cargar imágenes.", ephemeral=True)
                return
            
            # Obtener índice actual del mensaje
            current_embed = interaction.message.embeds[0] if interaction.message.embeds else None
            current_index = 0
            
            if current_embed and current_embed.image:
                current_url = current_embed.image.url
                try:
                    current_index = image_urls.index(current_url)
                except ValueError:
                    current_index = 0
            
            # Calcular nuevo índice
            new_index = (current_index + self.direction) % len(image_urls)
            
            # Crear nuevo embed con la imagen
            embed = await self.bot.utils.create_auction_embed_with_image(self.auction_id, new_index)
            
            await interaction.response.edit_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en navegación de imágenes: {e}")
            await interaction.response.send_message("❌ Error al cambiar imagen.", ephemeral=True)

# Alias para compatibilidad
AuctionView = OptimizedAuctionView
QuickBidView = OptimizedAuctionView
