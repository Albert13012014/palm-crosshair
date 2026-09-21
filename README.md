# Palm Crosshair Overlay

Кросс-платформенный оверлей-прицел для игр с поддержкой Windows и macOS.

![Crosshair Preview](icon.ico)

## Особенности

- 🎯 6 типов прицела: точка, крест, круг, крест+точка, T-образный, крест с разрывом
- 🎨 8 готовых цветов + выбор любого цвета
- 📏 Регулировка размера (2-60px), толщины (1-8px), прозрачности
- 🖱️ Режим перемещения (F6) - перетаскивание мышью
- 📍 Сброс позиции в центр экрана
- 💾 Автосохранение настроек в config.json
- 🖥️ Трей-иконка (Windows/macOS)
- ⌨️ Горячие клавиши даже в фокусе игры

## Горячие клавиши

- `F5` - показать/скрыть прицел
- `F6` - вкл/выкл режим перемещения
- `F10` - открыть окно настроек
- `F9` - сохранить и выйти

## Установка

### Установка зависимостей

**Windows:**
```bash
pip install keyboard pywin32 pystray pillow
```

**macOS:**
```bash
pip install pynput pystray pillow
```

### Запуск
```bash
python main.py
```

## Сборка в EXE/APP

### Локальная сборка (Windows)
```bash
python -m nuitka --onefile --standalone --assume-yes-for-downloads --enable-plugin=tk-inter --windows-console-mode=disable --windows-icon-from-ico="icon.ico" --output-filename="Palm Crosshair.exe" main.py
```

### GitHub Actions
При каждом пуше в репозиторий автоматически собираются версии:
- `Palm Crosshair.exe` для Windows
- `Palm Crosshair.app` для macOS

Скачать артефакты: `https://github.com/Albert13012014/palm-crosshair/actions`

## Настройки

Настройки сохраняются в файле `config.json`:
```json
{
  "preset": "cross_gap",
  "color": "#ffffff",
  "size": 8,
  "thickness": 2,
  "opacity": 1.0,
  "x": 960,
  "y": 540,
  "visible": true
}
```

## Технологии

- Python 3.11+
- tkinter - GUI
- keyboard (Windows) / pynput (macOS) - горячие клавиши
- pystray - трей-иконка
- Pillow - работа с изображениями
- Nuitka - компиляция в EXE/APP

## Лицензия

MIT