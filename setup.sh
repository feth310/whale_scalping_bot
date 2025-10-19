#!/bin/bash
echo "🚀 Installation du Whale Scalping Bot..."

# 1️⃣ Créer dossier du bot
mkdir -p ~/scalping-bot
cd ~/scalping-bot

# 2️⃣ Mettre à jour le système
echo "🔄 Mise à jour du système..."
apt update -y && apt upgrade -y

# 3️⃣ Installer Python & pip
echo "🐍 Vérification de Python..."
apt install -y python3 python3-pip

# 4️⃣ Installer dépendances
echo "📦 Installation des librairies..."
pip install --upgrade pip
pip install ccxt pandas pandas-ta-classic requests python-dotenv

# 5️⃣ Télécharger le script principal depuis ton GitHub
echo "⬇️ Téléchargement du bot..."
curl -o main.py https://raw.githubusercontent.com/TON_PSEUDO/whale_scalping_bot/main/main.py

# 6️⃣ Créer le fichier .env (identifiants et paramètres)
echo "🧩 Configuration initiale..."
cat > .env <<EOF
KUCOIN_API_KEY=68f4efc5f9a9a300014c03d5
KUCOIN_API_SECRET=ea4ef3d5-45ab-48a8-a49e-eb77ae164191
KUCOIN_PASSPHRASE=Pavillion310

SMTP_USER=nisf2531@gmail.com 
SMTP_PASS=avlc juuy bwvz oozh
TO_EMAIL=nisf2531@gmail.com

TOTAL_CAPITAL_USDT=18
CHECK_INTERVAL=60
AUTO_TRADE=true
LEVERAGE=3
EOF

# 7️⃣ Lancer le bot
echo "🚀 Lancement du bot..."
python3 main.py
