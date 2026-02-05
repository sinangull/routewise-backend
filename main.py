import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

# 1. Ayarları Yükle
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)
API_KEY = os.getenv("GOOGLE_API_KEY")

# Model Ayarı (Senin için çalışan model)
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-flash-latest') # veya gemini-2.0-flash

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Gelen Veri Modeli (KONUM BİLGİSİ EKLENDİ)
class RotaIstegi(BaseModel):
    gidilecek_yer: str
    gun_sayisi: int
    butce: str
    kisi_sayisi: str
    ilgi_alani: str
    # Kullanıcının anlık konumu (Opsiyonel olabilir ama biz göndereceğiz)
    user_lat: float = None
    user_lng: float = None

@app.post("/rota-olustur")
async def rota_olustur(istek: RotaIstegi):
    print(f"İstek: {istek.gidilecek_yer}, Konum: {istek.user_lat}, {istek.user_lng}")

    # Konum bilgisi varsa prompte ekle
    konum_bilgisi = ""
    if istek.user_lat and istek.user_lng:
        konum_bilgisi = f"""
        KULLANICININ ŞU ANKİ KONUMU: Enlem {istek.user_lat}, Boylam {istek.user_lng}.
        ÖNEMLİ: İlk günün ilk aktivitesini, kullanıcının bu konumuna EN YAKIN olan yerden başlat.
        Sonraki aktiviteleri de coğrafi yakınlığa göre mantıklı bir sırada diz (Zigzag çizme).
        """

    prompt = f"""
    Sen uzman bir tur rehberisin.
    
    KULLANICI BİLGİLERİ:
    - Hedef: {istek.gidilecek_yer}
    - Süre: {istek.gun_sayisi} Gün
    - Bütçe: {istek.butce}
    - Kiminle: {istek.kisi_sayisi}
    - İlgi: {istek.ilgi_alani}
    {konum_bilgisi}

    GÖREVİN:
    Bu bilgilere göre JSON formatında detaylı rota oluştur.
    
    KURALLAR:
    1. Her aktivite için tam koordinat ver.
    2. Sadece saf JSON döndür. Markdown yok.

    İSTENEN JSON FORMATI:
    {{
      "sehir": "Şehir İsmi",
      "gunler": [
        {{
          "gun": 1,
          "aktiviteler": [
            {{
              "isim": "Mekan Adı",
              "saat": "09:00 - 11:00",
              "aciklama": "Kısa bilgi",
              "koordinat": {{ "lat": 41.0, "lng": 29.0 }}
            }}
          ]
        }}
      ]
    }}
    JSON yanıtının başında veya sonunda ```json gibi işaretler KULLANMA. Sadece saf JSON ver.
    """

    try:
        response = model.generate_content(prompt)
        raw_text = response.text.strip().replace("```json", "").replace("```", "")
        
        # Olası json temizliği
        start = raw_text.find('{')
        end = raw_text.rfind('}') + 1
        if start != -1 and end != 0:
            raw_text = raw_text[start:end]

        return json.loads(raw_text)

    except Exception as e:
        print(f"Hata: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)