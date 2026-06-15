PROVIDER_PRESETS = {
    "gmail": {
        "name": "Gmail",
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["app_password"],
        "daily_limit": 500,
        "daily_limit_workspace": 2000,
        "spf_include": "_spf.google.com",
        "app_password_url": "https://myaccount.google.com/apppasswords",
        "notes_en": "Requires an App Password — generate one in Google Account → Security → App Passwords",
        "notes_cs": "Vyžaduje heslo aplikace — vygenerujte ho v Google účet → Zabezpečení → Hesla aplikací",
        "notes_de": "Erfordert ein App-Passwort — erstellen Sie eines unter Google-Konto → Sicherheit → App-Passwörter",
        "notes_ru": "Требуется пароль приложения — создайте его в Аккаунт Google → Безопасность → Пароли приложений",
        "notes_es": "Requiere una contraseña de aplicación — genérala en Cuenta de Google → Seguridad → Contraseñas de aplicaciones",
        "mx_patterns": ["google.com", "googlemail.com", "gmail-smtp-in.l.google.com"],
    },
    "outlook": {
        "name": "Outlook / Microsoft 365",
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["app_password"],
        "daily_limit": 10000,
        "spf_include": "spf.protection.outlook.com",
        "app_password_url": "https://account.live.com/proofs/AppPassword",
        "notes_en": "Requires an App Password — enable 2FA, then generate one in Microsoft Account → Security → App Passwords",
        "notes_cs": "Vyžaduje heslo aplikace — zapněte 2FA, pak vygenerujte heslo v Microsoft účet → Zabezpečení → Hesla aplikací",
        "notes_de": "Erfordert ein App-Passwort — aktivieren Sie 2FA, dann erstellen Sie eines unter Microsoft-Konto → Sicherheit → App-Passwörter",
        "notes_ru": "Требуется пароль приложения — включите 2FA, затем создайте пароль в Microsoft аккаунт → Безопасность → Пароли приложений",
        "notes_es": "Requiere una contraseña de aplicación — activa 2FA, luego genera una en Cuenta Microsoft → Seguridad → Contraseñas de aplicaciones",
        "mx_patterns": ["outlook.com", "microsoft.com", "hotmail.com", "protection.outlook.com"],
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["app_password"],
        "daily_limit": 500,
        "spf_include": "spf.mail.yahoo.com",
        "app_password_url": "https://login.yahoo.com/myaccount/security/app-password",
        "notes_en": "Requires an App Password — generate one in Yahoo Account Security settings",
        "notes_cs": "Vyžaduje heslo aplikace — vygenerujte ho v nastavení zabezpečení Yahoo účtu",
        "notes_de": "Erfordert ein App-Passwort — erstellen Sie eines in den Yahoo-Kontosicherheitseinstellungen",
        "notes_ru": "Требуется пароль приложения — создайте его в настройках безопасности аккаунта Yahoo",
        "notes_es": "Requiere una contraseña de aplicación — genérala en la configuración de seguridad de tu cuenta Yahoo",
        "mx_patterns": ["yahoodns.net", "yahoo.com"],
    },
    "seznam": {
        "name": "Seznam.cz",
        "smtp_host": "smtp.seznam.cz",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["plain"],
        "daily_limit": 500,
        "spf_include": "seznam.cz",
        "notes_en": "Use your Seznam.cz email and password. Enable SMTP access in email settings.",
        "notes_cs": "Použijte svůj email a heslo k Seznam.cz. Povolte SMTP přístup v nastavení emailu.",
        "notes_de": "Verwenden Sie Ihre Seznam.cz-E-Mail und Passwort. Aktivieren Sie den SMTP-Zugang in den E-Mail-Einstellungen.",
        "notes_ru": "Используйте ваш email и пароль Seznam.cz. Включите SMTP-доступ в настройках почты.",
        "notes_es": "Usa tu email y contraseña de Seznam.cz. Habilita el acceso SMTP en la configuración del correo.",
        "mx_patterns": ["seznam.cz"],
    },
    "zoho": {
        "name": "Zoho Mail",
        "smtp_host": "smtp.zoho.com",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["plain", "app_password"],
        "daily_limit": 500,
        "spf_include": "zoho.com",
        "notes_en": "Use your Zoho account credentials or generate an App Password",
        "notes_cs": "Použijte přihlašovací údaje Zoho účtu nebo vygenerujte heslo aplikace",
        "notes_de": "Verwenden Sie Ihre Zoho-Kontodaten oder generieren Sie ein App-Passwort",
        "notes_ru": "Используйте учётные данные Zoho или сгенерируйте пароль приложения",
        "notes_es": "Usa las credenciales de tu cuenta Zoho o genera una contraseña de aplicación",
        "mx_patterns": ["zoho.com", "zoho.eu"],
    },
    "ses": {
        "name": "Amazon SES",
        "smtp_host": "email-smtp.{region}.amazonaws.com",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["api_key"],
        "daily_limit": 50000,
        "spf_include": "amazonses.com",
        "extra_fields": ["region"],
        "regions": ["us-east-1", "us-east-2", "us-west-2", "eu-west-1", "eu-central-1", "ap-south-1", "ap-southeast-2"],
        "notes_en": "Use IAM SMTP credentials (not AWS access keys). Select your SES region.",
        "notes_cs": "Použijte IAM SMTP přihlašovací údaje (ne AWS přístupové klíče). Vyberte svůj SES region.",
        "notes_de": "Verwenden Sie IAM-SMTP-Zugangsdaten (nicht AWS-Zugriffsschlüssel). Wählen Sie Ihre SES-Region.",
        "notes_ru": "Используйте SMTP-учётные данные IAM (не ключи доступа AWS). Выберите регион SES.",
        "notes_es": "Usa las credenciales SMTP de IAM (no las claves de acceso de AWS). Selecciona tu región SES.",
        "mx_patterns": [],
    },
    "sendgrid": {
        "name": "SendGrid",
        "smtp_host": "smtp.sendgrid.net",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["api_key"],
        "daily_limit": 100,
        "daily_limit_paid": 100000,
        "spf_include": "sendgrid.net",
        "notes_en": "Username is always 'apikey'. Use your SendGrid API key as password.",
        "notes_cs": "Uživatelské jméno je vždy 'apikey'. Jako heslo použijte svůj SendGrid API klíč.",
        "notes_de": "Benutzername ist immer 'apikey'. Verwenden Sie Ihren SendGrid-API-Schlüssel als Passwort.",
        "notes_ru": "Имя пользователя всегда 'apikey'. В качестве пароля используйте ваш API-ключ SendGrid.",
        "notes_es": "El usuario es siempre 'apikey'. Usa tu clave API de SendGrid como contraseña.",
        "default_username": "apikey",
        "mx_patterns": [],
    },
    "mailgun": {
        "name": "Mailgun",
        "smtp_host": "smtp.mailgun.org",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["plain"],
        "daily_limit": 5000,
        "spf_include": "mailgun.org",
        "notes_en": "Use your Mailgun SMTP credentials from the domain settings page.",
        "notes_cs": "Použijte SMTP přihlašovací údaje z nastavení domény v Mailgun.",
        "notes_de": "Verwenden Sie Ihre Mailgun-SMTP-Zugangsdaten aus den Domain-Einstellungen.",
        "notes_ru": "Используйте SMTP-учётные данные из настроек домена в Mailgun.",
        "notes_es": "Usa tus credenciales SMTP de Mailgun desde la página de configuración del dominio.",
        "mx_patterns": [],
    },
    "custom": {
        "name": "Custom SMTP",
        "smtp_host": "",
        "smtp_port": 587,
        "tls_mode": "starttls",
        "auth_methods": ["plain", "app_password"],
        "daily_limit": 100,
        "notes_en": "Enter your SMTP server details manually.",
        "notes_cs": "Zadejte údaje svého SMTP serveru ručně.",
        "notes_de": "Geben Sie Ihre SMTP-Serverdaten manuell ein.",
        "notes_ru": "Введите данные SMTP-сервера вручную.",
        "notes_es": "Introduce los datos de tu servidor SMTP manualmente.",
        "mx_patterns": [],
    },
}


