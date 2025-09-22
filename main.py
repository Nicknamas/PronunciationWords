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
import random  # Добавляем импорт random

class SettingsManager:
    """Класс для управления настройками программы"""
    
    def __init__(self, settings_file='tts_settings.json'):
        self.settings_file = settings_file
        self.default_settings = {
            'pause_duration': 0.3,
            'speed_factor': 1.2,
            'language': 'ru',
            'generation_mode': 1,  # 1-параллельный, 2-батчи, 3-авто
            'max_workers': 4,
            'batch_size': 3,
            'random_order': True  # Добавляем настройку случайного порядка
        }
        self.settings = self.load_settings()
    
    def load_settings(self):
        """Загружает настройки из файла"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                
                # Объединяем с настройками по умолчанию
                settings = {**self.default_settings, **saved_settings}
                print(f"✅ Загружены сохраненные настройки")
                return settings
            else:
                print("✅ Используются настройки по умолчанию")
                return self.default_settings.copy()
        except Exception as e:
            print(f"❌ Ошибка загрузки настроек: {e}, используем по умолчанию")
            return self.default_settings.copy()
    
    def save_settings(self):
        """Сохраняет настройки в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            print("💾 Настройки сохранены!")
        except Exception as e:
            print(f"❌ Ошибка сохранения настроек: {e}")
    
    def get(self, key):
        """Получает значение настройки"""
        return self.settings.get(key, self.default_settings.get(key))
    
    def set(self, key, value):
        """Устанавливает значение настройки"""
        self.settings[key] = value
    
    def print_current_settings(self):
        """Показывает текущие настройки"""
        print("\n📊 ТЕКУЩИЕ НАСТРОЙКИ:")
        print(f"   ⏱️ Пауза между словами: {self.settings['pause_duration']}с")
        print(f"   🎯 Скорость произношения: {self.settings['speed_factor']}x")
        print(f"   🌐 Язык: {self.settings['language']}")
        print(f"   🔧 Режим генерации: {self.get_mode_name()}")
        print(f"   🎲 Случайный порядок: {'ВКЛ' if self.settings['random_order'] else 'ВЫКЛ'}")
        
        if self.settings['generation_mode'] == 1:
            print(f"   🚀 Потоков: {self.settings['max_workers']}")
        elif self.settings['generation_mode'] == 2:
            print(f"   📦 Размер батча: {self.settings['batch_size']}")
    
    def get_mode_name(self):
        """Возвращает название режима генерации"""
        modes = {
            1: "Параллельный",
            2: "Батчами", 
            3: "Автоматический"
        }
        return modes.get(self.settings['generation_mode'], "Неизвестно")

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

def play_words_optimized(audio_data, words, pause_duration=0.3, playback_speed=1.0, random_order=True):
    """Воспроизведение с настройками"""
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    pygame.mixer.set_num_channels(3)
    
    print(f"🎵 Воспроизведение {len(words)} слов...")
    print(f"⏱️ Пауза: {pause_duration}с, скорость: {playback_speed}x")
    print(f"🎲 Случайный порядок: {'ВКЛ' if random_order else 'ВЫКЛ'}")
    print("-" * 60)
    
    # Создаем список индексов для воспроизведения
    if random_order:
        # Случайный порядок: перемешиваем индексы
        playback_indices = list(range(len(words)))
        random.shuffle(playback_indices)
        print("🔀 Слова будут воспроизведены в случайном порядке")
    else:
        # Обычный порядок
        playback_indices = list(range(len(words)))
        print("➡️ Слова будут воспроизведены в обычном порядке")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        start_time = time.time()
        
        for play_index, original_index in enumerate(playback_indices, 1):
            word = words[original_index]
            audio_buffer = audio_data[original_index]
            
            if audio_buffer is None:
                print(f"⏭️ Пропуск {play_index}/{len(words)}: {word}")
                continue
                
            print(f"{play_index}/{len(words)}: {word}")
            
            try:
                audio_buffer.seek(0)
                temp_filename = os.path.join(temp_dir, f"word_{original_index}.mp3")
                
                with open(temp_filename, 'wb') as f:
                    f.write(audio_buffer.getvalue())
                
                sound = pygame.mixer.Sound(temp_filename)
                channel = sound.play()
                
                while channel.get_busy():
                    pygame.time.wait(5)
                
                if play_index < len(words):
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

