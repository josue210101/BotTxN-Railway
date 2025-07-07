"""
Comandos optimizados del bot de subastas
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
from datetime import datetime, timedelta
from typing import Optional
from utils import AuctionUtils
from views import AuctionView

logger = logging.getLogger(__name__)

class AuctionCommands(commands.Cog):
    """Comandos optimizados para el sistema de subastas"""
    
    def __init__(self, bot):
        self.bot = bot
        self.utils = AuctionUtils(bot)
    
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
    
    @app_commands.command(name="subasta", description="Iniciar una nueva subasta")
    @app_commands.describe(
        titulo="Título de la subasta",
        precio_inicial="Precio inicial de la subasta",
        incremento_minimo="Incremento mínimo para las pujas",
        material_pago="Material de pago (ej: diamantes, oro, etc.)",
        duracion="Duración de la subasta (12h o 24h)",
        descripcion="Descripción opcional de la subasta",
        imagen1="Primera imagen (opcional)",
        imagen2="Segunda imagen (opcional)",
        imagen3="Tercera imagen (opcional)",
        imagen4="Cuarta imagen (opcional)",
        imagen5="Quinta imagen (opcional)",
        imagen6="Sexta imagen (opcional)",
        imagen7="Séptima imagen (opcional)",
        imagen8="Octava imagen (opcional)",
        imagen9="Novena imagen (opcional)",
        imagen10="Décima imagen (opcional)"
    )
    @app_commands.choices(duracion=[
        app_commands.Choice(name="12 horas", value=12),
        app_commands.Choice(name="24 horas", value=24)
    ])
    async def create_auction(
        self,
        interaction: discord.Interaction,
        titulo: str,
        precio_inicial: float,
        incremento_minimo: float,
        material_pago: str,
        duracion: int,
        descripcion: Optional[str] = None,
        imagen1: Optional[discord.Attachment] = None,
        imagen2: Optional[discord.Attachment] = None,
        imagen3: Optional[discord.Attachment] = None,
        imagen4: Optional[discord.Attachment] = None,
        imagen5: Optional[discord.Attachment] = None,
        imagen6: Optional[discord.Attachment] = None,
        imagen7: Optional[discord.Attachment] = None,
        imagen8: Optional[discord.Attachment] = None,
        imagen9: Optional[discord.Attachment] = None,
        imagen10: Optional[discord.Attachment] = None
    ):
        """Crear una nueva subasta con validaciones optimizadas"""
        # Defer para operaciones largas
        await interaction.response.defer()
        
        try:
            # Validaciones básicas
            if precio_inicial <= 0:
                await interaction.followup.send("❌ El precio inicial debe ser mayor a 0.")
                return
            
            if incremento_minimo <= 0:
                await interaction.followup.send("❌ El incremento mínimo debe ser mayor a 0.")
                return
            
            if len(titulo) > 100:
                await interaction.followup.send("❌ El título no puede exceder 100 caracteres.")
                return
            
            # Validar imágenes de forma optimizada
            image_urls = []
            images = [imagen1, imagen2, imagen3, imagen4, imagen5, 
                     imagen6, imagen7, imagen8, imagen9, imagen10]
            
            for imagen in images:
                if imagen is not None:
                    # Solo validación básica de tamaño para velocidad
                    if imagen.size > 10 * 1024 * 1024:  # 10MB límite rápido
                        await interaction.followup.send(f"❌ Imagen muy grande (máx 10MB)")
                        return
                    
                    image_urls.append(imagen.url)
            
            # Convertir a JSON para almacenar
            import json
            image_urls_json = json.dumps(image_urls) if image_urls else "[]"
            
            # Calcular tiempo de finalización
            created_at = datetime.now()
            ends_at = created_at + timedelta(hours=duracion)
            
            # Crear datos de la subasta
            auction_data = {
                'guild_id': interaction.guild.id,
                'channel_id': interaction.channel.id,
                'creator_id': interaction.user.id,
                'title': titulo,
                'description': descripcion or "Sin descripción",
                'starting_price': precio_inicial,
                'min_increment': incremento_minimo,
                'payment_material': material_pago,
                'image_urls': image_urls_json,
                'duration_hours': duracion,
                'created_at': created_at.isoformat(),
                'ends_at': ends_at.isoformat()
            }
            
            # Crear subasta en la base de datos
            auction_id = await self.bot.db.create_auction(auction_data)
            
            # Precargar datos en cache para optimización
            await self.bot.cache_manager.preload_auction_data(auction_id)
            
            # Crear embed de la subasta
            embed = await self.utils.create_auction_embed(auction_id)
            
            # Obtener rol de miembros de subasta y crear menciones
            auction_role = self.bot.get_auction_member_role(interaction.guild)
            mention_text = ""
            
            if auction_role:
                mention_text = f"{auction_role.mention} ¡Nueva subasta disponible!"
            else:
                mention_text = "¡Nueva subasta disponible!"
            
            # Enviar mensaje de subasta con vista optimizada
            message = await interaction.followup.send(
                content=mention_text,
                embed=embed,
                view=AuctionView(self.bot, auction_id)
            )
            
            # Actualizar ID del mensaje en la base de datos
            await self.bot.db.update_auction_message_id(auction_id, message.id)
            
            # Invalidar cache para incluir message_id
            await self.bot.cache_manager.invalidate_auction_cache(auction_id)
            
            # Programar finalización automática
            await self.bot.timer_manager.schedule_auction_end(auction_id, ends_at)
            
            logger.info(f"Subasta creada: ID={auction_id}, Creador={interaction.user.id}")
            
        except Exception as e:
            logger.error(f"Error al crear subasta: {e}")
            await interaction.followup.send("❌ Error al crear la subasta. Intenta de nuevo.")
    
    @app_commands.command(name="pujar", description="Realizar una puja en una subasta")
    @app_commands.describe(
        auction_id="ID de la subasta",
        cantidad="Cantidad a pujar"
    )
    async def bid(self, interaction: discord.Interaction, auction_id: int, cantidad: float):
        """Realizar una puja optimizada"""
        user_id = interaction.user.id
        
        try:
            # Verificar cooldown antes de defer
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
            
            await interaction.response.defer(ephemeral=True)
            
            # Marcar como procesando
            await self.bot.set_bid_processing(user_id, True)
            
            try:
                # Obtener subasta desde cache
                auction = await self.bot.cache_manager.get_auction_cached(auction_id)
                if not auction:
                    await interaction.followup.send("❌ Subasta no encontrada.")
                    return
                
                if auction['status'] != 'active':
                    await interaction.followup.send("❌ Esta subasta ya no está activa.")
                    return
                
                # Verificar que no sea el creador
                if user_id == auction['creator_id']:
                    await interaction.followup.send("❌ No puedes pujar en tu propia subasta.")
                    return
                
                # Verificar tiempo límite
                ends_at = datetime.fromisoformat(auction['ends_at'])
                if datetime.now() >= ends_at:
                    await interaction.followup.send("❌ Esta subasta ya ha terminado.")
                    return
                
                # Verificar cantidad mínima
                min_bid = auction['current_price'] + auction['min_increment']
                if cantidad < min_bid:
                    await interaction.followup.send(f"❌ La puja mínima es {self.format_number(min_bid)} {auction['payment_material']}.")
                    return
                
                # Realizar puja optimizada
                success, result = await self.bot.db.place_bid_optimized(auction_id, user_id, cantidad)
                if not success:
                    error_msg = result.get('error', 'No se pudo realizar la puja')
                    await interaction.followup.send(f"❌ {error_msg}")
                    return
                
                # Establecer cooldown
                await self.bot.set_user_cooldown(user_id, self.bot.config.get_bid_cooldown())
                
                # Invalidar cache
                await self.bot.cache_manager.invalidate_auction_cache(auction_id)
                
                # Notificar al usuario anterior en background
                if result.get('previous_user_id') and result['previous_user_id'] != user_id:
                    import asyncio
                    asyncio.create_task(self._notify_previous_bidder(result))
                
                # Actualizar mensaje de subasta en background
                asyncio.create_task(self._update_auction_message(auction_id))
                
                # Confirmar puja
                await interaction.followup.send(f"✅ Puja realizada: {self.format_number(cantidad)} {auction['payment_material']}")
                
                logger.info(f"Puja realizada: Subasta={auction_id}, Usuario={user_id}, Cantidad={cantidad}")
                
            finally:
                # Siempre liberar el estado de procesamiento
                await self.bot.set_bid_processing(user_id, False)
            
        except Exception as e:
            logger.error(f"Error al realizar puja: {e}")
            await self.bot.set_bid_processing(user_id, False)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error al realizar la puja. Intenta de nuevo.", ephemeral=True)
                else:
                    await interaction.followup.send("❌ Error al realizar la puja. Intenta de nuevo.")
            except:
                pass
    
    async def _notify_previous_bidder(self, notification_info: dict):
        """Notificar al pujador anterior"""
        try:
            previous_user_id = notification_info['previous_user_id']
            user = await self.bot.fetch_user(previous_user_id)
            if not user:
                return
            
            # Obtener información del canal
            guild_id = notification_info.get('guild_id')
            channel_id = notification_info.get('channel_id')
            channel_mention = f"<#{channel_id}>" if channel_id else "Canal desconocido"
            
            embed = discord.Embed(
                title="🔔 Tu puja ha sido superada",
                description=f"Tu puja en **{notification_info['auction_title']}** ha sido superada.",
                color=0xff9900
            )
            
            embed.add_field(
                name="📍 Ubicación",
                value=f"Canal: {channel_mention}\nID Subasta: #{notification_info['auction_id']}",
                inline=False
            )
            
            embed.add_field(
                name="💰 Detalles de Puja",
                value=f"Tu puja: {self.format_number(notification_info['previous_amount'])} {notification_info.get('payment_material', '')}\n"
                      f"Nueva puja: {self.format_number(notification_info['new_amount'])} {notification_info.get('payment_material', '')}",
                inline=False
            )
            
            embed.set_footer(text="¡Puedes pujar de nuevo directamente en el canal!")
            await user.send(embed=embed)
            
        except Exception as e:
            logger.warning(f"Error enviando notificación DM: {e}")
    
    async def _update_auction_message(self, auction_id: int):
        """Actualizar mensaje de subasta"""
        try:
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
                embed = await self.utils.create_auction_embed(auction_id)
                await message.edit(embed=embed)
            except discord.NotFound:
                logger.warning(f"Mensaje de subasta {auction_id} no encontrado")
            
        except Exception as e:
            logger.error(f"Error actualizando mensaje: {e}")
    
    @app_commands.command(name="subastas_activas", description="Ver todas las subastas activas (solo admins)")
    async def list_active_auctions(self, interaction: discord.Interaction):
        """Listar subastas activas con paginación optimizada"""
        if not self.bot.is_admin(interaction.user):
            await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            auctions = await self.bot.db.get_active_auctions(interaction.guild.id)
            
            if not auctions:
                await interaction.followup.send("📭 No hay subastas activas en este momento.")
                return
            
            # Crear embed con lista de subastas
            embed = discord.Embed(
                title="📋 Subastas Activas",
                color=self.bot.config.COLOR_ACTIVE,
                timestamp=datetime.now()
            )
            
            for auction in auctions[:10]:  # Limitar a 10 subastas
                creator = interaction.guild.get_member(auction['creator_id'])
                creator_name = creator.display_name if creator else "Usuario desconocido"
                
                ends_at = datetime.fromisoformat(auction['ends_at'])
                time_left = ends_at - datetime.now()
                
                if time_left.total_seconds() > 0:
                    hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                    minutes, _ = divmod(remainder, 60)
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = "Expirada"
                
                embed.add_field(
                    name=f"#{auction['id']} - {auction['title'][:30]}...",
                    value=f"💰 {self.format_number(auction['current_price'])} {auction['payment_material']}\n"
                          f"👤 {creator_name}\n"
                          f"⏰ {time_str}",
                    inline=True
                )
            
            if len(auctions) > 10:
                embed.set_footer(text=f"Mostrando 10 de {len(auctions)} subastas activas")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error al listar subastas activas: {e}")
            await interaction.followup.send("❌ Error al obtener las subastas activas.")
    
    @app_commands.command(name="cache_stats", description="Ver estadísticas del cache (solo admins)")
    async def cache_stats(self, interaction: discord.Interaction):
        """Mostrar estadísticas del cache"""
        if not self.bot.is_admin(interaction.user):
            await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)
            return
        
        try:
            stats = await self.bot.cache_manager.get_cache_stats()
            timer_count = await self.bot.timer_manager.get_active_timer_count()
            
            embed = discord.Embed(
                title="📊 Estadísticas del Sistema",
                color=self.bot.config.COLOR_SUCCESS,
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="💾 Cache",
                value=f"Subastas: {stats['auctions_cached']}\n"
                      f"Pujas: {stats['bids_cached']}\n"
                      f"Usuarios: {stats['users_cached']}\n"
                      f"Contadores: {stats['bid_counts_cached']}",
                inline=True
            )
            
            embed.add_field(
                name="⏱️ Timers Activos",
                value=f"{timer_count}",
                inline=True
            )
            
            embed.add_field(
                name="🔄 Estados",
                value=f"Procesando pujas: {len(self.bot.bid_processing)}\n"
                      f"Cooldowns activos: {len(self.bot.user_cooldowns)}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {e}")
            await interaction.response.send_message("❌ Error al obtener estadísticas.", ephemeral=True)

    @app_commands.command(name="finalizar", description="Finalizar una subasta (solo Admin/Moderador)")
    @app_commands.describe(auction_id="ID de la subasta a finalizar")
    async def finalize_auction(self, interaction: discord.Interaction, auction_id: int):
        """Finalizar una subasta manualmente (solo Admin/Moderador)"""
        # Verificar permisos
        user_roles = [role.name.lower() for role in interaction.user.roles]
        if not any(role in ['admin', 'moderador', 'administrator'] for role in user_roles):
            await interaction.response.send_message(
                "❌ Solo usuarios con rol Admin o Moderador pueden finalizar subastas.",
                ephemeral=True
            )
            return
        
        try:
            await interaction.response.defer()
            
            # Verificar que la subasta existe y está activa
            auction = await self.bot.db.get_auction(auction_id)
            if not auction:
                await interaction.followup.send(
                    f"❌ No se encontró la subasta con ID {auction_id}.",
                    ephemeral=True
                )
                return
            
            if auction['status'] != 'active':
                await interaction.followup.send(
                    f"❌ La subasta {auction_id} ya está finalizada.",
                    ephemeral=True
                )
                return
            
            # Finalizar la subasta
            success = await self.bot.timer_manager.end_auction(auction_id)
            
            if success:
                await interaction.followup.send(
                    f"✅ Subasta {auction_id} finalizada exitosamente por {interaction.user.mention}.",
                    ephemeral=True
                )
                logger.info(f"Subasta {auction_id} finalizada manualmente por {interaction.user} ({interaction.user.id})")
            else:
                await interaction.followup.send(
                    f"❌ Error al finalizar la subasta {auction_id}.",
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error finalizando subasta {auction_id}: {e}")
            await interaction.followup.send(
                "❌ Error procesando la finalización de la subasta.",
                ephemeral=True
            )
