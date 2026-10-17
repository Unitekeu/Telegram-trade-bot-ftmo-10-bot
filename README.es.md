# FTMO Pro Bot 🚀

![FTMO Pro Bot](https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot/raw/main/screenshot.png)

**Bot de Telegram + MetaTrader 5** para trading automatizado, diseñado para **desafíos FTMO** y cuentas financiadas.

Genera señales, envía botones de confirmación en Telegram, ejecuta operaciones en MT5 y cumple estrictamente las reglas de riesgo de FTMO.

## Idiomas

- [English](README.md)
- [Español](README.es.md)
- [Shqip](README.sq.md)
- Français, Italiano, Ελληνικά, Deutsch — pronto

## Características

| Característica               | Descripción                                       |
|-----------------------------|--------------------------------------------------|
| Control por Telegram        | Control total, alertas y botones de confirmación |
| Trading Automático MT5      | Conexión directa a MetaTrader 5                  |
| Motor de Reglas FTMO        | Límites de drawdown y posiciones integrados       |
| Seguro para Challenge       | Diseñado para superar las reglas de FTMO         |
| Notificaciones en tiempo real| Alertas instantáneas de entradas, salidas y riesgos |
| Configuración fácil         | Configuración simple con `.env`                  |

## Símbolos Soportados

- **XAUUSD** (Oro)
- **USDJPY**
- **BTCUSD**

## Estrategia

Señales generadas en el timeframe **M15** utilizando:

- EMA 20 / 50 / 200
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)

## Gestión de Riesgo (Reglas FTMO)

| Regla                      | Valor          |
|----------------------------|----------------|
| Máx. operaciones abiertas  | 3              |
| Riesgo por operación       | 0.5%           |
| Stop Loss mínimo           | 50 puntos      |
| Máx. drawdown diario       | 5%             |
| Máx. drawdown total        | 4%             |

## Instalación

1. Clona el repositorio
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. Instala las dependencias
   ```bash
   pip install -r requirements.txt
   ```

3. Crea y edita `.env`
   ```bash
   cp .env.example .env
   ```

4. Ejecuta
   ```bash
   python telegram_bot.py
   ```

## Comandos de Telegram

| Comando                              | Descripción                           |
|--------------------------------------|--------------------------------------|
| `/start`                             | Iniciar el bot                       |
| `/connect`                           | Conectar a MT5                       |
| `/status`                            | Mostrar estado y operaciones         |
| `/scan`                              | Escanear nuevas señales              |
| `/manual BUY GOLD 0.02 60 120`       | Operación manual de compra           |
| `/manual SELL USDJPY 0.10 80 160`    | Operación manual de venta            |
| `/closeall`                          | Cerrar todas las posiciones          |

## Advertencia

> Úsalo primero en una **cuenta demo**. El trading implica riesgo de pérdida. Esto no es asesoramiento financiero.

## Requisitos

- Python 3.10+
- MetaTrader 5
- Token de Bot de Telegram