def get_user_settings(settings_manager):
    """Получает настройки от пользователя с возможностью использовать сохраненные"""
    settings_manager.print_current_settings()
    
    print("\n⚙️ НАСТРОЙКИ ВОСПРОИЗВЕДЕНИЯ:")
    print("1 - Использовать сохраненные настройки")
    print("2 - Ввести новые настройки")
    print("3 - Использовать сохраненные, но изменить паузу/скорость/порядок")
    
    choice = input("Выберите вариант (1-3): ").strip()
    
    if choice == "1":
        # Используем сохраненные настройки без изменений
        print("✅ Используются сохраненные настройки")
        return
    
    # Запрос новых настроек
    if choice == "3":
        print("📝 Изменение паузы, скорости и порядка:")
    
    if choice != "3":
        # Настройка паузы
        print("\n⏱️ Пауза между словами:")
        print("   0.0 - Без паузы")
        print("   0.1 - Очень короткая")
        print("   0.3 - Короткая (рекомендуется)")
        print("   0.5 - Средняя")
        print("   1.0 - Длинная")
    
    pause_input = input(f"Пауза в секундах [текущая: {settings_manager.get('pause_duration')}]: ").strip()
    if pause_input:
        settings_manager.set('pause_duration', float(pause_input))
    
    if choice != "3":
        # Настройка скорости
        print("\n🎯 Скорость произношения:")
        print("   0.7 - Очень медленно")
        print("   0.9 - Медленно")
        print("   1.0 - Нормальная")
        print("   1.2 - Быстро (рекомендуется)")
        print("   1.5 - Очень быстро")
    
    speed_input = input(f"Скорость 0.5-2.0 [текущая: {settings_manager.get('speed_factor')}]: ").strip()
    if speed_input:
        speed = float(speed_input)
        if 0.5 <= speed <= 2.0:
            settings_manager.set('speed_factor', speed)
        else:
            print("❌ Скорость должна быть от 0.5 до 2.0, используется значение по умолчанию")
    
    # Настройка случайного порядка
    print("\n🎲 Порядок воспроизведения:")
    print("   1 - Случайный порядок (рекомендуется для обучения)")
    print("   2 - Обычный порядок (как в файле)")
    
    order_input = input(f"Порядок [текущий: {'1' if settings_manager.get('random_order') else '2'}]: ").strip()
    if order_input:
        settings_manager.set('random_order', order_input == "1")
    
    if choice != "3":
        # Выбор режима генерации
        print("\n🎛️ РЕЖИМ ГЕНЕРАЦИИ:")
        print("1 - Параллельный (скорость)")
        print("2 - Батчами (стабильность)")
        print("3 - Автоматический")
        
        mode_input = input(f"Режим [текущий: {settings_manager.get('generation_mode')}]: ").strip()
        if mode_input:
            settings_manager.set('generation_mode', int(mode_input))
        
        # Дополнительные настройки в зависимости от режима
        if settings_manager.get('generation_mode') == 1:
            workers_input = input(f"Количество потоков [текущее: {settings_manager.get('max_workers')}]: ").strip()
            if workers_input:
                settings_manager.set('max_workers', int(workers_input))
        elif settings_manager.get('generation_mode') == 2:
            batch_input = input(f"Размер батча [текущий: {settings_manager.get('batch_size')}]: ").strip()
            if batch_input:
                settings_manager.set('batch_size', int(batch_input))

def get_optimization_settings(word_count, settings_manager):
    """Настройки оптимизации с учетом сохраненных значений"""
    if word_count <= 5:
        return settings_manager.get('max_workers'), settings_manager.get('batch_size')
    elif word_count <= 15:
        return min(4, settings_manager.get('max_workers')), min(3, settings_manager.get('batch_size'))
    else:
        return settings_manager.get('max_workers'), settings_manager.get('batch_size')

