# Конфігураційні налаштування бота
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не встановлено в .env файлі!")

MODERATOR_CHAT_ID = int(os.getenv('MODERATOR_CHAT_ID', 0))
PUBLIC_CHANNEL_ID = os.getenv('PUBLIC_CHANNEL_ID', '')
BOT_OWNER_ID = int(os.getenv('BOT_OWNER_ID', 0))

if BOT_OWNER_ID == 0:
    raise ValueError("BOT_OWNER_ID не встановлено в .env файлі!")

DATABASE_URL = "sqlite:///database.db"

# Обмеження для бази даних
MAX_RIOT_ID_LENGTH = 50       # Максимальна довжина Riot ID
MAX_RANK_LENGTH = 20          # Максимальна довжина рангу
MAX_ROLE_LENGTH = 100         # Максимальна довжина ролей
MAX_BIO_LENGTH = 500          # Максимальна довжина "про себе"
MAX_CONTACT_LENGTH = 25       # Максимальна довжина контакту
MAX_USERNAME_LENGTH = 50      # Максимальна довжина username
MAX_STATUS_LENGTH = 20        # Максимальна довжина статусу

# Обмеження вибору
MAX_AGENTS_SELECTION = 8      # Максимум агентів в анкеті
MAX_ROLES_SELECTION = 4       # Максиму м ролей в анкеті

# Причини відхилення анкет
REJECTION_REASONS = {
    "bad_id": "Некоректний ID",
    "offensive": "Образливий зміст",
    "insufficient": "Недостатньо інформації",
    "rules": "Порушення правил",
    "other": "Інше",
    "custom": "💬 Своя причина"
}

# Список всіх агентів Valorant (станом на 2025)
ALL_AGENTS = sorted([
    # Дуеліанти
    "Jett", "Phoenix", "Raze", "Reyna", "Yoru", "Neon", "Iso", "Waylay",
    # Стражі
    "Killjoy", "Cypher", "Sage", "Chamber", "Deadlock", "Vyse", "Veto",
    # Ініціатори
    "Sova", "Breach", "Skye", "KAY/O", "Fade", "Gekko", "Tejo",
    # Контролери
    "Brimstone", "Viper", "Omen", "Astra", "Harbor", "Clove"
])

# Регіони та сервери з прапорцями
REGIONS = {
    "🇺🇸 Північна Америка (NA)": {
        "🇺🇸 Орегон (Портленд)": "na_oregon",
        "🇺🇸 Північна Каліфорнія (Сан-Хосе)": "na_california",
        "🇺🇸 Техас (Даллас)": "na_texas",
        "🇺🇸 Джорджія (Атланта)": "na_georgia",
        "🇺🇸 Вірджинія (Ашберн)": "na_virginia",
        "🇺🇸 Іллінойс (Чикаго)": "na_illinois"
    },
    "🇪🇺 Європа (EMEA/EU)": {
        "🇬🇧 Лондон (Великобританія)": "eu_london",
        "🇫🇷 Париж (Франція)": "eu_paris",
        "🇩🇪 Франкфурт (Німеччина)": "eu_frankfurt",
        "🇸🇪 Стокгольм (Швеція)": "eu_stockholm",
        "🇹🇷 Стамбул (Туреччина)": "eu_istanbul",
        "🇵🇱 Варшава (Польща)": "eu_warsaw",
        "🇪🇸 Мадрид (Іспанія)": "eu_madrid",
        "🇧🇭 Бахрейн (Манама)": "eu_bahrain"
    },
    "🌏 Азіатсько-Тихоокеанський регіон (AP)": {
        "🇯🇵 Токіо (Японія)": "ap_tokyo",
        "🇸🇬 Сингапур": "ap_singapore",
        "🇦🇺 Сідней (Австралія)": "ap_sydney",
        "🇮🇳 Мумбаї (Індія)": "ap_mumbai",
        "🇭🇰 Гонконг (Китай)": "ap_hongkong",
        "🇰🇷 Сеул (Південна Корея)": "ap_seoul"
    },
    "🇲🇽 Латинська Америка (LATAM)": {
        "🇨🇱 Сантьяго (Чилі)": "latam_santiago",
        "🇲🇽 Мехіко (Мексика)": "latam_mexico",
        "🇺🇸 Маямі (США)": "latam_miami"
    },
    "🇧🇷 Бразилія (BR)": {
        "🇧🇷 Сан-Паулу (Бразилія)": "br_saopaulo"
    },
    "🇰🇷 Корея (KR)": {
        "🇰🇷 Сеул (Південна Корея)": "kr_seoul"
    },
    "🇨🇳 Китай (CN)": {
        "🇨🇳 Гуанчжоу": "cn_guangzhou",
        "🇨🇳 Нанкін": "cn_nanjing",
        "🇨🇳 Чунцін": "cn_chongqing",
        "🇨🇳 Тяньцзінь": "cn_tianjin"
    }
}

# Словник для скорочення назв регіонів
REGION_SHORT_CODES = {
    "🇺🇸 Північна Америка (NA)": "na",
    "🇪🇺 Європа (EMEA/EU)": "eu",
    "🌏 Азіатсько-Тихоокеанський регіон (AP)": "ap",
    "🇲🇽 Латинська Америка (LATAM)": "latam",
    "🇧🇷 Бразилія (BR)": "br",
    "🇰🇷 Корея (KR)": "kr",
    "🇨🇳 Китай (CN)": "cn"
}

# Ігрові ранги Valorant
RANKS = [
    "Iron 1", "Iron 2", "Iron 3",
    "Bronze 1", "Bronze 2", "Bronze 3",
    "Silver 1", "Silver 2", "Silver 3",
    "Gold 1", "Gold 2", "Gold 3",
    "Platinum 1", "Platinum 2", "Platinum 3",
    "Diamond 1", "Diamond 2", "Diamond 3",
    "Ascendant 1", "Ascendant 2", "Ascendant 3",
    "Immortal 1", "Immortal 2", "Immortal 3",
    "Radiant"
]

# Ролі в грі
ROLES = ["Дуелянт", "Захисник", "Контролер", "Ініціатор"]