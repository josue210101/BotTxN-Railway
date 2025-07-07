"""
Views para interacciones del bot de subastas - Diseño Original
"""
import discord
from discord.ext import commands
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class AuctionView(discord.ui.View):
    """Vista para subastas con carrusel de fotos optimizado"""
    
    def __init__(self, bot, auction_id: int):
        super().__init__(timeout=None)  # Vista persistente
        self.bot = bot
        self.auction_id = auction_id
        self.current_image_index = 0
        self.image_cache = None  # Cache local de URLs de imágenes
        self.total_images = 0
        
        # Inicializar cache de imágenes
        asyncio.create_task(self._preload_images())
        
        # Botones principales: Puja Rápida y Puja Personalizada (diseño original)
        self.add_item(QuickBidButton(bot, auction_id))
        self.add_item(CustomBidButton(bot, auction_id))
        
        # Botón para abrir carrusel personal (solo si hay imágenes)
        self.add_item(ViewImagesButton(bot, auction_id))
    
    async def _preload_images(self):
        """Precargar información de imágenes para optimizar navegación"""
        try:
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if auction and auction.get('image_urls'):
                import json
                try:
                    self.image_cache = json.loads(auction['image_urls'])
                    self.total_images = len(self.image_cache)
                except (json.JSONDecodeError, TypeError):
                    self.image_cache = []
                    self.total_images = 0
            else:
                self.image_cache = []
                self.total_images = 0
        except Exception as e:
            logger.debug(f"Error precargando imágenes: {e}")
            self.image_cache = []
            self.total_images = 0

class ViewImagesButton(discord.ui.Button):
    """Botón para abrir carrusel personal de imágenes"""
    
    def __init__(self, bot, auction_id: int):
        self.bot = bot
        self.auction_id = auction_id
        
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="📷 Ver Imágenes",
            custom_id=f"view_images_{auction_id}",
            row=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Abrir carrusel personal para el usuario"""
        try:
            # Obtener información de la subasta
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if not auction or not auction.get('image_urls'):
                await interaction.response.send_message(
                    "📷 Esta subasta no tiene imágenes para mostrar.", 
                    ephemeral=True
                )
                return
            
            import json
            try:
                image_urls = json.loads(auction['image_urls'])
                total_images = len(image_urls)
            except (json.JSONDecodeError, TypeError):
                await interaction.response.send_message(
                    "❌ Error cargando imágenes.", 
                    ephemeral=True
                )
                return
            
            if total_images == 0:
                await interaction.response.send_message(
                    "📷 Esta subasta no tiene imágenes para mostrar.", 
                    ephemeral=True
                )
                return
            
            # Crear embed con primera imagen
            embed = await self.bot.utils.create_auction_embed_with_image(self.auction_id, 0)
            
            # Crear vista personal con navegación
            personal_view = discord.ui.View(timeout=300)  # 5 minutos timeout
            if total_images > 1:
                personal_view.add_item(PersonalImageNavigationButton(self.bot, self.auction_id, "◀️", -1))
                personal_view.add_item(PersonalImageNavigationButton(self.bot, self.auction_id, "▶️", 1))
                
                # Botón indicador
                indicator = PersonalImageIndicatorButton(self.bot, self.auction_id)
                indicator.label = f"📷 1/{total_images}"
                personal_view.add_item(indicator)
            
            # Enviar mensaje personal con carrusel
            await interaction.response.send_message(
                embed=embed,
                view=personal_view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.error(f"Error abriendo carrusel personal: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error abriendo el carrusel de imágenes.", 
                    ephemeral=True
                )

class PersonalImageNavigationButton(discord.ui.Button):
    """Botón de navegación para carrusel personal"""
    
    def __init__(self, bot, auction_id: int, emoji: str, direction: int):
        self.bot = bot
        self.auction_id = auction_id
        self.direction = direction
        self.current_index = 0  # Índice local de este botón
        
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            custom_id=f"personal_nav_{auction_id}_{direction}",
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Navegar entre imágenes en vista personal"""
        try:
            # Obtener información de imágenes
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if not auction or not auction.get('image_urls'):
                await interaction.response.send_message(
                    "❌ Error: No se encontraron imágenes.", 
                    ephemeral=True
                )
                return
            
            import json
            try:
                image_urls = json.loads(auction['image_urls'])
                total_images = len(image_urls)
            except (json.JSONDecodeError, TypeError):
                await interaction.response.send_message(
                    "❌ Error procesando imágenes.", 
                    ephemeral=True
                )
                return
            
            # Calcular nuevo índice
            self.current_index = (self.current_index + self.direction) % total_images
            
            # Crear embed con nueva imagen
            embed = await self.bot.utils.create_auction_embed_with_image(
                self.auction_id, 
                self.current_index
            )
            
            # Actualizar indicador en la vista
            view = self.view
            for item in view.children:
                if isinstance(item, PersonalImageIndicatorButton):
                    item.label = f"📷 {self.current_index + 1}/{total_images}"
                elif isinstance(item, PersonalImageNavigationButton):
                    item.current_index = self.current_index
            
            # Editar mensaje con nueva imagen
            await interaction.response.edit_message(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error en navegación personal: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error navegando imágenes.", 
                    ephemeral=True
                )

