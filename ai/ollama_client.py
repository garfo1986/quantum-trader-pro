"""
Integración opcional con IA local mediante Ollama (100% gratuita y privada).
La aplicación funciona con normalidad incluso si Ollama no está instalado o ejecutándose.
"""

from typing import List, Dict, Any, Optional
import requests
import json


class OllamaClient:
    """Cliente para comunicarse con el servidor local de Ollama (http://localhost:11434)."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url.rstrip("/")

    def check_availability(self) -> Dict[str, Any]:
        """Comprueba si el demonio de Ollama está activo y devuelve los modelos instalados."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name") for m in data.get("models", [])]
                return {
                    "available": True,
                    "models": models,
                    "count": len(models)
                }
        except Exception:
            pass

        return {
            "available": False,
            "models": [],
            "count": 0,
            "message": "Ollama no detectado en localhost:11434. La app continúa funcionando con normalidad sin IA."
        }

    def generate_response(self, model: str, prompt: str, system_prompt: str = "") -> Dict[str, Any]:
        """Envía una petición de inferencia local sin streaming."""
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2  # Baja temperatura para consistencia técnica
            }
        }
        try:
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=25)
            if resp.status_code == 200:
                result = resp.json()
                return {"success": True, "response": result.get("response", "").strip()}
            return {"success": False, "error": f"Error HTTP {resp.status_code} desde Ollama."}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Tiempo de espera agotado al conectar con Ollama."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def explain_signal(self, symbol: str, signal_dict: Dict[str, Any], model: str) -> str:
        """Pide a la IA local que interprete la señal generada con los datos reales suministrados."""
        sys_p = (
            "Eres un analista financiero cuantitativo. Explica de forma concisa y profesional "
            "la confluencia técnica proporcionada. NO inventes precios ni datos que no estén en el contexto."
        )
        prompt = f"""
        Activo: {symbol}
        Precio Actual: ${signal_dict.get('price', 0):,.2f}
        Señal del Sistema: {signal_dict.get('type')}
        Score Multi-Factor: {signal_dict.get('score')}/100
        Razón Algorítmica: {signal_dict.get('reason')}

        Factores Alcistas Detectados:
        {json.dumps(signal_dict.get('bullish_factors', []), indent=2, ensure_ascii=False)}

        Factores Bajistas Detectados:
        {json.dumps(signal_dict.get('bearish_factors', []), indent=2, ensure_ascii=False)}

        Por favor redacta un resumen ejecutivo en 2 párrafos explicando qué significa esta señal técnica para el trader y cómo gestionar el riesgo.
        """
        res = self.generate_response(model, prompt, sys_p)
        if res["success"]:
            return res["response"]
        return f"No se pudo generar la explicación con Ollama: {res.get('error')}"

    def summarize_news(self, news_items: List[Dict[str, Any]], model: str) -> str:
        """Genera un resumen ejecutivo de noticias con la IA local."""
        if not news_items:
            return "No hay noticias para resumir."

        headlines = [f"- {item['title']} (Fuente: {item['source']})" for item in news_items[:8]]
        headlines_text = "\n".join(headlines)

        sys_p = "Eres un analista de mercados. Resume objetivamente el impacto conjunto de estos titulares en 3 puntos clave."
        prompt = f"Titulares financieros recientes:\n{headlines_text}\n\nResumen en 3 puntos claros:"

        res = self.generate_response(model, prompt, sys_p)
        if res["success"]:
            return res["response"]
        return f"Error al resumir con Ollama: {res.get('error')}"
