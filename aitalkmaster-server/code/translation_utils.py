from enum import Enum

class Language(Enum):
    """Enumeration of supported languages"""
    ENGLISH = "English"
    SPANISH = "Spanish"
    FRENCH = "French"
    GERMAN = "German"
    ITALIAN = "Italian"
    PORTUGUESE = "Portuguese"
    RUSSIAN = "Russian"
    CHINESE = "Chinese"
    JAPANESE = "Japanese"
    KOREAN = "Korean"
    ARABIC = "Arabic"
    DUTCH = "Dutch"
    POLISH = "Polish"
    TURKISH = "Turkish"
    GREEK = "Greek"
    SWEDISH = "Swedish"
    NORWEGIAN = "Norwegian"
    DANISH = "Danish"
    FINNISH = "Finnish"
    CZECH = "Czech"
    HUNGARIAN = "Hungarian"
    ROMANIAN = "Romanian"
    HINDI = "Hindi"
    THAI = "Thai"
    VIETNAMESE = "Vietnamese"

# Language mapping: English language name (key) to list of possible input values (aliases)
LANGUAGE_MAP = {
    Language.ENGLISH: ["english", "en"],
    Language.SPANISH: ["spanish", "es", "español"],
    Language.FRENCH: ["french", "fr", "français"],
    Language.GERMAN: ["german", "de", "deutsch"],
    Language.ITALIAN: ["italian", "it", "italiano"],
    Language.PORTUGUESE: ["portuguese", "pt", "português"],
    Language.RUSSIAN: ["russian", "ru", "русский"],
    Language.CHINESE: ["chinese", "zh", "中文"],
    Language.JAPANESE: ["japanese", "ja", "日本語"],
    Language.KOREAN: ["korean", "ko", "한국어"],
    Language.ARABIC: ["arabic", "ar", "العربية"],
    Language.DUTCH: ["dutch", "nl", "nederlands"],
    Language.POLISH: ["polish", "pl", "polski"],
    Language.TURKISH: ["turkish", "tr", "türkçe"],
    Language.GREEK: ["greek", "el", "ελληνικά"],
    Language.SWEDISH: ["swedish", "sv", "svenska"],
    Language.NORWEGIAN: ["norwegian", "no", "norsk"],
    Language.DANISH: ["danish", "da", "dansk"],
    Language.FINNISH: ["finnish", "fi", "suomi"],
    Language.CZECH: ["czech", "cs", "čeština"],
    Language.HUNGARIAN: ["hungarian", "hu", "magyar"],
    Language.ROMANIAN: ["romanian", "ro", "română"],
    Language.HINDI: ["hindi", "hi", "हिन्दी"],
    Language.THAI: ["thai", "th", "ไทย"],
    Language.VIETNAMESE: ["vietnamese", "vi", "tiếng việt"],
}

# Mapping from English language name to native language name
NATIVE_NAME_MAP = {
    Language.ENGLISH: "English",
    Language.SPANISH: "español",
    Language.FRENCH: "français",
    Language.GERMAN: "Deutsch",
    Language.ITALIAN: "italiano",
    Language.PORTUGUESE: "português",
    Language.RUSSIAN: "русский",
    Language.CHINESE: "中文",
    Language.JAPANESE: "日本語",
    Language.KOREAN: "한국어",
    Language.ARABIC: "العربية",
    Language.DUTCH: "Nederlands",
    Language.POLISH: "polski",
    Language.TURKISH: "Türkçe",
    Language.GREEK: "ελληνικά",
    Language.SWEDISH: "svenska",
    Language.NORWEGIAN: "norsk",
    Language.DANISH: "dansk",
    Language.FINNISH: "suomi",
    Language.CZECH: "čeština",
    Language.HUNGARIAN: "magyar",
    Language.ROMANIAN: "română",
    Language.HINDI: "हिन्दी",
    Language.THAI: "ไทย",
    Language.VIETNAMESE: "Tiếng Việt",
}

FALLBACK_AUDIO_INSTRUCTIONS = "Speak naturally in {language}. Use proper pronunciation and intonation for {language}."

