#!/usr/bin/env python3
# -*- coding: utf-8 -*-

print("Content-type: text/html\n")

try:
    import TTS
    print("Coqui TTS ist installiert und verfügbar!")
except ImportError:
    print("Coqui TTS ist NICHT installiert oder nicht gefunden.")