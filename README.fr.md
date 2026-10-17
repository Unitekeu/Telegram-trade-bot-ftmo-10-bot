# FTMO Pro Bot 🚀

![FTMO Pro Bot](https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot/raw/main/screenshot.png)

**Bot Telegram + MetaTrader 5** pour le trading automatisé, conçu pour les **défis FTMO** et les comptes financés.

Il génère des signaux, envoie des boutons de confirmation sur Telegram, exécute les trades sur MT5 et respecte strictement les règles de risque FTMO.

## Langues

- [English](README.md)
- [Français](README.fr.md)
- [Shqip](README.sq.md)
- Italiano, Ελληνικά, Deutsch, Español — bientôt

## Fonctionnalités

| Fonctionnalité               | Description                                      |
|-----------------------------|--------------------------------------------------|
| Contrôle Telegram           | Contrôle total, alertes et boutons de confirmation |
| Trading Automatique MT5     | Connexion directe à MetaTrader 5                 |
| Moteur de Règles FTMO       | Limites de drawdown et de positions intégrées    |
| Sécurisé Challenge         | Conçu pour respecter les règles FTMO             |
| Notifications en temps réel | Alertes instantanées pour entrées, sorties et risques |
| Configuration facile        | Configuration simple avec `.env`                 |

## Symboles Supportés

- **XAUUSD** (Or)
- **USDJPY**
- **BTCUSD**

## Stratégie

Signaux générés sur le timeframe **M15** en utilisant :

- EMA 20 / 50 / 200
- RSI (14)
- MACD (12, 26, 9)
- ATR (14)

## Gestion des Risques (Règles FTMO)

| Règle                       | Valeur         |
|----------------------------|----------------|
| Max trades ouverts         | 3              |
| Risque par trade           | 0.5%           |
| Stop Loss minimum          | 50 points      |
| Max drawdown journalier    | 5%             |
| Max drawdown total         | 4%             |

## Installation

1. Cloner le dépôt
   ```bash
   git clone https://github.com/Unitekeu/Telegram-trade-bot-ftmo-10-bot.git
   cd Telegram-trade-bot-ftmo-10-bot
   ```

2. Installer les dépendances
   ```bash
   pip install -r requirements.txt
   ```

3. Créer et éditer `.env`
   ```bash
   cp .env.example .env
   ```

4. Lancer
   ```bash
   python telegram_bot.py
   ```

## Commandes Telegram

| Commande                             | Description                          |
|--------------------------------------|--------------------------------------|
| `/start`                             | Démarrer le bot                     |
| `/connect`                           | Se connecter à MT5                   |
| `/status`                            | Afficher le statut et les trades     |
| `/scan`                              | Scanner de nouveaux signaux          |
| `/manual BUY GOLD 0.02 60 120`       | Trade manuel achat                   |
| `/manual SELL USDJPY 0.10 80 160`    | Trade manuel vente                   |
| `/closeall`                          | Fermer toutes les positions          |

## Avertissement

> Utilisez d'abord sur un **compte démo**. Le trading comporte un risque de perte. Ceci n'est pas un conseil financier.

## Prérequis

- Python 3.10+
- MetaTrader 5
- Token Bot Telegram
