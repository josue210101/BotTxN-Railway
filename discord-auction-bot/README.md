# Discord Auction Bot

Un bot de subastas para Discord optimizado con sistema de pujas rápidas y manejo automático de temporizadores.

## Características

- ⚡ **Pujas rápidas** con botones (+1x, +5x, +10x incrementos)
- 🔄 **Sistema de cache** inteligente para optimizar rendimiento
- ⏰ **Temporizadores automáticos** para finalización de subastas
- 📸 **Soporte multi-imagen** (hasta 10 imágenes por subasta)
- 💬 **Notificaciones DM** automáticas a ganadores
- 🛡️ **Sistema robusto** de manejo de errores
- 🚀 **Optimizado para Railway** hosting

## Instalación

### Requisitos

- Python 3.8+
- Token de bot de Discord

### Dependencias

```bash
pip install discord.py==2.3.2 aiosqlite==0.19.0 aiohttp==3.9.1
```

### Configuración

1. Crea un bot en el Discord Developer Portal
2. Obtén el token del bot
3. Configura las variables de entorno:
   - `DISCORD_TOKEN`: Token de tu bot de Discord

### Deployment en Railway

1. Conecta tu repositorio a Railway
2. Configura la variable `DISCORD_TOKEN` en Railway
3. Railway detectará automáticamente el `pyproject.toml` y desplegará el bot

## Comandos

### Comandos de Usuario

- `/crear_subasta` - Crear nueva subasta
- `/pujar` - Realizar puja manual
- `/subastas_activas` - Ver subastas activas

### Comandos de Administrador

- `/finalizar_admin` - Finalizar subasta manualmente
- `/cache_stats` - Ver estadísticas del cache

## Estructura del Proyecto

```
discord-auction-bot/
├── main.py                 # Punto de entrada principal
├── config.py              # Configuración del bot
├── database.py            # Gestión de base de datos
├── cache_manager.py       # Sistema de cache
├── commands.py            # Comandos del bot
├── views.py               # Interfaces de usuario
├── utils.py               # Utilidades
├── timer_manager.py       # Gestión de temporizadores
├── pyproject.toml         # Dependencias
├── Procfile               # Configuración Railway
└── README.md              # Este archivo
```

## Desarrollo

### Configuración Local

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/discord-auction-bot.git
cd discord-auction-bot

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
export DISCORD_TOKEN=tu_token_aqui

# Ejecutar
python main.py
```

### Características Técnicas

- **Base de datos**: SQLite con modo WAL para concurrencia
- **Cache**: Sistema TTL con limpieza automática
- **Latencia**: Optimizado para pujas rápidas (<1 segundo)
- **Escalabilidad**: Manejo eficiente de múltiples subastas simultáneas

## Configuración del Bot

### Permisos Requeridos

- Send Messages
- Use Slash Commands
- Embed Links
- Attach Files
- Read Message History
- Manage Messages (para admins)

### Roles

- **Administradores**: Pueden usar comandos admin
- **Auction Member**: Rol para participar en subastas (opcional)

## Contribución

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## Licencia

MIT License - ver archivo LICENSE para detalles

## Soporte

Para reportar bugs o solicitar features, abre un issue en GitHub.