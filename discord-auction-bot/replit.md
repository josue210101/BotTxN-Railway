# Discord Auction Bot - System Architecture

## Overview

This is a Discord auction bot built with Python using discord.py, designed for deployment on Railway hosting. The system provides a complete auction platform with automated timers, multi-image support, bidding validation, private DM notifications, and administrative controls.

## System Architecture

### Backend Architecture
- **Language**: Python 3.x
- **Framework**: discord.py for Discord API integration
- **Database**: SQLite with aiosqlite for async operations
- **Deployment**: Railway hosting platform
- **Architecture Pattern**: Component-based modular design

### Database Design
- **Storage**: SQLite database with optimized settings (WAL mode, memory temp store)
- **Tables**: 
  - `auctions` - Core auction data with metadata
  - `bids` - Bidding history and user interactions
  - Additional tables for user management and caching
- **Optimization**: Connection pooling, busy timeout handling, and indexing

### Core Components
1. **Bot Core** (`main.py`, `auction_bot.py`) - Main bot initialization and Discord client
2. **Command System** (`commands.py`) - Slash command handlers for auction operations
3. **Database Layer** (`database.py`) - Async SQLite operations with connection management
4. **Cache Manager** (`cache_manager.py`) - In-memory caching with TTL for performance
5. **Timer System** (`timer_manager.py`) - Automated auction end scheduling
6. **UI Components** (`views.py`) - Discord UI interactions (buttons, modals)
7. **Utilities** (`utils.py`) - Helper functions and embed generation

## Key Components

### Cache Management
- **Auction Cache**: 30-second TTL for active auction data
- **Bid Cache**: 10-second TTL for recent bidding activity  
- **User Cache**: 5-minute TTL for user information
- **Cleanup**: Automatic cache cleanup every 60 seconds

### Timer Management
- **Automatic Scheduling**: Auctions end automatically based on duration
- **Cleanup Tasks**: Background processes to handle expired auctions
- **Optimization**: Dynamic timer adjustment for auctions ending soon

### User Interface
- **Slash Commands**: Modern Discord slash command interface
- **Interactive Buttons**: Quick bid buttons (+1x, +5x, +10x multipliers)
- **Image Navigation**: Multi-image support with navigation controls
- **Real-time Updates**: Live auction status updates

### Performance Optimizations
- **Connection Pooling**: SQLite connection reuse and timeout handling
- **Update Throttling**: Rate limiting for message updates (2-second throttle)
- **Bid Cooldowns**: 1-second cooldown between bids, 0.5s for quick bids
- **Async Operations**: Non-blocking database and Discord API calls

## Data Flow

1. **Auction Creation**: User creates auction via slash command → Data stored in database → Timer scheduled → Embed posted
2. **Bidding Process**: User clicks bid button → Validation checks → Database update → Cache invalidation → UI refresh
3. **Auction End**: Timer triggers → Final bid calculation → Winner notification → Database cleanup

## External Dependencies

### Required Packages
- `discord.py==2.3.2` - Discord API client
- `aiosqlite==0.19.0` - Async SQLite operations
- `aiohttp==3.9.1` - HTTP client for Discord interactions

### Discord Permissions
- Read Messages
- Send Messages
- Use Slash Commands
- Embed Links
- Attach Files
- Manage Messages (for admin functions)

## Deployment Strategy

### Railway Deployment (Primary Target)
- **Environment Variables**: `DISCORD_TOKEN` (required), `GUILD_ID` (optional)
- **Database**: SQLite file persistence on Railway's filesystem with WAL mode
- **Logging**: Structured logging to stdout for Railway's log aggregation
- **Health Checks**: Bot presence as health indicator
- **Port Configuration**: Bot runs without port binding (background service)
- **File System**: Persistent storage for SQLite database and logs
- **Process Management**: Single process with automatic restart on Railway

### Configuration Management
- Environment-based configuration through `Config` class
- Centralized settings in `config.py` for easy adjustments
- Support for development and production environments

### Data Persistence
- SQLite database file stored in Railway's persistent filesystem
- WAL mode for better concurrent access
- Automatic backup considerations for production use

## Changelog
```
Changelog:
- July 07, 2025. Initial setup
- July 07, 2025. Fixed auction completion error "No se pudo cargar la información de finalización" with robust error handling in notify_auction_end function
- July 07, 2025. Restored original design: "Puja Rápida" (min increment) and "Puja Personalizada" (custom amount) buttons, creator name display, user names in bid history, and DM notifications when outbid
- July 07, 2025. Optimized image carousel with preloading, local cache, dynamic indicator button (📷 1/3), instant navigation, and improved user experience
- July 07, 2025. Fixed bid button functionality: "Puja Rápida" and "Puja Personalizada" now work correctly by calling command methods properly
- July 07, 2025. Implemented user-specific carousel navigation: each user sees their own image selection independently (ephemeral responses)
- July 07, 2025. Added /finalizar command for Admin/Moderador roles to manually end auctions, improved creator display to show actual usernames instead of "usuario desconocido", enhanced Auction member role detection for multiple role name variations
- July 07, 2025. Fixed latency issues in /subasta command by optimizing image validation (removed heavy format checks), fixed "interaction already responded" errors in bid buttons by implementing proper defer() pattern with followup responses
- July 07, 2025. Enhanced DM notifications when outbid to include channel information: shows channel mention, payment material details, and organized layout for better user experience
- July 07, 2025. FIXED CRITICAL BID ERRORS: Eliminated "interaction already responded" errors by implementing independent bid logic for buttons (avoiding double defer calls), maintaining all functionality while ensuring stable bid processing
- July 07, 2025. RESOLVED DATABASE ATTRIBUTE ERROR: Fixed 'OptimizedAuctionBot' object has no attribute 'database' error by correcting database references from self.bot.database to self.bot.db throughout views.py and commands.py - bid buttons now fully functional
- July 07, 2025. Implemented public bid confirmations with auto-deletion: bid messages now appear publicly showing user name and amount, then automatically delete after 5 seconds to keep channels clean while providing transparency
- July 07, 2025. Expanded bid history display: increased "Últimas Pujas" section from showing 3 to 5 recent bids for better auction activity visibility and user tracking
- July 07, 2025. Fixed CustomBidModal auto-deletion error: resolved "'CustomBidModal' object has no attribute '_delete_message_after_delay'" by adding _auto_delete_message method to modal class - both bid types now fully functional with public confirmations
- July 07, 2025. System maintenance: Finalized all 6 active auctions to clean system state - bot ready for fresh auction activities with all enhanced features operational
- July 07, 2025. Ultra-fast message deletion: Reduced bid confirmation auto-deletion time from 5 seconds to 0.5 seconds for minimal visual impact while maintaining transparency
- July 07, 2025. Implemented truly independent image carousel: Users click "📷 Ver Imágenes" to open personal carousel window, preventing navigation interference between users while maintaining individual image selection
- July 07, 2025. Fixed number formatting: Eliminated ".0" decimals in bid amounts (e.g., "10K" instead of "10.0K") for cleaner display across all auction interfaces
- July 07, 2025. Fixed bid history display: Increased database query limits and cache capacity to properly show all 5 recent bids instead of truncating at 2
- July 07, 2025. Reverted auction creation optimizations: Restored stable sequential operations after asyncio import errors, maintaining reliable auction publishing functionality
- July 07, 2025. Reset auction ID counter: Cleaned database and reset autoincrement sequences, next auction will start at ID #1 with clean numbering system
```

## User Preferences
```
Preferred communication style: Simple, everyday language.
Deployment target: Railway hosting platform (always optimize for Railway compatibility).
```