class PersonalImageIndicatorButton(discord.ui.Button):
    """Botón indicador para carrusel personal"""
    
    def __init__(self, bot, auction_id: int):
        self.bot = bot
        self.auction_id = auction_id
        
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="📷 1/1",
            custom_id=f"personal_indicator_{auction_id}",
            row=0,
            disabled=True
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Callback informativo"""
        await interaction.response.send_message(
            "📷 Este indicador muestra tu posición actual en el carrusel personal.",
            ephemeral=True
        )

class QuickBidButton(discord.ui.Button):
    """Botón de puja rápida (incremento mínimo) - Diseño Original"""
    
    def __init__(self, bot, auction_id: int):
        self.bot = bot
        self.auction_id = auction_id
        
        super().__init__(
            style=discord.ButtonStyle.green,
            label="⚡ Puja Rápida",
            custom_id=f"quick_bid_{auction_id}",
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Callback para puja rápida (incremento mínimo)"""
        user_id = interaction.user.id
        
        try:
            # Defer inmediatamente para evitar timeouts
            await interaction.response.defer()
            
            # Verificar cooldown
            if await self.bot.is_user_on_cooldown(user_id):
                await interaction.followup.send(
                    "⏳ Debes esperar un momento antes de pujar nuevamente.", 
                    ephemeral=True
                )
                return
            
            # Verificar si ya está procesando
            if await self.bot.is_bid_processing(user_id):
                await interaction.followup.send(
                    "⚠️ Ya estás procesando una puja.",
                    ephemeral=True
                )
                return
            
            # Obtener datos de la subasta
            auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
            if not auction:
                await interaction.followup.send(
                    "❌ Subasta no encontrada.",
                    ephemeral=True
                )
                return
            
            # Calcular puja automática (precio actual + incremento mínimo)
            quick_bid_amount = auction['current_price'] + auction['min_increment']
            
            # Procesar puja directamente sin llamar al comando (evitar doble defer)
            commands_cog = self.bot.get_cog('AuctionCommands')
            if commands_cog:
                # Marcar como procesando
                await self.bot.set_bid_processing(user_id, True)
                
                try:
                    # Realizar puja usando la base de datos directamente
                    success, result = await self.bot.db.place_bid_optimized(
                        self.auction_id, user_id, quick_bid_amount, is_quick_bid=True
                    )
                    
                    if not success:
                        error_msg = result.get('error', 'No se pudo realizar la puja')
                        await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
                        return
                    
                    # Invalidar cache
                    await self.bot.cache_manager.invalidate_auction_cache(self.auction_id)
                    
                    # Establecer cooldown
                    await self.bot.set_user_cooldown(user_id, 1.0)
                    
                    # Obtener datos de la subasta para confirmación
                    auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
                    material = auction['payment_material'] if auction else ''
                    
                    # Confirmar puja (público y auto-eliminar)
                    confirmation_msg = await interaction.followup.send(
                        f"✅ **{interaction.user.display_name}** realizó puja rápida: {commands_cog.format_number(quick_bid_amount)} {material}"
                    )
                    
                    # Auto-eliminar mensaje después de 0.5 segundos
                    asyncio.create_task(self._auto_delete_message(confirmation_msg, 0.5))
                    
                    # Notificar al usuario anterior en background
                    if result.get('previous_user_id') and result['previous_user_id'] != user_id:
                        asyncio.create_task(commands_cog._notify_previous_bidder(result))
                    
                    # Actualizar mensaje de subasta
                    asyncio.create_task(commands_cog._update_auction_message(self.auction_id))
                    
                finally:
                    await self.bot.set_bid_processing(user_id, False)
            else:
                await interaction.followup.send(
                    "❌ Error del sistema. Intenta más tarde.",
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error en puja rápida: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error procesando la puja. Intenta de nuevo.",
                    ephemeral=True
                )
    
    async def _auto_delete_message(self, message, delay: int):
        """Eliminar mensaje después de un delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception as e:
            logger.debug(f"No se pudo eliminar mensaje: {e}")

class CustomBidButton(discord.ui.Button):
    """Botón de puja personalizada - Diseño Original"""
    
    def __init__(self, bot, auction_id: int):
        self.bot = bot
        self.auction_id = auction_id
        
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="💬 Puja Personalizada",
            custom_id=f"custom_bid_{auction_id}",
            row=0
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Mostrar modal para puja personalizada"""
        modal = CustomBidModal(self.bot, self.auction_id)
        await interaction.response.send_modal(modal)

