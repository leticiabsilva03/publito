# services/comunicados_service.py
import httpx
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
SICOM_URL = "https://portalsicom1.tce.mg.gov.br/comunicado/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def fetch_ultimos_comunicados(limit: int = 5) -> Optional[List[Dict]]:
    """
    Busca os comunicados mais recentes do portal SICOM.
    """
    try:
        async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:
            response = await client.get(SICOM_URL, follow_redirects=True, timeout=15.0)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        comunicados = []

        articles = soup.find_all('article', class_='post') 
        if not articles:
            logger.warning("Nenhum 'article' com a classe 'post' foi encontrado. A estrutura do site pode ter mudado.")
            return None

        for article in articles[:limit]:
            container = article.find('div', class_='post_text')
            if not container:
                continue

            h2_tag = container.find('h2')
            titulo_postagem = h2_tag.find('a') if h2_tag else None
            data_postagem = h2_tag.find('span', class_='date') if h2_tag else None
            resumo = container.find('p')

            if titulo_postagem and resumo:
                texto_resumo = resumo.get_text(separator=" ", strip=True)

                comunicados.append({
                    "titulo_comunicado": titulo_postagem.get_text(strip=True),
                    "data_comunicado": data_postagem.get_text(strip=True) if data_postagem else "Data não encontrada",
                    "resumo": texto_resumo,
                    "link": titulo_postagem['href']
                })

        return comunicados
    except Exception as e:
        logger.error(f"Erro inesperado no serviço de comunicados: {e}", exc_info=True)

    return None