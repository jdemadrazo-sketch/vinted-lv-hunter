name: VintedLVScraper

on:
  schedule:
    - cron: '0 9,21 * * *'
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scraper:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Instalar dependencias
        run: pip install requests

      - name: Ejecutar scraper
        run: python scraper.py

      - name: Guardar datos
        run: |
          git config user.name "VintedBot"
          git config user.email "bot@vinted.com"
          git add data.json
          git diff --staged --quiet || git commit -m "Update data.json"
          git push