def main_optimized_with_cache_and_settings():
    """Основная функция с кэшированием и настройками"""
    # Инициализируем менеджеры
    settings_manager = SettingsManager()
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
    
    # Получаем настройки от пользователя
    get_user_settings(settings_manager)
    
    # Показываем финальные настройки
    settings_manager.print_current_settings()
    
    # Генерация аудио
    gen_start = time.time()
    
    generation_mode = settings_manager.get('generation_mode')
    speed_factor = settings_manager.get('speed_factor')
    language = settings_manager.get('language')

    if generation_mode == 1:
        # Параллельный режим
        max_workers, _ = get_optimization_settings(len(words), settings_manager)
        audio_data = generate_audio_parallel(
            words, 
            speed_factor=speed_factor, 
            max_workers=max_workers, 
            language=language,
            cache=cache
        )
    elif generation_mode == 2:
        # Батч-режим
        _, batch_size = get_optimization_settings(len(words), settings_manager)
        audio_data = generate_audio_batch(
            words, 
            speed_factor=speed_factor, 
            batch_size=batch_size, 
            language=language,
            cache=cache
        )
    else:
        # Автоматический выбор
        max_workers, batch_size = get_optimization_settings(len(words), settings_manager)
        if len(words) > 10:
            print("🤖 Автоматически выбран параллельный режим")
            audio_data = generate_audio_parallel(
                words, 
                speed_factor=speed_factor, 
                max_workers=max_workers, 
                language=language,
                cache=cache
            )
        else:
            print("🤖 Автоматически выбран батч-режим")
            audio_data = generate_audio_batch(
                words, 
                speed_factor=speed_factor, 
                language=language,
                batch_size=batch_size, 
                cache=cache
            )
    
    gen_time = time.time() - gen_start
    print(f"⏱️ Генерация аудио завершена за {gen_time:.1f} секунд")
    
    # Сохраняем настройки и кэш
    settings_manager.save_settings()
    cache.save_cache()
    
    # Воспроизведение
    try:
        play_words_optimized(
            audio_data, 
            words, 
            settings_manager.get('pause_duration'), 
            settings_manager.get('speed_factor'),
            settings_manager.get('random_order')  # Добавляем параметр случайного порядка
        )
    except KeyboardInterrupt:
        print("\n⏹️ Воспроизведение прервано пользователем")
    except Exception as e:
        print(f"❌ Ошибка при воспроизведении: {e}")
    finally:
        # Всегда сохраняем настройки и кэш при завершении
        settings_manager.save_settings()
        cache.save_cache()

def clear_all_data():
    """Очистка всех данных"""
    # Очистка кэша
    cache_files = ['audio_cache.pkl']
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            os.remove(cache_file)
            print(f"🧹 Кэш {cache_file} очищен")
    
    # Очистка настроек
    settings_file = 'tts_settings.json'
    if os.path.exists(settings_file):
        os.remove(settings_file)
        print(f"🧹 Настройки {settings_file} очищены")

def show_settings_info():
    """Показывает текущие настройки"""
    settings_manager = SettingsManager()
    settings_manager.print_current_settings()

if __name__ == "__main__":
    print("🚀 УСКОРЕННОЕ АУДИО ВОСПРОИЗВЕДЕНИЕ С СОХРАНЕНИЕМ НАСТРОЕК")
    print("=" * 65)
    
    print("\n🎮 РЕЖИМЫ:")
    print("1 - Основной режим (с настройками)")
    print("2 - Быстрый запуск с сохраненными настройками")
    print("3 - Просмотр текущих настроек")
    print("4 - Очистка всех данных (кэш + настройки)")
    print("5 - Тест скорости")
    
    choice = input("Выберите режим (1-5): ").strip()
    
    if choice == "2":
        # Быстрый запуск с сохраненными настройками
        settings_manager = SettingsManager()
        cache = AudioCache()
        words = read_words_from_file("listen.txt")
        if words:
            print("⚡ Быстрый запуск с сохраненными настройками")
            settings_manager.print_current_settings()
            
            audio_data = generate_audio_parallel(
                words, 
                speed_factor=settings_manager.get('speed_factor'), 
                max_workers=settings_manager.get('max_workers'), 
                language=settings_manager.get('language'),
                cache=cache
            )
            play_words_optimized(
                audio_data, 
                words, 
                settings_manager.get('pause_duration'), 
                settings_manager.get('speed_factor'),
                settings_manager.get('random_order')  # Добавляем параметр случайного порядка
            )
            settings_manager.save_settings()
            cache.save_cache()
    elif choice == "3":
        show_settings_info()
    elif choice == "4":
        clear_all_data()
    elif choice == "5":
        # Тест скорости
        words = read_words_from_file("listen.txt")
        if words:
            settings_manager = SettingsManager()
            cache = AudioCache()
            start = time.time()
            generate_audio_parallel(words, cache=cache)
            print(f"⏱️ Тест скорости: {time.time() - start:.1f}с")
            settings_manager.save_settings()
            cache.save_cache()
    else:
        main_optimized_with_cache_and_settings()