# Language-specific audio instructions
AUDIO_INSTRUCTIONS = {
    Language.ENGLISH: "Speak naturally in English. Use proper pronunciation and intonation for English.",
    Language.SPANISH: "Habla de forma natural en español. Usa la pronunciación y entonación adecuadas para el español.",
    Language.FRENCH: "Parlez naturellement en français. Utilisez une prononciation et une intonation appropriées pour le français.",
    Language.GERMAN: "Sprechen Sie natürlich auf Deutsch. Verwenden Sie die richtige Aussprache und Intonation für Deutsch.",
    Language.ITALIAN: "Parla naturalmente in italiano. Usa la pronuncia e l'intonazione appropriate per l'italiano.",
    Language.PORTUGUESE: "Fale naturalmente em português. Use a pronúncia e entonação adequadas para o português.",
    Language.RUSSIAN: "Говорите естественно по-русски. Используйте правильное произношение и интонацию для русского языка.",
    Language.CHINESE: "用中文自然地说话。使用正确的中文发音和语调。",
    Language.JAPANESE: "日本語で自然に話してください。日本語の適切な発音とイントネーションを使用してください。",
    Language.KOREAN: "한국어로 자연스럽게 말하세요. 한국어의 적절한 발음과 억양을 사용하세요.",
    Language.ARABIC: "تحدث بشكل طبيعي بالعربية. استخدم النطق والتنغيم المناسبين للعربية.",
    Language.DUTCH: "Spreek natuurlijk in het Nederlands. Gebruik de juiste uitspraak en intonatie voor het Nederlands.",
    Language.POLISH: "Mów naturalnie po polsku. Używaj odpowiedniej wymowy i intonacji dla języka polskiego.",
    Language.TURKISH: "Türkçe'de doğal konuşun. Türkçe için uygun telaffuz ve tonlama kullanın.",
    Language.GREEK: "Μιλήστε φυσικά στα ελληνικά. Χρησιμοποιήστε τη σωστή προφορά και τονισμό για τα ελληνικά.",
    Language.SWEDISH: "Tala naturligt på svenska. Använd rätt uttal och intonation för svenska.",
    Language.NORWEGIAN: "Snakk naturlig på norsk. Bruk riktig uttale og intonasjon for norsk.",
    Language.DANISH: "Tal naturligt på dansk. Brug korrekt udtale og intonation for dansk.",
    Language.FINNISH: "Puhu luonnollisesti suomeksi. Käytä oikeaa ääntämistä ja intonaatiota suomen kielelle.",
    Language.CZECH: "Mluvte přirozeně česky. Používejte správnou výslovnost a intonaci pro češtinu.",
    Language.HUNGARIAN: "Beszéljen természetesen magyarul. Használja a megfelelő kiejtést és hangsúlyozást a magyarnak.",
    Language.ROMANIAN: "Vorbește natural în română. Folosește pronunția și intonația corespunzătoare pentru română.",
    Language.HINDI: "हिन्दी में स्वाभाविक रूप से बोलें। हिन्दी के लिए उचित उच्चारण और स्वर का उपयोग करें।",
    Language.THAI: "พูดอย่างเป็นธรรมชาติในภาษาไทย ใช้การออกเสียงและน้ำเสียงที่เหมาะสมสำหรับภาษาไทย",
    Language.VIETNAMESE: "Nói tự nhiên bằng tiếng Việt. Sử dụng cách phát âm và ngữ điệu phù hợp cho tiếng Việt."
}

FALLBACK_TRANSLATE_INSTRUCTIONS = "You are a professional translator. Translate the user's text accurately and naturally. Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else:"

