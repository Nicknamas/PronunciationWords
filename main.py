from gtts import gTTS
import pygame
import time
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

def speak_words_gtts(words, delay=2.0, language='ru'):
    """Произносит слова используя gTTS"""
    if not words:
        print("Нет слов для воспроизведения!")
        return
    
    pygame.mixer.init()
    
    print(f"Начинаю воспроизведение {len(words)} слов...")
    print("-" * 40)
    
    for i, word in enumerate(words, 1):
        print(f"{i}/{len(words)}: {word}")
        
        try:
            # Создаем аудио файл
            tts = gTTS(text=word, lang=language, slow=False)
            temp_file = "temp_audio.mp3"
            tts.save(temp_file)
            
            # Воспроизводим аудио
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # Ждем завершения воспроизведения
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            # Удаляем временный файл
            os.remove(temp_file)
            
            # Пауза между словами (кроме последнего)
            if i < len(words):
                time.sleep(delay)
                
        except Exception as e:
            print(f"Ошибка при воспроизведении слова '{word}': {e}")
    
    print("-" * 40)
    print("Воспроизведение завершено!")
    pygame.mixer.quit()

def main_gtts():
    """Основная функция программы с gTTS"""
    filename = "listen.txt"
    
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден!")
        return
    
    words = read_words_from_file(filename)
    if not words:
        print("Не удалось прочитать слова из файла.")
        return
    
    print(f"Прочитано {len(words)} слов:")
    for word in words:
        print(f"  - {word}")
    print()
    
    try:
        speak_words_gtts(words, delay=0.0, language='ru')
    except KeyboardInterrupt:
        print("\nВоспроизведение прервано пользователем.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")

# Для использования gTTS версии раскомментируйте следующую строку:
if __name__ == "__main__": main_gtts()
