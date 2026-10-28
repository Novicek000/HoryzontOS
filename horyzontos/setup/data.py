"""Listy dla instalatora: strefy czasowe (w układzie klasycznej listy), ustawienia regionalne i klawiatury."""

# (przesunięcie w minutach, etykieta PL, etykieta EN, strefa IANA)
TIMEZONES = [
    (-720, "Linia zmiany daty", "International Date Line West", "Etc/GMT+12"),
    (-660, "Wyspa Midway, Samoa", "Midway Island, Samoa", "Pacific/Pago_Pago"),
    (-600, "Hawaje", "Hawaii", "Pacific/Honolulu"),
    (-540, "Alaska", "Alaska", "America/Anchorage"),
    (-480, "Czas pacyficzny (USA i Kanada); Tijuana", "Pacific Time (US & Canada); Tijuana", "America/Los_Angeles"),
    (-420, "Arizona", "Arizona", "America/Phoenix"),
    (-420, "Czas górski (USA i Kanada)", "Mountain Time (US & Canada)", "America/Denver"),
    (-360, "Ameryka Środkowa", "Central America", "America/Guatemala"),
    (-360, "Czas środkowy (USA i Kanada)", "Central Time (US & Canada)", "America/Chicago"),
    (-360, "Gwadalajara, Meksyk, Monterrey", "Guadalajara, Mexico City, Monterrey", "America/Mexico_City"),
    (-300, "Bogota, Lima, Quito", "Bogota, Lima, Quito", "America/Bogota"),
    (-300, "Czas wschodni (USA i Kanada)", "Eastern Time (US & Canada)", "America/New_York"),
    (-240, "Czas atlantycki (Kanada)", "Atlantic Time (Canada)", "America/Halifax"),
    (-240, "Caracas, La Paz", "Caracas, La Paz", "America/Caracas"),
    (-240, "Santiago", "Santiago", "America/Santiago"),
    (-210, "Nowa Fundlandia", "Newfoundland", "America/St_Johns"),
    (-180, "Brasília", "Brasilia", "America/Sao_Paulo"),
    (-180, "Buenos Aires, Georgetown", "Buenos Aires, Georgetown", "America/Argentina/Buenos_Aires"),
    (-120, "Środkowoatlantycki", "Mid-Atlantic", "Atlantic/South_Georgia"),
    (-60, "Azory", "Azores", "Atlantic/Azores"),
    (-60, "Wyspy Zielonego Przylądka", "Cape Verde Is.", "Atlantic/Cape_Verde"),
    (0, "Casablanca, Monrovia", "Casablanca, Monrovia", "Africa/Casablanca"),
    (0, "Czas uniwersalny Greenwich: Dublin, Edynburg, Lizbona, Londyn",
     "Greenwich Mean Time: Dublin, Edinburgh, Lisbon, London", "Europe/London"),
    (60, "Amsterdam, Berlin, Berno, Rzym, Sztokholm, Wiedeń", "Amsterdam, Berlin, Bern, Rome, Stockholm, Vienna",
     "Europe/Berlin"),
    (60, "Belgrad, Bratysława, Budapeszt, Lublana, Praga", "Belgrade, Bratislava, Budapest, Ljubljana, Prague",
     "Europe/Prague"),
    (60, "Bruksela, Kopenhaga, Madryt, Paryż", "Brussels, Copenhagen, Madrid, Paris", "Europe/Paris"),
    (60, "Sarajewo, Skopje, Warszawa, Zagrzeb", "Sarajevo, Skopje, Warsaw, Zagreb", "Europe/Warsaw"),
    (60, "Afryka Środkowo-Zachodnia", "West Central Africa", "Africa/Lagos"),
    (120, "Ateny, Bukareszt", "Athens, Bucharest", "Europe/Athens"),
    (120, "Kair", "Cairo", "Africa/Cairo"),
    (120, "Harare, Pretoria", "Harare, Pretoria", "Africa/Johannesburg"),
    (120, "Helsinki, Kijów, Ryga, Sofia, Tallinn, Wilno", "Helsinki, Kyiv, Riga, Sofia, Tallinn, Vilnius",
     "Europe/Kyiv"),
    (120, "Jerozolima", "Jerusalem", "Asia/Jerusalem"),
    (180, "Bagdad", "Baghdad", "Asia/Baghdad"),
    (180, "Kuwejt, Rijad", "Kuwait, Riyadh", "Asia/Riyadh"),
    (180, "Mińsk", "Minsk", "Europe/Minsk"),
    (180, "Moskwa, Sankt Petersburg", "Moscow, St. Petersburg", "Europe/Moscow"),
    (180, "Nairobi", "Nairobi", "Africa/Nairobi"),
    (180, "Stambuł", "Istanbul", "Europe/Istanbul"),
    (210, "Teheran", "Tehran", "Asia/Tehran"),
    (240, "Abu Zabi, Maskat", "Abu Dhabi, Muscat", "Asia/Dubai"),
    (240, "Baku, Tbilisi, Erywań", "Baku, Tbilisi, Yerevan", "Asia/Baku"),
    (270, "Kabul", "Kabul", "Asia/Kabul"),
    (300, "Jekaterynburg", "Ekaterinburg", "Asia/Yekaterinburg"),
    (300, "Islamabad, Karaczi, Taszkent", "Islamabad, Karachi, Tashkent", "Asia/Karachi"),
    (330, "Ćennaj, Kalkuta, Mumbaj, Nowe Delhi", "Chennai, Kolkata, Mumbai, New Delhi", "Asia/Kolkata"),
    (345, "Katmandu", "Kathmandu", "Asia/Kathmandu"),
    (360, "Ałmaty, Astana, Dhaka", "Almaty, Astana, Dhaka", "Asia/Dhaka"),
    (390, "Rangun", "Rangoon", "Asia/Yangon"),
    (420, "Bangkok, Hanoi, Dżakarta", "Bangkok, Hanoi, Jakarta", "Asia/Bangkok"),
    (420, "Krasnojarsk, Nowosybirsk", "Krasnoyarsk, Novosibirsk", "Asia/Novosibirsk"),
    (480, "Pekin, Chongqing, Hongkong, Urumczi", "Beijing, Chongqing, Hong Kong, Urumqi", "Asia/Shanghai"),
    (480, "Irkuck, Ułan Bator", "Irkutsk, Ulaan Bataar", "Asia/Irkutsk"),
    (480, "Kuala Lumpur, Singapur", "Kuala Lumpur, Singapore", "Asia/Singapore"),
    (480, "Perth", "Perth", "Australia/Perth"),
    (480, "Tajpej", "Taipei", "Asia/Taipei"),
    (540, "Osaka, Sapporo, Tokio", "Osaka, Sapporo, Tokyo", "Asia/Tokyo"),
    (540, "Seul", "Seoul", "Asia/Seoul"),
    (540, "Jakuck", "Yakutsk", "Asia/Yakutsk"),
    (570, "Adelaide", "Adelaide", "Australia/Adelaide"),
    (570, "Darwin", "Darwin", "Australia/Darwin"),
    (600, "Brisbane", "Brisbane", "Australia/Brisbane"),
    (600, "Canberra, Melbourne, Sydney", "Canberra, Melbourne, Sydney", "Australia/Sydney"),
    (600, "Guam, Port Moresby", "Guam, Port Moresby", "Pacific/Port_Moresby"),
    (600, "Hobart", "Hobart", "Australia/Hobart"),
    (600, "Władywostok", "Vladivostok", "Asia/Vladivostok"),
    (660, "Magadan, Wyspy Salomona, Nowa Kaledonia", "Magadan, Solomon Is., New Caledonia", "Asia/Magadan"),
    (720, "Auckland, Wellington", "Auckland, Wellington", "Pacific/Auckland"),
    (720, "Fidżi, Kamczatka, Wyspy Marshalla", "Fiji, Kamchatka, Marshall Is.", "Pacific/Fiji"),
    (780, "Nuku'alofa", "Nuku'alofa", "Pacific/Tongatapu"),
]