def detect_provider(email: str) -> str | None:
    """Detect provider from email domain by checking MX records."""
    import dns.resolver

    domain = email.split("@")[1].lower()

    # Direct domain match first
    direct_map = {
        "gmail.com": "gmail",
        "googlemail.com": "gmail",
        "outlook.com": "outlook",
        "hotmail.com": "outlook",
        "live.com": "outlook",
        "yahoo.com": "yahoo",
        "yahoo.co.uk": "yahoo",
        "seznam.cz": "seznam",
        "email.cz": "seznam",
        "post.cz": "seznam",
        "spoluzaci.cz": "seznam",
        "zoho.com": "zoho",
    }
    if domain in direct_map:
        return direct_map[domain]

    # MX record lookup for custom domains
    try:
        answers = dns.resolver.resolve(domain, "MX")
        for rdata in answers:
            mx_host = str(rdata.exchange).lower().rstrip(".")
            for provider_key, preset in PROVIDER_PRESETS.items():
                for pattern in preset.get("mx_patterns", []):
                    if pattern in mx_host:
                        return provider_key
    except Exception:
        pass

    return None


def guess_smtp_from_mx(email: str) -> dict | None:
    """Try to guess SMTP settings from MX records for unknown providers."""
    import dns.resolver
    import socket
    import ssl

    domain = email.split("@")[1].lower()

    # Try MX lookup
    mx_host = None
    try:
        answers = dns.resolver.resolve(domain, "MX")
        best = min(answers, key=lambda r: r.preference)
        mx_host = str(best.exchange).lower().rstrip(".")
    except Exception:
        pass

    smtp_host = mx_host or f"mail.{domain}"

    # Probe which port is open (fast check, 2s timeout)
    port_configs = [
        (587, "starttls"),
        (465, "ssl"),
        (25, "none"),
    ]
    for port, tls in port_configs:
        try:
            sock = socket.create_connection((smtp_host, port), timeout=2)
            sock.close()
            return {
                "smtp_host": smtp_host,
                "smtp_port": port,
                "tls_mode": tls,
                "mx_host": mx_host,
                "guessed": True,
            }
        except (socket.timeout, socket.error, OSError):
            continue

    # No port responded — return best guess
    return {
        "smtp_host": smtp_host,
        "smtp_port": 587,
        "tls_mode": "starttls",
        "mx_host": mx_host,
        "guessed": True,
    }


def get_preset(provider_type: str) -> dict | None:
    return PROVIDER_PRESETS.get(provider_type)


def get_provider_note(provider_type: str, lang: str = "en") -> str:
    preset = PROVIDER_PRESETS.get(provider_type, {})
    return preset.get(f"notes_{lang}", preset.get("notes_en", ""))