class CustomBidModal(discord.ui.Modal, title="Realizar Puja Personalizada"):
    """Modal para puja personalizada"""
    
    def __init__(self, bot, auction_id: int):
        super().__init__()
        self.bot = bot
        self.auction_id = auction_id
    
    amount = discord.ui.TextInput(
        label="Cantidad a pujar",
        placeholder="Ej: 1000, 2500, 5K...",
        required=True,
        max_length=20
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Procesar puja personalizada"""
        try:
            # Limpiar y convertir cantidad
            amount_str = self.amount.value.strip().upper().replace(',', '')
            
            # Manejar formato con K
            if 'K' in amount_str:
                amount_str = amount_str.replace('K', '')
                amount = float(amount_str) * 1000
            else:
                amount = float(amount_str)
            
            if amount <= 0:
                await interaction.response.send_message(
                    "❌ La cantidad debe ser mayor a 0.",
                    ephemeral=True
                )
                return
            
            # Defer inmediatamente para evitar timeouts
            await interaction.response.defer()
            
            # Procesar puja personalizada directamente sin llamar al comando
            commands_cog = self.bot.get_cog('AuctionCommands')
            if commands_cog:
                user_id = interaction.user.id
                
                # Marcar como procesando
                await self.bot.set_bid_processing(user_id, True)
                
                try:
                    # Realizar puja usando la base de datos directamente
                    success, result = await self.bot.db.place_bid_optimized(
                        self.auction_id, user_id, amount, is_quick_bid=False
                    )
                    
                    if not success:
                        error_msg = result.get('error', 'No se pudo realizar la puja')
                        await interaction.followup.send(f"❌ {error_msg}", ephemeral=True)
                        return
                    
                    # Invalidar cache
                    await self.bot.cache_manager.invalidate_auction_cache(self.auction_id)
                    
                    # Establecer cooldown
                    await self.bot.set_user_cooldown(user_id, 1.0)
                    
                    # Obtener datos de la subasta para confirmación
                    auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
                    material = auction['payment_material'] if auction else ''
                    
                    # Confirmar puja (público y auto-eliminar)
                    confirmation_msg = await interaction.followup.send(
                        f"✅ **{interaction.user.display_name}** realizó puja personalizada: {commands_cog.format_number(amount)} {material}"
                    )
                    
                    # Auto-eliminar mensaje después de 0.5 segundos
                    asyncio.create_task(self._auto_delete_message(confirmation_msg, 0.5))
                    
                    # Notificar al usuario anterior en background
                    if result.get('previous_user_id') and result['previous_user_id'] != user_id:
                        asyncio.create_task(commands_cog._notify_previous_bidder(result))
                    
                    # Actualizar mensaje de subasta
                    asyncio.create_task(commands_cog._update_auction_message(self.auction_id))
                    
                finally:
                    await self.bot.set_bid_processing(user_id, False)
            else:
                await interaction.followup.send(
                    "❌ Error del sistema. Intenta más tarde.",
                    ephemeral=True
                )
                
        except ValueError:
            await interaction.response.send_message(
                "❌ Formato inválido. Usa números como: 1000, 2.5K, etc.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error en puja personalizada: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error procesando la puja. Intenta de nuevo.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Error procesando la puja. Intenta de nuevo.",
                    ephemeral=True
                )
    
    async def _auto_delete_message(self, message, delay: int):
        """Eliminar mensaje después de un delay"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception as e:
            logger.debug(f"No se pudo eliminar mensaje: {e}")

class ImageNavigationButton(discord.ui.Button):
    """Botón optimizado para navegación de imágenes"""
    
    def __init__(self, bot, auction_id: int, custom_id: str, emoji: str, direction: int):
        self.bot = bot
        self.auction_id = auction_id
        self.direction = direction
        
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            custom_id=f"{custom_id}_{auction_id}",
            row=1,
            disabled=False  # Se actualizará dinámicamente
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Navegación optimizada entre imágenes"""
        try:
            # Usar cache de la vista si está disponible
            if hasattr(self.view, 'image_cache') and self.view.image_cache:
                image_urls = self.view.image_cache
                total_images = self.view.total_images
            else:
                # Fallback: obtener de la base de datos
                auction = await self.bot.cache_manager.get_auction_cached(self.auction_id)
                if not auction or not auction.get('image_urls'):
                    await interaction.response.send_message(
                        "📷 Esta subasta no tiene imágenes.", 
                        ephemeral=True
                    )
                    return
                
                import json
                try:
                    image_urls = json.loads(auction['image_urls'])
                    total_images = len(image_urls)
                except (json.JSONDecodeError, TypeError):
                    await interaction.response.send_message(
                        "❌ Error cargando imágenes.", 
                        ephemeral=True
                    )
                    return
            
            # Verificar que hay múltiples imágenes
            if total_images <= 1:
                await interaction.response.send_message(
                    "📷 Esta subasta solo tiene una imagen.", 
                    ephemeral=True
                )
                return
            
            # Obtener índice específico del usuario o inicializar
            user_id = str(interaction.user.id)
            if not hasattr(self.view, 'user_image_indices'):
                self.view.user_image_indices = {}
            
            current_index = self.view.user_image_indices.get(user_id, 0)
            
            # Calcular nuevo índice
            new_index = (current_index + self.direction) % total_images
            
            # Actualizar índice específico del usuario
            self.view.user_image_indices[user_id] = new_index
            
            # Crear embed personalizado con la imagen para este usuario
            embed = await self.bot.utils.create_auction_embed_with_image(
                self.auction_id, 
                new_index
            )
            
            # Responder editando la interacción actual (no crear nuevo mensaje)
            await interaction.response.edit_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error en navegación optimizada: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Error navegando imágenes.", 
                    ephemeral=True
                )
    
    def _update_image_indicator(self):
        """Actualizar el botón indicador de imagen"""
        if hasattr(self.view, 'total_images') and self.view.total_images > 1:
            for item in self.view.children:
                if isinstance(item, ImageIndicatorButton):
                    current = self.view.current_image_index + 1
                    total = self.view.total_images
                    item.label = f"📷 {current}/{total}"
                    break

class ImageIndicatorButton(discord.ui.Button):
    """Botón indicador de posición en el carrusel"""
    
    def __init__(self, bot, auction_id: int):
        self.bot = bot
        self.auction_id = auction_id
        
        super().__init__(
            style=discord.ButtonStyle.gray,
            label="📷 1/1",
            custom_id=f"image_indicator_{auction_id}",
            row=1,
            disabled=True  # Solo informativo
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Callback para indicador (no hace nada, solo es informativo)"""
        await interaction.response.send_message(
            "📷 Este botón muestra la posición actual en el carrusel de imágenes.",
            ephemeral=True
        )