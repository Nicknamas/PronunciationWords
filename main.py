from gtts import gTTS
import pygame
import io
import time
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import pickle
import hashlib

class AudioCache:
    """Класс для кэширования аудио данных между запусками программы"""
    
    def __init__(self, cache_file='audio_cache.pkl'):
        self.cache_file = cache_file
        self.cache = self.load_cache()
    
    def get_cache_key(self, word, language='ru', slow=False):
        """Создает уникальный ключ для кэширования"""
        content = f"{word}_{language}_{slow}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def load_cache(self):
        """Загружает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                print(f"✅ Загружен кэш: {len(cache)} записей")
                return cache
            else:
                print("✅ Кэш не найден, создается новый")
                return {}
        except Exception as e:
            print(f"❌ Ошибка загрузки кэша: {e}, создается новый кэш")
            return {}
    
    def save_cache(self):
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            print(f"💾 Кэш сохранен: {len(self.cache)} записей")
        except Exception as e:
            print(f"❌ Ошибка сохранения кэша: {e}")
    
    def get(self, word, language='ru', slow=False):
        """Получает аудио из кэша"""
        key = self.get_cache_key(word, language, slow)
        if key in self.cache:
            # Создаем новый BytesIO из кэшированных данных
            cached_data = self.cache[key]
            audio_buffer = io.BytesIO()
            audio_buffer.write(cached_data)
            audio_buffer.seek(0)
            return audio_buffer
        return None
    
    def put(self, word, audio_buffer, language='ru', slow=False):
        """Добавляет аудио в кэш"""
        try:
            key = self.get_cache_key(word, language, slow)
            # Сохраняем сырые данные вместо BytesIO объекта
            audio_data = audio_buffer.getvalue()
            self.cache[key] = audio_data
        except Exception as e:
            print(f"❌ Ошибка добавления в кэш: {e}")

def read_words_from_file(filename):
    """Читает слова из файла и возвращает список"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            words = [line.strip() for line in file if line.strip()]
        return words
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл {filename} не найден!")
        return []
    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")
        return []

def generate_single_audio(word, language='ru', slow=False, cache=None):
    """Генерирует аудио для одного слова с использованием кэша"""
    # Проверяем кэш сначала
    if cache:
        cached_audio = cache.get(word, language, slow)
        if cached_audio:
            return cached_audio, word, True, True  # True - из кэша
    
    try:
        tts = gTTS(text=word, lang=language, slow=slow)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        # Сохраняем в кэш
        if cache:
            cache.put(word, audio_buffer, language, slow)
        
        return audio_buffer, word, True, False  # False - не из кэша
    except Exception as e:
        print(f"❌ Ошибка генерации для '{word}': {e}")
        return None, word, False, False

def generate_audio_parallel(words, language='ru', speed_factor=1.0, max_workers=5, cache=None):
    """Параллельная генерация аудио с кэшированием"""
    print(f"🔄 Параллельная генерация {len(words)} слов...")
    print(f"📊 Потоков: {max_workers}, скорость: {speed_factor}x")
    
    audio_data = [None] * len(words)
    slow_mode = speed_factor < 0.8
    cache_hits = 0
    total_words = len(words)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {
            executor.submit(generate_single_audio, word, language, slow_mode, cache): i 
            for i, word in enumerate(words)
        }
        
        completed = 0
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                audio_buffer, word, success, from_cache = future.result()
                if success:
                    audio_data[i] = audio_buffer
                    completed += 1
                    cache_status = "✓ КЭШ" if from_cache else "✓ ГЕНЕРАЦИЯ"
                    cache_hits += 1 if from_cache else 0
                    print(f"{cache_status}: {word} ({completed}/{total_words})")
                else:
                    print(f"✗ ОШИБКА: {word}")
            except Exception as e:
                print(f"✗ ИСКЛЮЧЕНИЕ: {words[i]} - {e}")
    
    print(f"📈 Статистика: {cache_hits} из кэша, {total_words - cache_hits} сгенерировано")
    return audio_data

