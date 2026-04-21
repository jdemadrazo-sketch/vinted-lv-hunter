import requests
import json
import time
from datetime import datetime

TELEGRAM_TOKEN = "8791653804:AAGPSyNM0CS2xmj6ErUg9jgp-c6w_vFJVuo"
TELEGRAM_CHAT_ID = "5897709372"
OUTPUT_FILE = "data.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "Accept-Language": "es-ES,es;q=0.9",
    "Referer": "https://www.vinted.es/",
}

def send(msg):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML",
              "disable_web_page_preview": True},
        timeout=10
    )

def cargar_datos():
    try:
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    except:
        return {"articulos": [], "ultima_actualizacion": "", "total": 0}

def guardar_datos(datos):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def scrape_vinted():
    articulos = []
    pagina = 1
    max_paginas = 20

    while pagina <= max_paginas:
        try:
            r = requests.get(
                "https://www.vinted.es/api/v2/catalog/items",
                params={
                    "search_text": "riñonera Louis Vuitton",
                    "brand_ids[]": "14",  # Louis Vuitton en Vinted
                    "order": "newest_first",
                    "per_page": 96,
                    "page": pagina,
                },
                headers=HEADERS,
                timeout=15
            )

            if r.status_code != 200:
                print(f"Error página {pagina}: {r.status_code}")
                break

            data = r.json()
            items = data.get("items", [])

            if not items:
                break

            for item in items:
                precio = float(item.get("price", {}).get("amount", 0))
                estado = item.get("status", "")
                titulo = item.get("title", "")
                url = item.get("url", "")
                item_id = str(item.get("id", ""))
                descripcion = item.get("description", "")
                foto = ""
                fotos = item.get("photos", [])
                if fotos:
                    foto = fotos[0].get("url", "")

                # Filtrar precios sospechosamente bajos (posibles falsificaciones)
                if precio < 80:
                    continue

                articulo = {
                    "id": item_id,
                    "titulo": titulo,
                    "precio": precio,
                    "estado": estado,
                    "url": url,
                    "foto": foto,
                    "descripcion": descripcion[:500],
                    "tiene_papeles": any(p in descripcion.lower() for p in [
                        "papeles", "recibo", "factura", "caja", "original",
                        "autentico", "autenticidad", "certificado", "ticket"
                    ]),
                    "fecha_scraping": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                articulos.append(articulo)

            total_paginas = data.get("pagination", {}).get("total_pages", 1)
            print(f"Página {pagina}/{min(total_paginas, max_paginas)} — {len(items)} artículos")

            if pagina >= total_paginas:
                break

            pagina += 1
            time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")
            break

    return articulos

def calcular_estadisticas(articulos):
    if not articulos:
        return {}

    precios = sorted([a["precio"] for a in articulos])
    n = len(precios)

    return {
        "total": n,
        "precio_minimo": min(precios),
        "precio_maximo": max(precios),
        "precio_medio": round(sum(precios) / n, 2),
        "percentil_25": precios[int(n * 0.25)],
        "percentil_50": precios[int(n * 0.50)],
        "percentil_75": precios[int(n * 0.75)],
        "percentil_10": precios[int(n * 0.10)],
    }

def main():
    print("Iniciando scraper Vinted LV...")
    send("🔍 Iniciando scraping de riñoneras Louis Vuitton en Vinted...")

    articulos = scrape_vinted()

    if not articulos:
        send("❌ No se encontraron artículos. Posiblemente sesión expirada.")
        return

    stats = calcular_estadisticas(articulos)

    # Añadir percentil a cada artículo
    precios_ordenados = sorted([a["precio"] for a in articulos])
    for a in articulos:
        pos = precios_ordenados.index(a["precio"])
        a["percentil"] = round((pos / len(precios_ordenados)) * 100)
        a["es_ganga"] = a["percentil"] <= 25
        a["es_muy_barato"] = a["percentil"] <= 10

    # Guardar JSON completo
    datos = {
        "ultima_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(articulos),
        "estadisticas": stats,
        "articulos": articulos
    }
    guardar_datos(datos)

    # Resumen por Telegram
    msg = (
        f"✅ <b>Scraping completado</b>\n\n"
        f"👜 Total artículos: <b>{len(articulos)}</b>\n"
        f"💶 Precio medio: <b>{stats['precio_medio']}€</b>\n"
        f"📊 Percentil 25%: {stats['percentil_25']}€\n"
        f"📊 Percentil 50%: {stats['precio_medio']}€\n"
        f"📊 Percentil 75%: {stats['percentil_75']}€\n"
        f"🔥 Gangas (top 10%): por debajo de {stats['percentil_10']}€\n\n"
        f"💾 JSON guardado con todos los datos"
    )
    send(msg)

    # Alertas de las mejores gangas
    gangas = [a for a in articulos if a["es_muy_barato"]]
    gangas.sort(key=lambda x: x["precio"])

    if gangas:
        send(f"🔥 <b>TOP GANGAS — Percentil 10% más barato</b>\n")
        for g in gangas[:10]:
            papeles = "📄 Menciona papeles/original" if g["tiene_papeles"] else ""
            send(
                f"👜 <b>{g['titulo']}</b>\n"
                f"💶 {g['precio']}€ — Percentil {g['percentil']}%\n"
                f"📦 Estado: {g['estado']}\n"
                f"{papeles}\n"
                f"🔗 {g['url']}"
            )
            time.sleep(1)

    print(f"Completado. {len(articulos)} artículos guardados.")

if __name__ == "__main__":
    main()
