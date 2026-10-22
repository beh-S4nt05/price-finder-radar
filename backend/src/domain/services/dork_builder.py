"""Domain Service: AdvancedSearchDorkBuilder — Real Search Engine Operators Generator."""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from typing import List

from src.domain.value_objects.search_criteria import ProductCategory


@dataclass(frozen=True, slots=True)
class AdvancedDorkLink:
    id: str
    engine_name: str
    label: str
    dork_query: str
    target_url: str
    description: str


CATEGORY_SITES = {
    ProductCategory.ALL: [
        "amazon.com.br",
        "mercadolivre.com.br",
        "terabyteshop.com.br",
        "kabum.com.br",
        "meupc.net",
        "buscape.com.br",
        "kalunga.com.br",
    ],
    ProductCategory.INFORMATICA: [
        "terabyteshop.com.br",
        "kabum.com.br",
        "pichau.com.br",
        "meupc.net",
        "amazon.com.br",
        "mercadolivre.com.br",
    ],
    ProductCategory.ESCRITORIO: [
        "kalunga.com.br",
        "amazon.com.br",
        "mercadolivre.com.br",
        "buscape.com.br",
        "kabum.com.br",
    ],
    ProductCategory.ELETRICA: [
        "copafer.com.br",
        "mercadolivre.com.br",
        "amazon.com.br",
        "leroymerlin.com.br",
        "buscape.com.br",
    ],
}


class AdvancedSearchDorkBuilder:
    """Constructs precision search engine dorks for price hunting & bug discovery."""

    def build_dorks(
        self, query: str, category: ProductCategory = ProductCategory.ALL
    ) -> List[AdvancedDorkLink]:
        clean = " ".join(query.strip().split())
        if not clean:
            return []

        sites = CATEGORY_SITES.get(category, CATEGORY_SITES[ProductCategory.ALL])
        site_or_clause = " OR ".join(f"site:{s}" for s in sites)

        # 1. Google Official Stores Cross-Site PIX Dork
        dork_pix = f'"{clean}" ("PIX" OR "à vista" OR "R$") ({site_or_clause}) -usado -recondicionado'
        # 2. Google Price Drop / Promo Bug Dork
        dork_bug = f'intitle:"{clean}" ("de R$" "por R$" OR "% OFF" OR "cupom") ({site_or_clause})'
        # 3. Google Shopping Direct Comparator
        q_shop = urllib.parse.quote_plus(clean)
        # 4. Direct Official Marketplaces Split Dorks
        dork_ml_amz = (
            f'"{clean}" (site:produto.mercadolivre.com.br OR site:mercadolivre.com.br/p '
            f'OR site:amazon.com.br/dp) -usado'
        )
        # 5. Hardware & Tech Aggregator Dork (MeuPC + Terabyte + KaBuM)
        dork_tech = (
            f'{clean} (site:meupc.net/peca OR site:terabyteshop.com.br/produto '
            f'OR site:kabum.com.br/produto)'
        )

        return [
            AdvancedDorkLink(
                id="google_official_pix",
                engine_name="Google Dork",
                label="Lojas Oficiais + Preço PIX",
                dork_query=dork_pix,
                target_url=f"https://www.google.com.br/search?q={urllib.parse.quote_plus(dork_pix)}&hl=pt-BR&gl=br&tbs=qdr:m",
                description="Filtra páginas indexadas recentemente em lojas oficiais contendo menção explícita a PIX/à vista e exclui usados.",
            ),
            AdvancedDorkLink(
                id="google_promo_bug",
                engine_name="Google Bug Hunter",
                label="Caçador de Quedas & Cupons",
                dork_query=dork_bug,
                target_url=f"https://www.google.com.br/search?q={urllib.parse.quote_plus(dork_bug)}&hl=pt-BR&gl=br&tbs=qdr:w",
                description="Usa operador intitle: combinado a marcadores de desconto ('% OFF', 'cupom') na última semana.",
            ),
            AdvancedDorkLink(
                id="google_shopping_br",
                engine_name="Google Shopping",
                label="Google Shopping Menor Preço",
                dork_query=clean,
                target_url=f"https://www.google.com.br/search?q={q_shop}&udm=28&hl=pt-BR&gl=br",
                description="Abre grade comparativa direta do Google Shopping Brasil para conferência cruzada.",
            ),
            AdvancedDorkLink(
                id="ml_amazon_direct_pdp",
                engine_name="Dork PDP Direto",
                label="Páginas de Produto Amazon (/dp) & ML",
                dork_query=dork_ml_amz,
                target_url=f"https://duckduckgo.com/?q={urllib.parse.quote_plus(dork_ml_amz)}&kl=br-pt",
                description="Localiza URLs canônicas de produto (/dp/ e /p/) prontas para inspeção direta de preço.",
            ),
            AdvancedDorkLink(
                id="tech_pc_dork",
                engine_name="Dork Hardware",
                label="MeuPC + Terabyte + KaBuM!",
                dork_query=dork_tech,
                target_url=f"https://www.bing.com/search?q={urllib.parse.quote_plus(dork_tech)}&cc=br&setlang=pt-br",
                description="Foca exclusivamente em SKUs de informática e componentes em MeuPC.net, Terabyteshop e KaBuM!.",
            ),
        ]
