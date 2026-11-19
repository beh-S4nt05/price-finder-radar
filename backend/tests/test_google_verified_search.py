"""Google-only discovery policy and verified/pending segregation."""
from unittest.mock import AsyncMock
import pytest
from src.application import google_verified_search as mod
from src.domain.services.comparator_service import CrossStoreComparatorService
from src.domain.entities.product_offer import ProductOffer
from src.domain.value_objects.money import Money
from src.domain.value_objects.seller_reliability import SellerReliability


def offer(url="https://store.example/item"):
    return ProductOffer(title="Notebook 16gb",url=url,pix_price=Money(100),
                        store_name="Store",scraper_engine="direct",
                        reliability=SellerReliability.evaluate("Store"))


@pytest.mark.parametrize("url", [
    "http://localhost/a", "http://127.0.0.1", "http://10.0.0.1/a",
    "http://169.254.169.254/latest", "file:///etc/passwd",
    "https://user:pass@example.com", "http://host.internal",
])
def test_private_destinations_rejected(url):
    assert not mod.public_url(url)


def test_public_url():
    assert mod.public_url("https://store.example/item")


@pytest.mark.asyncio
async def test_missing_google_configuration(monkeypatch):
    monkeypatch.delenv("GOOGLE_SEARCH_API_KEY",raising=False)
    monkeypatch.delenv("GOOGLE_SEARCH_ENGINE_ID",raising=False)
    found,error=await mod.google_discover("notebook")
    assert found==[] and "não configurado" in error


@pytest.mark.asyncio
async def test_google_only_api_request(monkeypatch):
    monkeypatch.setenv("GOOGLE_SEARCH_API_KEY","test")
    monkeypatch.setenv("GOOGLE_SEARCH_ENGINE_ID","cx")
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"items":[{"title":"A","link":"https://store.example/item"}]}
    class Client:
        def __init__(self,**kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*args): pass
        async def get(self,url,params):
            calls.append((url,params))
            return Response()
    monkeypatch.setattr(mod.httpx,"AsyncClient",Client)
    found,error=await mod.google_discover("notebook")
    assert error is None and len(found)==1
    assert calls[0][0]=="https://www.googleapis.com/customsearch/v1"
    assert calls[0][1]["q"]=="notebook"


@pytest.mark.asyncio
async def test_verified_and_pending_separation(monkeypatch):
    async def discover(query,limit):
        return [
            {"title":"Real","url":"https://store.example/item","snippet":"R$ 90"},
            {"title":"No price","url":"https://empty.example/item","snippet":"R$ 10"},
        ],None
    monkeypatch.setattr(mod,"google_discover",discover)
    monkeypatch.setattr(mod,"_public_dns",AsyncMock(return_value=True))
    inspector=AsyncMock()
    inspector.inspect_url.side_effect=[[offer()],[]]
    result=await mod.verified_google_search("Notebook 16gb",inspector,CrossStoreComparatorService())
    assert result["discovery_engine"]=="google"
    assert result["verification_policy"]=="direct_source_only"
    assert len(result["offers"])==1
    assert result["offers"][0]["pix_price"]==100
    assert len(result["pending"])==1
    assert result["pending"][0]["url"]=="https://empty.example/item"


@pytest.mark.asyncio
async def test_wrong_source_never_verified(monkeypatch):
    async def discover(query,limit):
        return [{"title":"Wrong","url":"https://store.example/item","snippet":""}],None
    monkeypatch.setattr(mod,"google_discover",discover)
    monkeypatch.setattr(mod,"_public_dns",AsyncMock(return_value=True))
    inspector=AsyncMock()
    inspector.inspect_url.return_value=[offer("https://another.example/item")]
    result=await mod.verified_google_search("Notebook 16gb",inspector,CrossStoreComparatorService())
    assert result["offers"]==[]
    assert len(result["pending"])==1
