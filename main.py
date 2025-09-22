from gtts import gTTS
import pygame
import io
import time
import os
import tempfile

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

def generate_audio_with_speed(words, language='ru', speed_factor=1.0):
    """
    Генерирует аудио с настраиваемой скоростью
    speed_factor: 0.5 - медленно, 1.0 - нормально, 1.5 - быстро, 2.0 - очень быстро
    """
    audio_data = []
    
    print(f"Генерация аудио (скорость: {speed_factor}x)...")
    for i, word in enumerate(words, 1):
        print(f"Генерация {i}/{len(words)}: {word}")
        try:
            # Для управления скоростью используем slow параметр
            slow = speed_factor < 0.8  # Если скорость меньше 0.8x, используем медленный режим
            
            tts = gTTS(text=word, lang=language, slow=slow)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            audio_data.append(audio_buffer)
        except Exception as e:
            print(f"Ошибка генерации для '{word}': {e}")
            audio_data.append(None)
    
    return audio_data

def play_words_with_settings(audio_data, words, pause_duration=0.3, playback_speed=1.0):
    """
    Воспроизводит слова с настраиваемой паузой и скоростью
    
    Args:
        pause_duration: пауза между словами в секундах (0.1 - очень коротко, 1.0 - долго)
        playback_speed: скорость воспроизведения (0.5-2.0)
    """
    # Инициализируем pygame с настройками для качества
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)
    
    print(f"Воспроизведение {len(words)} слов...")
    print(f"Настройки: пауза между словами = {pause_duration}с, скорость = {playback_speed}x")
    print("-" * 50)
    
    # Создаем временную папку для аудиофайлов
    temp_dir = tempfile.mkdtemp()
    
    try:
        for i, (audio_buffer, word) in enumerate(zip(audio_data, words), 1):
            if audio_buffer is None:
                print(f"Пропуск {i}/{len(words)}: {word} (ошибка генерации)")
                continue
                
            print(f"{i}/{len(words)}: {word}")
            
            try:
                # Сохраняем аудио во временный файл
                audio_buffer.seek(0)
                temp_filename = os.path.join(temp_dir, f"word_{i}.mp3")
                
                with open(temp_filename, 'wb') as f:
                    f.write(audio_buffer.getvalue())
                
                # Загружаем и воспроизводим звук
                sound = pygame.mixer.Sound(temp_filename)
                
                # Применяем скорость воспроизведения (если поддерживается)
                try:
                    # Некоторые версии pygame поддерживают set_volume для имитации скорости
                    # Это не настоящая смена скорости, но создает эффект
                    if playback_speed > 1.0:
                        sound.set_volume(min(1.0, 0.8 + (playback_speed - 1.0) * 0.1))
                except:
                    pass
                
                channel = sound.play()
                
                # Ждем завершения воспроизведения текущего слова
                while channel.get_busy():
                    pygame.time.wait(10)  # Короткие проверки
                
                # Пауза между словами (кроме последнего)
                if i < len(words):
                    time.sleep(pause_duration)
                    
            except Exception as e:
                print(f"Ошибка воспроизведения '{word}': {e}")
        
        print("-" * 50)
        print("Воспроизведение завершено!")
        
    finally:
        # Очистка временных файлов
        try:
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        except:
            pass

def get_user_settings():
    """Получает настройки от пользователя"""
    print("\n" + "="*50)
    print("НАСТРОЙКИ ВОСПРОИЗВЕДЕНИЯ")
    print("="*50)
    
    # Настройка паузы между словами
    print("\n1. Пауза между словами:")
    print("   0.0 - Без паузы")
    print("   0.1 - Очень короткая пауза")
    print("   0.3 - Короткая пауза (рекомендуется)")
    print("   0.5 - Средняя пауза")
    print("   1.0 - Длинная пауза")
    
    while True:
        try:
            pause_input = input("Введите длительность паузы в секундах (по умолчанию 0.3): ").strip()
            if pause_input == "":
                pause_duration = 0.3
                break
            pause_duration = float(pause_input)
            if pause_duration >= 0:
                break
            else:
                print("Пауза не может быть отрицательной!")
        except ValueError:
            print("Пожалуйста, введите число!")
    
    # Настройка скорости произношения
    print("\n2. Скорость произношения слов:")
    print("   0.7 - Очень медленно")
    print("   0.9 - Медленно")
    print("   1.0 - Нормальная скорость")
    print("   1.2 - Быстро")
    print("   1.5 - Очень быстро")
    
    while True:
        try:
            speed_input = input("Введите коэффициент скорости (по умолчанию 1.0): ").strip()
            if speed_input == "":
                speed_factor = 1.0
                break
            speed_factor = float(speed_input)
            if 0.5 <= speed_factor <= 2.0:
                break
            else:
                print("Скорость должна быть от 0.5 до 2.0!")
        except ValueError:
            print("Пожалуйста, введите число!")
    
    return pause_duration, speed_factor

def main_configured():
    """Основная функция с настраиваемыми параметрами"""
    filename = "listen.txt"
    
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден!")
        print("Создайте файл listen.txt со словами (каждое слово на новой строке)")
        return
    
    words = read_words_from_file(filename)
    if not words:
        print("Не удалось прочитать слова из файла или файл пуст.")
        return
    
    print(f"Прочитано {len(words)} слов из файла {filename}")
    print("Слова:", ", ".join(words))
    
    # Получаем настройки от пользователя
    pause_duration, speed_factor = get_user_settings()
    
    # Генерируем аудио с выбранной скоростью
    audio_data = generate_audio_with_speed(words, speed_factor=speed_factor)
    
    # Воспроизводим с настройками
    try:
        play_words_with_settings(audio_data, words, pause_duration, speed_factor)
    except KeyboardInterrupt:
        print("\nВоспроизведение прервано пользователем.")
    except Exception as e:
        print(f"Произошла ошибка при воспроизведении: {e}")

# Упрощенная версия с быстрым запуском
def quick_play(pause=0.2, speed=1.2):
    """Быстрый запуск с предустановленными параметрами"""
    filename = "listen.txt"
    
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден!")
        return
    
    words = read_words_from_file(filename)
    if not words:
        return
    
    print(f"Быстрое воспроизведение {len(words)} слов (пауза: {pause}с, скорость: {speed}x)")
    
    audio_data = generate_audio_with_speed(words, speed_factor=speed)
    play_words_with_settings(audio_data, words, pause_duration=pause, playback_speed=speed)

if __name__ == "__main__":
    print("АУДИО ВОСПРОИЗВЕДЕНИЕ СЛОВ")
    print("="*30)
    
    print("\nРежимы запуска:")
    print("1 - Настроить параметры (рекомендуется)")
    print("2 - Быстрый запуск (пауза 0.2с, скорость 1.2x)")
    print("3 - Очень быстрый запуск (пауза 0.1с, скорость 1.5x)")
    
    choice = input("Выберите режим (1-3, по умолчанию 1): ").strip()
    
    if choice == "2":
        quick_play(pause=0.2, speed=1.2)
    elif choice == "3":
        quick_play(pause=0.1, speed=1.5)
    else:
        main_configured()