# Language-specific translation instructions
TRANSLATION_INSTRUCTIONS = {
    Language.ENGLISH: "You are a professional translator. Translate the user's text accurately and naturally. Translate the following text from {source_language} to {target_language}. Only return the translated text, nothing else:",
    Language.SPANISH: "Eres un traductor profesional. Traduce el texto del usuario de forma precisa y natural. Traduce el siguiente texto de {source_language} a {target_language}. Solo devuelve el texto traducido, nada más:",
    Language.FRENCH: "Vous êtes un traducteur professionnel. Traduisez le texte de l'utilisateur avec précision et naturellement. Traduisez le texte suivant de {source_language} vers {target_language}. Ne renvoyez que le texte traduit, rien d'autre :",
    Language.GERMAN: "Sie sind ein professioneller Übersetzer. Übersetzen Sie den Text des Benutzers genau und natürlich. Übersetzen Sie den folgenden Text von {source_language} nach {target_language}. Geben Sie nur den übersetzten Text zurück, nichts anderes:",
    Language.ITALIAN: "Sei un traduttore professionista. Traduci il testo dell'utente in modo accurato e naturale. Traduci il seguente testo da {source_language} a {target_language}. Restituisci solo il testo tradotto, nient'altro:",
    Language.PORTUGUESE: "Você é um tradutor profissional. Traduza o texto do usuário com precisão e naturalidade. Traduza o seguinte texto de {source_language} para {target_language}. Retorne apenas o texto traduzido, nada mais:",
    Language.RUSSIAN: "Вы профессиональный переводчик. Переведите текст пользователя точно и естественно. Переведите следующий текст с {source_language} на {target_language}. Верните только переведенный текст, ничего больше:",
    Language.CHINESE: "您是一位专业翻译。准确自然地翻译用户的文本。将以下文本从 {source_language} 翻译为 {target_language}。只返回翻译后的文本，不要其他内容：",
    Language.JAPANESE: "あなたはプロの翻訳者です。ユーザーのテキストを正確かつ自然に翻訳してください。次のテキストを {source_language} から {target_language} に翻訳してください。翻訳されたテキストのみを返してください。それ以外は何も返さないでください：",
    Language.KOREAN: "당신은 전문 번역가입니다. 사용자의 텍스트를 정확하고 자연스럽게 번역하세요. 다음 텍스트를 {source_language}에서 {target_language}로 번역하세요. 번역된 텍스트만 반환하고 다른 것은 반환하지 마세요:",
    Language.ARABIC: "أنت مترجم محترف. ترجم نص المستخدم بدقة وبشكل طبيعي. ترجم النص التالي من {source_language} إلى {target_language}. أعد النص المترجم فقط، لا شيء آخر:",
    Language.DUTCH: "Je bent een professionele vertaler. Vertaal de tekst van de gebruiker nauwkeurig en natuurlijk. Vertaal de volgende tekst van {source_language} naar {target_language}. Geef alleen de vertaalde tekst terug, niets anders:",
    Language.POLISH: "Jesteś profesjonalnym tłumaczem. Przetłumacz tekst użytkownika dokładnie i naturalnie. Przetłumacz następujący tekst z {source_language} na {target_language}. Zwróć tylko przetłumaczony tekst, nic więcej:",
    Language.TURKISH: "Profesyonel bir çevirmensiniz. Kullanıcının metnini doğru ve doğal bir şekilde çevirin. Aşağıdaki metni {source_language} dilinden {target_language} diline çevirin. Sadece çevrilmiş metni döndürün, başka bir şey döndürmeyin:",
    Language.GREEK: "Είστε επαγγελματίας μεταφραστής. Μεταφράστε το κείμενο του χρήστη με ακρίβεια και φυσικότητα. Μεταφράστε το ακόλουθο κείμενο από {source_language} σε {target_language}. Επιστρέψτε μόνο το μεταφρασμένο κείμενο, τίποτα άλλο:",
    Language.SWEDISH: "Du är en professionell översättare. Översätt användarens text noggrant och naturligt. Översätt följande text från {source_language} till {target_language}. Returnera endast den översatta texten, inget annat:",
    Language.NORWEGIAN: "Du er en profesjonell oversetter. Oversett brukerens tekst nøyaktig og naturlig. Oversett følgende tekst fra {source_language} til {target_language}. Returner bare den oversatte teksten, ingenting annet:",
    Language.DANISH: "Du er en professionel oversætter. Oversæt brugerens tekst præcist og naturligt. Oversæt følgende tekst fra {source_language} til {target_language}. Returner kun den oversatte tekst, intet andet:",
    Language.FINNISH: "Olet ammattimainen kääntäjä. Käännä käyttäjän teksti tarkasti ja luonnollisesti. Käännä seuraava teksti kielestä {source_language} kieleen {target_language}. Palauta vain käännetty teksti, ei mitään muuta:",
    Language.CZECH: "Jste profesionální překladatel. Přeložte text uživatele přesně a přirozeně. Přeložte následující text z {source_language} do {target_language}. Vraťte pouze přeložený text, nic jiného:",
    Language.HUNGARIAN: "Ön egy professzionális fordító. Fordítsa le a felhasználó szövegét pontosan és természetesen. Fordítsa le a következő szöveget {source_language} nyelvről {target_language} nyelvre. Csak a lefordított szöveget adja vissza, semmi mást:",
    Language.ROMANIAN: "Ești un traducător profesionist. Tradu textul utilizatorului cu precizie și natural. Tradu următorul text din {source_language} în {target_language}. Returnează doar textul tradus, nimic altceva:",
    Language.HINDI: "आप एक पेशेवर अनुवादक हैं। उपयोगकर्ता के पाठ को सटीक और स्वाभाविक रूप से अनुवाद करें। निम्नलिखित पाठ को {source_language} से {target_language} में अनुवाद करें। केवल अनुवादित पाठ लौटाएं, और कुछ नहीं:",
    Language.THAI: "คุณเป็นนักแปลมืออาชีพ แปลข้อความของผู้ใช้อย่างถูกต้องและเป็นธรรมชาติ แปลข้อความต่อไปนี้จาก {source_language} เป็น {target_language} ส่งคืนเฉพาะข้อความที่แปลแล้ว ไม่มีอะไรอื่น:",
    Language.VIETNAMESE: "Bạn là một dịch giả chuyên nghiệp. Dịch văn bản của người dùng một cách chính xác và tự nhiên. Dịch văn bản sau từ {source_language} sang {target_language}. Chỉ trả về văn bản đã dịch, không có gì khác:",
}

