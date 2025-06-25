# test_umgebung.py
# Dieses Skript testet, ob alle unsere Bibliotheken korrekt installiert sind.

try:
    import backtrader as bt
    import pandas as pd
    import matplotlib
    import yfinance as yf
    import numpy as np  # Wir testen auch numpy mit!

    print("✅ Perfekt! Alle Bibliotheken sind startklar.")
    print("-" * 40)
    print(f"Backtrader Version: {bt.__version__}")
    print(f"Pandas Version:     {pd.__version__}")
    print(f"NumPy Version:      {np.__version__}")
    print(f"yfinance Version:   {yf.__version__}")
    print("-" * 40)

except ImportError as e:
    print(f"❌ Fehler! Eine Bibliothek fehlt oder konnte nicht geladen werden: {e}")