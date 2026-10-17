# FTMO Pro Bot 🚀

![FTMO Pro Bot](https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot/raw/main/screenshot.png)

**Bot Telegram + MetaTrader 5** për tregtim automatik, i ndërtuar për **sfidat FTMO** dhe llogaritë e financuara.

Gjeneron sinjale, dërgon butona konfirmimi në Telegram, ekzekuton tregti në MT5 dhe respekton rreptësisht rregullat e riskut të FTMO.

## Gjuhët

- [English](README.md)
- [Shqip](README.sq.md)
- Français, Italiano, Ελληνικά, Deutsch, Español — së shpejti

## Karakteristikat

| Karakteristika              | Përshkrim                                         |
|-----------------------------|--------------------------------------------------|
| Kontrolli nga Telegram      | Kontroll i plotë, njoftime dhe butona konfirmimi |
| Tregtim Automatik MT5       | Lidhje e drejtpërdrejtë me MetaTrader 5            |
| Motori i Rregullave FTMO    | Kufizime drawdown dhe pozicionesh të integruara  |
| I sigurt për Challenge      | I dizajnuar për të kaluar rregullat e FTMO        |
| Njoftime në kohë reale     | Alerta të menjëhershme për hyrje, dalje dhe risk  |
| Setup i lehtë              | Konfigurim i thjeshtë me `.env`                   |

## Simbolet e Mbështetura

- **XAUUSD** (Gold)
- **USDJPY**
- **BTCUSD**

## Strategjia

Sinjalet gjenerohen në timeframe **M15** duke përdorur:

- EMA 20 / 50 / 200
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)

## Menaxhimi i Riskut (Rregullat FTMO)

| Rregulli                   | Vlera          |
|----------------------------|----------------|
| Max tregti të hapura       | 3              |
| Risk për tregti            | 0.5%           |
| Stop Loss minimum          | 50 pika        |
| Max drawdown ditor         | 5%             |
| Max drawdown total         | 4%             |

## Instalimi

1. Klono repon
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. Instalo varësitë
   ```bash
   pip install -r requirements.txt
   ```

3. Krijo dhe plotëso `.env`
   ```bash
   cp .env.example .env
   ```

4. Nis botin
   ```bash
   python telegram_bot.py
   ```

## Komandat në Telegram

| Komanda                              | Përshkrim                          |
|--------------------------------------|-----------------------------------|
| `/start`                             | Nise botin                        |
| `/connect`                           | Lidhu me MT5                      |
| `/status`                            | Shfaq statusin dhe tregtitë        |
| `/scan`                              | Skano për sinjale të reja            |
| `/manual BUY GOLD 0.02 60 120`       | Tregti manuale buy                |
| `/manual SELL USDJPY 0.10 80 160`    | Tregti manuale sell               |
| `/closeall`                          | Mbyll të gjitha pozicionet         |

## Paralajmërim

> Përdore së pari në **llogari demo**. Tregtimi ka risk humbjeje. Kjo nuk është këshillë financiare.

## Kërkesat

- Python 3.10+
- MetaTrader 5
- Token i Telegram Bot
