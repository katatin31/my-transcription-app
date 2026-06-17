import pandas as pd
import streamlit as st
import re
import string
import pronouncing
import io
import os

# --- Словари и функции ---
ARPABET_TO_IPA = {
    'AO': 'ɔ', 'AO0': 'ɔ', 'AO1': 'ɔ', 'AO2': 'ɔ', 
    'AA': 'ɑ', 'AA0': 'ɑ', 'AA1': 'ɑ', 'AA2': 'ɑ',
    'IY': 'i', 'IY0': 'i', 'IY1': 'i', 'IY2': 'i', 
    'UW': 'u', 'UW0': 'u', 'UW1': 'u', 'UW2': 'u',
    'EH': 'e', 'EH0': 'e', 'EH1': 'e', 'EH2': 'e', 
    'IH': 'ɪ', 'IH0': 'ɪ', 'IH1': 'ɪ', 'IH2': 'ɪ', 
    'UH': 'ʊ', 'UH0': 'ʊ', 'UH1': 'ʊ', 'UH2': 'ʊ', 
    'AH': 'ʌ', 'AH0': 'ə', 'AH1': 'ʌ', 'AH2': 'ʌ', 
    'AE': 'æ', 'AE0': 'æ', 'AE1': 'æ', 'AE2': 'æ', 
    'AX': 'ə', 'AX0': 'ə', 'AX1': 'ə', 'AX2': 'ə',
    'EY': 'eɪ', 'EY0': 'eɪ', 'EY1': 'eɪ', 'EY2': 'eɪ', 
    'AY': 'aɪ', 'AY0': 'aɪ', 'AY1': 'aɪ', 'AY2': 'aɪ',
    'OW': 'oʊ', 'OW0': 'oʊ', 'OW1': 'oʊ', 'OW2': 'oʊ', 
    'AW': 'aʊ', 'AW0': 'aʊ', 'AW1': 'aʊ', 'AW2': 'aʊ', 
    'OY': 'ɔɪ', 'OY0': 'ɔɪ', 'OY1': 'ɔɪ', 'OY2': 'ɔɪ', 
    'P': 'p', 'B': 'b', 'T': 't', 'D': 'd', 
    'K': 'k', 'G': 'g', 'CH': 'tʃ', 'JH': 'dʒ', 
    'F': 'f', 'V': 'v', 'TH': 'θ', 'DH': 'ð', 
    'S': 's', 'Z': 'z', 'SH': 'ʃ', 'ZH': 'ʒ', 
    'HH': 'h', 'M': 'm', 'N': 'n', 'NG': 'ŋ', 
    'L': 'l', 'R': 'r', 'ER': 'ɜr', 'ER0': 'ɜr', 'ER1': 'ɜr', 'ER2': 'ɜr', 
    'AXR': 'ər', 'AXR0': 'ər', 'AXR1': 'ər', 'AXR2': 'ər', 
    'W': 'w', 'Y': 'j'
}

def remove_punctuation(word):
    cleaned = re.sub(r"’s|'s$", '', word, flags=re.IGNORECASE)
    cleaned = re.sub(r"[’']", '', cleaned)
    return cleaned.translate(str.maketrans('', '', string.punctuation))

def arpabet_to_ipa_str(arpabet_string):
    if not arpabet_string or arpabet_string == "не_найдено": return "не_найдено"
    ipa_chars = []
    for symbol in arpabet_string.replace('|', '').split():
        ipa = ARPABET_TO_IPA.get(symbol)
        if not ipa:
            symbol_clean = re.sub(r'\d', '', symbol)
            ipa = ARPABET_TO_IPA.get(symbol_clean, symbol)
        ipa_chars.append(ipa)
    return ''.join(ipa_chars)

def determine_possessive_suffix_arpabet(arpabet_transcription):
    last_sound = arpabet_transcription.split()[-1]
    if last_sound in ['P', 'T', 'K', 'F', 'TH']: return 'S'
    if last_sound in ['S', 'Z', 'CH', 'SH', 'JH']: return 'IH Z'
    return 'Z'

def process_single_word(word_str, dict_df):
    base_word = remove_punctuation(word_str).lower()
    if not base_word: return word_str
    arpabet = "не_найдено"
    
    if dict_df is not None:
        match = dict_df[dict_df['word'] == base_word]
        if not match.empty:
            arpabet_val = match.iloc[0]['transcription']
            if pd.notna(arpabet_val):
                arpabet = str(arpabet_val).strip('[]')
                
    if arpabet == "не_найдено" or arpabet.lower() == "nan":
        phones = pronouncing.phones_for_word(base_word)
        if phones: arpabet = phones[0]
            
    if word_str.lower().endswith(("’s", "'s")) and arpabet != "не_найдено":
        suffix = determine_possessive_suffix_arpabet(arpabet)
        arpabet += f" {suffix}"
        
    if arpabet != "не_найдено": return f"[{arpabet_to_ipa_str(arpabet)}]"
    return "[Not found]"

def process_text(text, dict_df):
    if pd.isna(text): return ""
    text_str = str(text).strip()
    parts = re.findall(r"[\w’']+|[^\w’']+", text_str)
    result = []
    for part in parts:
        if re.match(r"[\w’']+", part): result.append(process_single_word(part, dict_df))
        else: result.append(part)
    return "".join(result).strip()

# --- Фоновая загрузка словаря ---
@st.cache_data
def load_dictionary():
    file_path = 'words_with_translations.xlsx'
    if os.path.exists(file_path):
        try:
            df = pd.read_excel(file_path)
            df['word'] = df['word'].str.strip().str.lower()
            return df
        except Exception:
            return None
    return None

# --- Интерфейс приложения ---
st.title("Генератор транскрипций")

# Загружаем словарь невидимо для пользователя
dict_df = load_dictionary()

if dict_df is not None:
    st.success("✅ Внутренний словарь успешно подключен!")
else:
    st.warning("⚠️ Словарь words_with_translations.xlsx не найден. Транскрипция будет генерироваться на лету (может быть менее точно).")

st.write("Загрузите ваш Excel-файл для обработки:")

# Загрузка целевого файла
input_file = st.file_uploader("Выберите Excel-файл (.xlsx)", type=['xlsx'])

if input_file is not None:
    if st.button("Начать обработку"):
        with st.spinner("Обработка данных... Пожалуйста, подождите."):
            try:
                # Читаем основной файл
                df = pd.read_excel(input_file, header=None)
                
                # Обработка
                next_col_idx = len(df.columns)
                new_col_data = df.iloc[:, 0].apply(lambda w: process_text(w, dict_df))
                df.insert(next_col_idx, next_col_idx, new_col_data)
                
                # Сохраняем результат в память
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, header=False, index=False)
                processed_data = output.getvalue()
                
                # === Генерируем новое имя файла на основе исходного ===
                original_name = input_file.name
                base_name, ext = os.path.splitext(original_name)
                new_file_name = f"{base_name}_with_transcriptions{ext}"
                
                st.success("✨ Готово! Файл успешно обработан.")
                
                # Кнопка для скачивания с новым умным именем
                st.download_button(
                    label="📥 Скачать готовый файл",
                    data=processed_data,
                    file_name=new_file_name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Произошла ошибка: {e}")