def generate_audio_batch(words, language='ru', speed_factor=1.0, batch_size=3, cache=None):
    """Генерация аудио батчами с кэшированием"""
    print(f"🔄 Батч-генерация {len(words)} слов...")
    print(f"📦 Размер батча: {batch_size}, скорость: {speed_factor}x")
    
    audio_data = []
    slow_mode = speed_factor < 0.8
    total_batches = (len(words) + batch_size - 1) // batch_size
    cache_hits = 0
    
    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, len(words))
        batch_words = words[start_idx:end_idx]
        
        print(f"📦 Батч {batch_num + 1}/{total_batches}: {', '.join(batch_words)}")
        
        threads = []
        batch_results = [None] * len(batch_words)
        batch_cache_stats = [False] * len(batch_words)
        
        def generate_batch_word(idx, word):
            # Проверяем кэш
            if cache:
                cached_audio = cache.get(word, language, slow_mode)
                if cached_audio:
                    batch_results[idx] = cached_audio
                    batch_cache_stats[idx] = True
                    return
            
            # Генерируем новое аудио
            try:
                tts = gTTS(text=word, lang=language, slow=slow_mode)
                audio_buffer = io.BytesIO()
                tts.write_to_fp(audio_buffer)
                audio_buffer.seek(0)
                batch_results[idx] = audio_buffer
                
                # Сохраняем в кэш
                if cache:
                    cache.put(word, audio_buffer, language, slow_mode)
                    
            except Exception as e:
                print(f"❌ Ошибка генерации '{word}': {e}")
        
        # Запускаем потоки для батча
        for i, word in enumerate(batch_words):
            thread = threading.Thread(target=generate_batch_word, args=(i, word))
            threads.append(thread)
            thread.start()
        
        # Ждем завершения
        for thread in threads:
            thread.join()
        
        # Считаем попадания в кэш
        batch_cache_hits = sum(batch_cache_stats)
        cache_hits += batch_cache_hits
        print(f"   📊 Батч {batch_num + 1}: {batch_cache_hits}/{len(batch_words)} из кэша")
        
        audio_data.extend(batch_results)
    
    print(f"📈 Итог: {cache_hits} из кэша, {len(words) - cache_hits} сгенерировано")
    return audio_data

def play_words_optimized(audio_data, words, pause_duration=0.3, playback_speed=1.0):
    """Воспроизведение с настройками"""
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(3)
    
    print(f"🎵 Воспроизведение {len(words)} слов...")
    print(f"⏱️ Пауза: {pause_duration}с, скорость: {playback_speed}x")
    print("-" * 60)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        start_time = time.time()
        
        for i, (audio_buffer, word) in enumerate(zip(audio_data, words), 1):
            if audio_buffer is None:
                print(f"⏭️ Пропуск {i}/{len(words)}: {word}")
                continue
                
            print(f"{i}/{len(words)}: {word}")
            
            try:
                audio_buffer.seek(0)
                temp_filename = os.path.join(temp_dir, f"word_{i}.mp3")
                
                with open(temp_filename, 'wb') as f:
                    f.write(audio_buffer.getvalue())
                
                sound = pygame.mixer.Sound(temp_filename)
                channel = sound.play()
                
                while channel.get_busy():
                    pygame.time.wait(5)
                
                if i < len(words):
                    time.sleep(pause_duration)
                    
            except Exception as e:
                print(f"❌ Ошибка воспроизведения '{word}': {e}")
        
        total_time = time.time() - start_time
        print("-" * 60)
        print(f"✅ Воспроизведение завершено за {total_time:.1f} секунд")
        
    finally:
        # Очистка временных файлов
        try:
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        except:
            pass

def get_generation_mode():
    """Выбор режима генерации"""
    print("\n🎛️ ВЫБЕРИТЕ РЕЖИМ ГЕНЕРАЦИИ:")
    print("1. Параллельный (рекомендуется для большого количества слов)")
    print("2. Батчами (стабильность, контроль над процессом)")
    print("3. Автоматический выбор")
    
    while True:
        choice = input("Введите номер (1-3): ").strip()
        if choice in ['1', '2', '3']:
            return int(choice)
        print("❌ Пожалуйста, введите 1, 2 или 3")

def get_optimization_settings(word_count):
    """Настройки оптимизации"""
    if word_count <= 5:
        return 2, 2  # Мало слов - мало потоков/батчей
    elif word_count <= 15:
        return 4, 3  # Среднее количество
    else:
        return 6, 4  # Много слов

