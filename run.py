#!/usr/bin/env python3
"""Запуск бота из корня проекта: python run.py"""
import runpy
import sys
from pathlib import Path

BOT_DIR = Path(__file__).resolve().parent / "bot"
sys.path.insert(0, str(BOT_DIR))
runpy.run_path(str(BOT_DIR / "main.py"), run_name="__main__")