def tz_label(entry, lang):
    off, pl, en, _ = entry
    if off == 0:
        pre = "(GMT)"
    else:
        s = "+" if off > 0 else "-"
        pre = f"(GMT{s}{abs(off) // 60:02d}:{abs(off) % 60:02d})"
    return f"{pre} {pl if lang == 'pl' else en}"


def fixed_zone(offset_min):
    """Strefa bez zmiany czasu (gdy odznaczono automatyczne uwzględnianie zmian): Etc/GMT∓N."""
    if offset_min % 60:
        return None
    h = offset_min // 60
    if h == 0:
        return "Etc/UTC"
    return f"Etc/GMT{'-' if h > 0 else '+'}{abs(h)}"


# (locale, nazwa PL, nazwa EN, kraj PL, kraj EN, układ klawiatury, domyślna strefa)
LOCALES = [
    ("pl_PL.UTF-8", "Polski", "Polish", "Polska", "Poland", "pl", "Europe/Warsaw"),
    ("en_US.UTF-8", "Angielski (Stany Zjednoczone)", "English (United States)", "Stany Zjednoczone",
     "United States", "us", "America/New_York"),
    ("en_GB.UTF-8", "Angielski (Wielka Brytania)", "English (United Kingdom)", "Wielka Brytania",
     "United Kingdom", "gb", "Europe/London"),
    ("de_DE.UTF-8", "Niemiecki (Niemcy)", "German (Germany)", "Niemcy", "Germany", "de", "Europe/Berlin"),
    ("cs_CZ.UTF-8", "Czeski", "Czech", "Czechy", "Czech Republic", "cz", "Europe/Prague"),
    ("sk_SK.UTF-8", "Słowacki", "Slovak", "Słowacja", "Slovakia", "sk", "Europe/Prague"),
    ("uk_UA.UTF-8", "Ukraiński", "Ukrainian", "Ukraina", "Ukraine", "ua", "Europe/Kyiv"),
    ("fr_FR.UTF-8", "Francuski (Francja)", "French (France)", "Francja", "France", "fr", "Europe/Paris"),
    ("es_ES.UTF-8", "Hiszpański (Hiszpania)", "Spanish (Spain)", "Hiszpania", "Spain", "es", "Europe/Paris"),
    ("it_IT.UTF-8", "Włoski (Włochy)", "Italian (Italy)", "Włochy", "Italy", "it", "Europe/Berlin"),
    ("ru_RU.UTF-8", "Rosyjski", "Russian", "Rosja", "Russia", "ru", "Europe/Moscow"),
]

# (układ xkb, wariant, nazwa PL, nazwa EN, mapa konsoli)
KEYBOARDS = [
    ("pl", "", "Polski (programisty)", "Polish (Programmers)", "pl2"),
    ("pl", "qwertz", "Polski (214)", "Polish (214)", "pl3"),
    ("us", "", "Stany Zjednoczone", "US", "us"),
    ("us", "intl", "Stany Zjednoczone - międzynarodowy", "United States-International", "us-acentos"),
    ("gb", "", "Wielka Brytania", "United Kingdom", "uk"),
    ("de", "", "Niemiecki", "German", "de"),
    ("cz", "", "Czeski", "Czech", "cz"),
    ("sk", "", "Słowacki", "Slovak", "sk-qwertz"),
    ("ua", "", "Ukraiński", "Ukrainian", "ua"),
    ("fr", "", "Francuski", "French", "fr"),
    ("es", "", "Hiszpański", "Spanish", "es"),
    ("it", "", "Włoski", "Italian", "it"),
    ("ru", "", "Rosyjski", "Russian", "ru"),
]