def main_optimized_with_cache():
    """Основная функция с кэшированием и выбором режима"""
    # Инициализируем кэш
    cache = AudioCache()
    
    filename = "listen.txt"
    
    if not os.path.exists(filename):
        print(f"❌ Файл {filename} не найден!")
        print("📝 Создайте файл listen.txt со словами (каждое слово на новой строке)")
        return
    
    words = read_words_from_file(filename)
    if not words:
        print("❌ Не удалось прочитать слова из файла")
        return
    
    print(f"📖 Загружено {len(words)} слов")
    print("📝 Слова:", ", ".join(words[:10]) + ("..." if len(words) > 10 else ""))
    
    # Настройки воспроизведения
    print("\n⚙️ НАСТРОЙКИ ВОСПРОИЗВЕДЕНИЯ:")
    
    pause_input = input("⏱️ Пауза между словами в секундах (по умолчанию 0.2): ").strip()
    pause_duration = float(pause_input) if pause_input else 0.2
    
    speed_input = input("🎯 Скорость произношения 0.5-2.0 (по умолчанию 1.2): ").strip()
    speed_factor = float(speed_input) if speed_input else 1.2
    
    # Выбор режима генерации
    generation_mode = get_generation_mode()
    
    # Генерация аудио
    gen_start = time.time()
    
    if generation_mode == 1:
        # Параллельный режим
        max_workers, _ = get_optimization_settings(len(words))
        audio_data = generate_audio_parallel(
            words, speed_factor=speed_factor, max_workers=max_workers, cache=cache
        )
    elif generation_mode == 2:
        # Батч-режим
        _, batch_size = get_optimization_settings(len(words))
        audio_data = generate_audio_batch(
            words, speed_factor=speed_factor, batch_size=batch_size, cache=cache
        )
    else:
        # Автоматический выбор
        max_workers, batch_size = get_optimization_settings(len(words))
        if len(words) > 10:
            print("🤖 Автоматически выбран параллельный режим")
            audio_data = generate_audio_parallel(
                words, speed_factor=speed_factor, max_workers=max_workers, cache=cache
            )
        else:
            print("🤖 Автоматически выбран батч-режим")
            audio_data = generate_audio_batch(
                words, speed_factor=speed_factor, batch_size=batch_size, cache=cache
            )
    
    gen_time = time.time() - gen_start
    print(f"⏱️ Генерация аудио завершена за {gen_time:.1f} секунд")
    
    # Сохраняем кэш
    cache.save_cache()
    
    # Воспроизведение
    try:
        play_words_optimized(audio_data, words, pause_duration, speed_factor)
    except KeyboardInterrupt:
        print("\n⏹️ Воспроизведение прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка при воспроизведении: {e}")
    finally:
        # Всегда сохраняем кэш при завершении
        cache.save_cache()

def clear_cache():
    """Очистка кэша"""
    cache_files = ['audio_cache.pkl']
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"🧹 Кэш {cache_file} очищен")

def show_cache_info():
    """Показывает информацию о кэше"""
    cache = AudioCache()
    print(f"📊 Размер кэша: {len(cache.cache)} записей")
    
    # Примеры слов в кэше (первые 5)
    sample_words = list(cache.cache.keys())[:5]
    print("📝 Примеры записей в кэше:", sample_words)

if __name__ == "__main__":
    print("🚀 УСКОРЕННОЕ АУДИО ВОСПРОИЗВЕДЕНИЕ С КЭШИРОВАНИЕМ")
    print("=" * 55)
    
    print("\n🎮 РЕЖИМЫ:")
    print("1 - Основной режим с кэшированием")
    print("2 - Быстрый запуск (пауза 0.1с, скорость 1.3x)")
    print("3 - Очистка кэша")
    print("4 - Информация о кэше")
    print("5 - Тест скорости генерации")
    
    choice = input("Выберите режим (1-5): ").strip()
    
    if choice == "2":
        # Быстрый запуск
        cache = AudioCache()
        words = read_words_from_file("listen.txt")
        if words:
            print(f"⚡ Быстрый запуск {len(words)} слов")
            audio_data = generate_audio_parallel(words, speed_factor=1.3, max_workers=4, cache=cache)
            play_words_optimized(audio_data, words, pause_duration=0.1, playback_speed=1.3)
            cache.save_cache()
    elif choice == "3":
        clear_cache()
    elif choice == "4":
        show_cache_info()
    elif choice == "5":
        # Тест скорости
        words = read_words_from_file("listen.txt")
        if words:
            cache = AudioCache()
            start = time.time()
            generate_audio_parallel(words, cache=cache)
            print(f"⏱️ Тест скорости: {time.time() - start:.1f}с")
            cache.save_cache()
    else:
        main_optimized_with_cache()