def _normalize_language(language: str) -> str:
    """Normalize language string to lowercase for mapping lookup"""
    if not language:
        return ""
    return language.strip().lower()

def _get_language_name(language: str) -> str:
    """Get the English language name from the language mapping, or return the original if not found"""
    if not language or language.strip() == "":
        return ""
    
    normalized = _normalize_language(language)
    
    # Search through LANGUAGE_MAP to find which language this input belongs to
    for language_enum, aliases in LANGUAGE_MAP.items():
        if normalized in [_normalize_language(alias) for alias in aliases]:
            return language_enum.value
    
    # If not found, return the original (normalized)
    return language.strip()

def _get_native_language_name(english_name: str) -> str:
    """Get the native language name from the English name"""
    if not english_name or english_name.strip() == "":
        return ""
    
    # Try to find the enum value that matches the english_name
    for language_enum in Language:
        if language_enum.value == english_name:
            return NATIVE_NAME_MAP.get(language_enum, english_name)
    
    return english_name

def build_audio_instructions(language: str) -> str:
    """Build audio generation instructions for the specified language"""
    if not language or language.strip() == "":
        return ""
    
    # Get the English language name, then find the corresponding enum
    english_name = _get_language_name(language)
    native_name = _get_native_language_name(english_name)
    
    # Find the enum for the language
    language_enum = None
    for lang_enum in Language:
        if lang_enum.value == english_name:
            language_enum = lang_enum
            break
    
    # Try to get language-specific instructions using enum
    if language_enum and language_enum in AUDIO_INSTRUCTIONS:
        return AUDIO_INSTRUCTIONS[language_enum]
    
    # Fallback to English instructions with the native language name
    return FALLBACK_AUDIO_INSTRUCTIONS.format(language=native_name)

def build_translation_instructions(source_language: str, target_language: str) -> str:
    """Build translation instructions for the specified languages"""
    if not source_language or source_language.strip() == "":
        return ""
    if not target_language or target_language.strip() == "":
        return ""
    
    # Get the English language names, then the native names
    source_english = _get_language_name(source_language)
    target_english = _get_language_name(target_language)
    source_native = _get_native_language_name(source_english)
    target_native = _get_native_language_name(target_english)
    
    # Find the enum for the target language
    target_enum = None
    for lang_enum in Language:
        if lang_enum.value == target_english:
            target_enum = lang_enum
            break
    
    # Try to get language-specific instructions in the target language using enum
    if target_enum and target_enum in TRANSLATION_INSTRUCTIONS:
        template = TRANSLATION_INSTRUCTIONS[target_enum]
        return template.format(source_language=source_native, target_language=target_native)
    
    # Fallback to English instructions
    return FALLBACK_TRANSLATE_INSTRUCTIONS.format(source_language=source_native, target_language=target_native)