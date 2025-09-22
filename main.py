from gtts import gTTS
import pygame
import io
import time
import threading
from queue import Queue
import os

def read_words_from_file(filename):
    """Читает слова из файла и возвращает список"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            words = [line.strip() for line in file if line.strip()]
        return words
    except FileNotFoundError:
        print(f"Ошибка: Файл {filename} не найден!")
        return []
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        return []

def generate_audio_in_memory(words, language='ru'):
    """Генерирует аудио для всех слов в памяти"""
    audio_data = []
    
    print("Генерация аудио...")
    for i, word in enumerate(words, 1):
        print(f"Генерация {i}/{len(words)}: {word}")
        try:
            # Генерируем аудио в память (без сохранения в файл)
            tts = gTTS(text=word, lang=language, slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)  # Перемещаемся в начало буфера
            audio_data.append(audio_buffer)
        except Exception as e:
            print(f"Ошибка генерации для '{word}': {e}")
            audio_data.append(None)
    
    return audio_data

def play_audio_sequentially(audio_data, words):
    """Воспроизводит предварительно сгенерированные аудиофайлы"""
    pygame.mixer.init()
    pygame.mixer.set_num_channels(2)  # Два канала для плавного перехода
    
    print(f"Начинаю воспроизведение {len(words)} слов...")
    print("-" * 40)
    
    for i, (audio_buffer, word) in enumerate(zip(audio_data, words), 1):
        if audio_buffer is None:
            print(f"Пропуск {i}/{len(words)}: {word} (ошибка генерации)")
            continue
            
        print(f"{i}/{len(words)}: {word}")
        
        try:
            # Воспроизводим аудио из памяти
            audio_buffer.seek(0)  # Важно: возвращаемся в начало буфера
            temp_filename = f"temp_{i}.mp3"
            
            # Сохраняем временно для воспроизведения
            with open(temp_filename, 'wb') as f:
                f.write(audio_buffer.getvalue())
            
            # Загружаем и воспроизводим
            sound = pygame.mixer.Sound(temp_filename)
            channel = sound.play()
            
            # Ждем завершения воспроизведения
            while channel.get_busy():
                pygame.time.wait(1)  # Короткая пауза
            
            # Удаляем временный файл
            os.remove(temp_filename)
            
        except Exception as e:
            print(f"Ошибка воспроизведения '{word}': {e}")
    
    print("-" * 40)
    print("Воспроизведение завершено!")

def main_fast():
    """Основная функция с быстрым воспроизведением"""
    filename = "listen.txt"
    
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден!")
        return
    
    words = read_words_from_file(filename)
    if not words:
        print("Не удалось прочитать слова из файла.")
        return
    
    print(f"Прочитано {len(words)} слов")
    
    # Генерируем все аудио заранее
    audio_data = generate_audio_in_memory(words, 'ru')
    
    # Воспроизводим без задержек
    play_audio_sequentially(audio_data, words)

if __name__ == "__main__":
    main_fast()
