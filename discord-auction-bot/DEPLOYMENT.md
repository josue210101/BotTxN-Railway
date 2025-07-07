# Deployment Guide

## Railway Deployment

### Preparación

1. **Crear cuenta en Railway**
   - Visita [railway.app](https://railway.app)
   - Crea una cuenta gratuita

2. **Preparar repositorio**
   - Sube el código a GitHub
   - Asegúrate de que todos los archivos estén incluidos

### Configuración

1. **Conectar repositorio**
   - En Railway, crea un nuevo proyecto
   - Conecta tu repositorio de GitHub
   - Railway detectará automáticamente el `pyproject.toml`

2. **Variables de entorno**
   - En el panel de Railway, ve a "Variables"
   - Agrega: `DISCORD_TOKEN=tu_token_aqui`

3. **Configuración automática**
   - Railway ejecutará automáticamente `python main.py`
   - El bot se iniciará automáticamente

### Verificación

1. **Logs**
   - Revisa los logs en Railway
   - Deberías ver: "BotTxN está conectado y listo!"

2. **Comandos**
   - Prueba `/crear_subasta` en Discord
   - Verifica que los botones de puja funcionan

## Alternativas de Deploy

### Heroku

```bash
# Crear aplicación
heroku create tu-auction-bot

# Configurar variables
heroku config:set DISCORD_TOKEN=tu_token

# Deploy
git push heroku main
```

### VPS/Cloud

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/discord-auction-bot.git
cd discord-auction-bot

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables
export DISCORD_TOKEN=tu_token

# Ejecutar
python main.py
```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
```

## Monitoreo

### Logs importantes

```
INFO - BotTxN está conectado y listo!
INFO - Bot conectado a X servidores
INFO - Recuperación completada: X subastas reprogramadas
```

### Errores comunes

- **Token inválido**: Verifica la variable `DISCORD_TOKEN`
- **Permisos**: Asegúrate de que el bot tenga permisos adecuados
- **Base de datos**: SQLite se crea automáticamente

## Mantenimiento

### Actualizaciones

1. Actualiza el código en GitHub
2. Railway redesplegará automáticamente
3. El bot se reiniciará con los cambios

### Backup

- SQLite se guarda automáticamente
- Railway mantiene persistencia de archivos
- Considera backups periódicos para datos importantes