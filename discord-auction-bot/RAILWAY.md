# Railway Deployment Guide

Este bot está específicamente optimizado para Railway hosting platform.

## Configuración en Railway

### 1. Variables de Entorno
Configura estas variables en Railway:
```
DISCORD_TOKEN=tu_token_de_discord_aqui
```

### 2. Configuración Automática
Railway detectará automáticamente:
- `Procfile` para el comando `worker: python main.py`
- `pyproject.toml` para las dependencias de Python
- Base de datos SQLite se crea automáticamente en el filesystem persistente

### 3. Características Optimizadas para Railway

#### Base de Datos
- **SQLite con WAL mode** para concurrencia optimizada
- **Persistent filesystem** - Los datos se mantienen entre reinicios
- **Backup automático** con archivos .db-wal y .db-shm

#### Logging
- **Structured logging** hacia stdout para agregación de Railway
- **Niveles apropiados** INFO para operaciones, ERROR para fallos
- **Sin archivos de log locales** - todo va a Railway logs

#### Performance
- **Cache inteligente** con TTL optimizado para Railway
- **Cooldowns ajustados** para balance entre performance y rate limits
- **Conexiones optimizadas** para el entorno de Railway

#### Proceso
- **Worker process** - No usa puerto web, es un background service
- **Auto-restart** - Railway reinicia automáticamente si hay fallos
- **Health monitoring** - Bot status como indicador de salud

### 4. Deployment Steps

1. **Conectar Repositorio**
   - Conecta tu repo de GitHub a Railway
   - Railway detecta automáticamente que es un proyecto Python

2. **Configurar Variables**
   - En Railway dashboard → Variables
   - Agrega `DISCORD_TOKEN` con tu token

3. **Deploy Automático**
   - Railway construye y despliega automáticamente
   - Logs disponibles en tiempo real en Railway dashboard

### 5. Monitoring

#### Logs para Verificar
```
INFO - BotTxN está conectado y listo!
INFO - Bot conectado a X servidores
INFO - Base de datos inicializada correctamente
INFO - Comandos sincronizados exitosamente
```

#### Señales de Problemas
```
ERROR - No se pudo conectar a Discord
ERROR - Token inválido
WARNING - Rate limited
```

### 6. Mantenimiento

#### Updates
- Push a GitHub → Railway redespliega automáticamente
- Zero downtime deployment
- Rollback disponible en Railway dashboard

#### Database
- SQLite persiste automáticamente
- Backups manuales disponibles descargando archivos
- WAL mode permite lecturas concurrentes sin bloqueos

#### Performance Monitoring
- CPU y memoria visible en Railway dashboard
- Bot response time optimizado para Railway infrastructure
- Cache hit rates logged para monitoreo

### 7. Troubleshooting

#### Bot No Conecta
- Verificar `DISCORD_TOKEN` en variables
- Check logs para errores de autenticación
- Verificar permisos del bot en Discord

#### Database Issues
- Railway filesystem es persistente
- SQLite se recrea automáticamente si se corrompe
- WAL mode previene la mayoría de corruption issues

#### Performance Issues
- Cache TTL se puede ajustar en `config.py`
- Cooldowns configurables para diferentes cargas
- Memory usage optimizado para Railway limits

### 8. Costos y Scaling

#### Railway Pricing
- Bot optimizado para Railway's free tier limits
- Memory usage eficiente < 512MB typical
- CPU usage optimizado con cache y cooldowns

#### Auto-scaling
- Single instance suficiente para la mayoría de servers
- Horizontal scaling no necesario para Discord bots
- Vertical scaling disponible si se necesita más memoria

## Soporte

Para issues específicos de Railway:
- Check Railway logs first
- Verify environment variables
- Test locally with same environment setup
- Railway Discord community para deployment issues