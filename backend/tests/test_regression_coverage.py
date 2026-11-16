"""Regression and integration coverage of application orchestration and domain boundaries."""
from decimal import Decimal
from unittest.mock import AsyncMock
import asyncio
import csv
import io
import pytest

from src.application.use_cases import SearchOffersUseCase, InspectUrlsUseCase, WatchlistUseCase, ExportOffersCsvUseCase
from src.domain.entities.alert_config import AlertChannelConfig, DealNotificationPayload
from src.domain.entities.product_offer import ProductOffer, AnomalyClassification
from src.domain.entities.watchlist_item import WatchlistItem
from src.domain.services.comparator_service import CrossStoreComparatorService
from src.domain.services.dork_builder import AdvancedSearchDorkBuilder
from src.domain.value_objects.money import Money
from src.domain.value_objects.search_criteria import SearchCriteria, ProductCategory, SortCriterion
from src.domain.value_objects.seller_reliability import SellerReliability, TrustTier


def offer(price=100, title="Notebook 16gb", store="Amazon", **kw):
    return ProductOffer(title=title, url="https://example.org/item", pix_price=Money(Decimal(str(price))),
                        store_name=store, scraper_engine="test", reliability=SellerReliability.evaluate(store), **kw)


def watch(**kw):
    defaults=dict(id=1,label="Notebook",query_or_url="Notebook 16gb",is_direct_url=False,
                  category="all",target_pix_price=100)
    defaults.update(kw)
    return WatchlistItem(**defaults)


@pytest.mark.parametrize("raw,expected", [
    ("R$ 1.299,90","1299.90"), ("1299.90","1299.90"), ("997,00","997.00"),
    (129, "129.00"), (Decimal("2.345"),"2.35"), ("R$ 0,00",None),
    (None,None), ("",None), ("sem preço",None), (-3,None),
    (float("nan"),None),
])
def test_money_parsing(raw, expected):
    got=Money.from_raw(raw)
    assert (str(got.amount) if got else None)==expected


def test_money_validation_and_discount():
    with pytest.raises(ValueError):
        Money(Decimal("-1"))
    assert Money(Decimal("1299.9")).formatted_brl()=="R$ 1.299,90"
    assert Money(80).discount_percentage_from(Money(100))==20
    assert Money(100).discount_percentage_from(Money(100))==0
    assert Money(100).discount_percentage_from(Money(0))==0
    assert Money(12).as_float==12.0


@pytest.mark.parametrize("store,seller,aggregator,tier",[
    ("Amazon",None,False,TrustTier.OFFICIAL_DIRECT),
    ("Amazon","Third party",False,TrustTier.VERIFIED_MARKETPLACE),
    ("Mercado Livre",None,False,TrustTier.VERIFIED_MARKETPLACE),
    ("Unknown",None,True,TrustTier.AGGREGATOR_VERIFIED),
    ("Unknown",None,False,TrustTier.THIRD_PARTY_SELLER),
])
def test_seller_tiers(store,seller,aggregator,tier):
    assert SellerReliability.evaluate(store,seller,via_trusted_aggregator=aggregator).trust_tier==tier


@pytest.mark.parametrize("rating,reviews",[(5,100),(4.4,50),(3.1,0),(4.0,101),(None,None)])
def test_seller_rating_signals(rating,reviews):
    obj=SellerReliability.evaluate("Other",rating=rating,review_count=reviews)
    assert 35<=obj.score<=99
    assert obj.badge_label=="Vendedor Externo"


def test_seller_badges():
    assert SellerReliability.evaluate("Amazon").badge_label=="Loja Oficial"
    assert SellerReliability.evaluate("Magalu").badge_label=="Marketplace Oficial"
    assert SellerReliability.evaluate("Other",via_trusted_aggregator=True).badge_label=="Parceiro Verificado"


def test_watchlist_history_and_alert_transition():
    item=watch()
    assert not item.is_below_target
    assert not item.register_observation(120,None,"A","https://a")
    assert item.register_observation(90,100,"B","https://b","https://img")
    assert item.is_below_target
    assert not item.register_observation(95,None,"C","https://c","https://other")
    assert item.register_observation(80,None,"D","https://d")
    assert item.lowest_historical_pix==80
    assert item.image_url=="https://img"
    assert len(item.history)==4
    assert not watch(target_pix_price=0).register_observation(0,None,"A","https://a")


def test_product_offer_properties():
    o=offer(80,installment_price=Money(100),original_price=Money(160))
    assert o.effective_installment_total.amount==100
    assert o.pix_savings_vs_installment_pct==20
    assert o.listed_discount_pct==50
    assert len(o.offer_id)==16
    assert offer().effective_installment_total.amount==100
    assert offer().pix_savings_vs_installment_pct==0
    assert offer().listed_discount_pct==0
    assert o.simulate_resale_profit(150,10,5)["net_profit"]==50


@pytest.mark.parametrize("sort",list(SortCriterion))
def test_comparator_sort_modes(sort):
    offers=[offer(100,store="Amazon"),offer(120,store="Magalu"),offer(90,store="Pichau")]
    ranked,summary=CrossStoreComparatorService().process_and_rank(offers,SearchCriteria(query="",sort_by=sort))
    assert len(ranked)==3
    assert summary.total_offers==3
    assert summary.lowest_pix==90
    assert summary.highest_pix==120


def test_comparator_filters_and_deduplication():
    offers=[offer(100),offer(80),offer(40,title="Notebook 16gb usado"),
            offer(20,title="Capinha notebook 16gb"),offer(110,store="Aliexpress"),
            offer(70,store="Pichau",free_shipping=True)]
    ranked,summary=CrossStoreComparatorService().process_and_rank(
        offers,SearchCriteria(query="Notebook 16gb",only_national_stores=True,
                              only_free_shipping=True,min_price=50,max_price=90))
    assert len(ranked)==1 and ranked[0].pix_price.amount==70
    assert summary.total_offers==1
    ranked,_=CrossStoreComparatorService().process_and_rank(
        offers,SearchCriteria(query="Notebook 16gb",only_national_stores=True))
    assert len(ranked)==2


def test_comparator_empty_and_anomaly():
    comparator=CrossStoreComparatorService()
    ranked,summary=comparator.process_and_rank([],SearchCriteria(query=""))
    assert ranked==[] and summary.lowest_pix is None
    offers=[offer(50,store="Amazon"),offer(100,store="Magalu"),offer(110,store="Pichau")]
    ranked,summary=comparator.process_and_rank(offers,SearchCriteria(query=""))
    assert summary.potential_bugs_count>=1
    filtered,_=comparator.process_and_rank([offer(100)],SearchCriteria(query="",only_anomalies=True))
    assert filtered==[]


def test_export_csv_and_roi_zero():
    csv_text=ExportOffersCsvUseCase().generate_csv([
        {"title":"Produto","pix_price":100,"quantity":2,"target_resale_price":160,
         "marketplace_fee_pct":10,"coupon_code":"SAVE"},
        {"title":"Zero","pix_price":0,"quantity":0},
    ])
    assert csv_text.startswith("\ufeff")
    rows=list(csv.reader(io.StringIO(csv_text.lstrip("\ufeff")),delimiter=";"))
    assert len(rows)==3 and rows[1][0]=="Produto" and rows[1][4]=="2"
    assert rows[2][4]=="1"


def make_search(scrapers=None,config=None,notifiers=None):
    logs=AsyncMock()
    cfg=AsyncMock()
    cfg.get_config.return_value=config or AlertChannelConfig()
    uc=SearchOffersUseCase(scrapers or [],CrossStoreComparatorService(),
                           AdvancedSearchDorkBuilder(),logs,cfg,notifiers or [])
    return uc,logs,cfg


@pytest.mark.asyncio
async def test_search_orchestration_success_error_empty_and_filter():
    good=AsyncMock()
    good.engine_id="good";good.display_name="Good";good.target_verticals=["all"]
    good.search.return_value=[offer(100)]
    broken=AsyncMock()
    broken.engine_id="broken";broken.display_name="Broken";broken.target_verticals=["all"]
    broken.search.side_effect=RuntimeError("offline")
    empty=AsyncMock()
    empty.engine_id="empty";empty.display_name="Empty";empty.target_verticals=["all"]
    empty.search.return_value=[]
    uc,logs,_=make_search([good,broken,empty])
    assert len(uc.available_engines)==3
    ranked,summary,tel,dorks=await uc.execute(SearchCriteria(query="Notebook 16gb"))
    assert len(ranked)==1 and summary.total_offers==1
    assert [t.status for t in tel]==["ok","error","empty"]
    logs.record_search.assert_awaited_once()
    ranked,_,tel,_=await uc.execute(SearchCriteria(query="",enabled_engines=["good"]))
    assert len(tel)==1 and len(ranked)==1


@pytest.mark.asyncio
async def test_search_timeout(monkeypatch):
    scraper=AsyncMock()
    scraper.engine_id="slow";scraper.display_name="Slow";scraper.target_verticals=["all"]
    scraper.search.side_effect=asyncio.TimeoutError()
    uc,_,_=make_search([scraper])
    _,_,telemetry,_=await uc.execute(SearchCriteria(query=""))
    assert telemetry[0].status=="timeout"


@pytest.mark.asyncio
async def test_inspect_urls_exception_isolation():
    inspector=AsyncMock()
    inspector.inspect_url.side_effect=[[offer(50)],RuntimeError("bad"),[]]
    uc=InspectUrlsUseCase(inspector,CrossStoreComparatorService())
    ranked,summary=await uc.execute([" https://a ","https://b","https://c"],force_browser=True)
    assert summary.total_offers==1
    assert ranked[0].pix_price.amount==50
    assert inspector.inspect_url.await_count==3


@pytest.mark.asyncio
async def test_watchlist_use_case_crud_and_refresh():
    item=watch()
    repo=AsyncMock()
    repo.list_all.return_value=[item]
    repo.save.side_effect=lambda x:x
    repo.get_by_id.return_value=item
    repo.delete.return_value=True
    inspector=AsyncMock()
    search=AsyncMock()
    search.execute.return_value=([offer(80)],None,None,None)
    cfg=AsyncMock()
    cfg.get_config.return_value=AlertChannelConfig()
    uc=WatchlistUseCase(repo,search,inspector,cfg,[])
    assert await uc.list_items()==[item]
    assert await uc.create_item(item)==item
    assert (await uc.update_target(1,90,"note")).notes=="note"
    assert await uc.remove_item(1)
    refreshed=await uc.refresh_single(1)
    assert refreshed.current_best_pix==80
    repo.add_snapshot.assert_awaited_once()
    repo.get_by_id.return_value=None
    assert await uc.update_target(1,50) is None
    assert await uc.refresh_single(1) is None


@pytest.mark.asyncio
async def test_watchlist_direct_url_and_alert():
    item=watch(is_direct_url=True,query_or_url="https://example.org/item",notify_webhook=True)
    repo=AsyncMock()
    repo.get_by_id.return_value=item
    repo.save.side_effect=lambda x:x
    inspector=AsyncMock()
    inspector.inspect_url.return_value=[offer(90),offer(70,store="Pichau")]
    cfg=AsyncMock()
    cfg.get_config.return_value=AlertChannelConfig(webhook_enabled=True)
    notifier=AsyncMock()
    notifier.channel_name="webhook"
    uc=WatchlistUseCase(repo,AsyncMock(),inspector,cfg,[notifier])
    await uc.refresh_single(1)
    notifier.send.assert_awaited_once()
    assert item.current_best_pix==70


@pytest.mark.asyncio
async def test_dispatch_alert_notification_failure_is_isolated():
    notifier=AsyncMock()
    notifier.channel_name="webhook"
    notifier.send.side_effect=RuntimeError("offline")
    uc,_,_=make_search(notifiers=[notifier])
    from src.domain.services.comparator_service import MarketComparisonSummary
    summary=MarketComparisonSummary(1,["Amazon"],100,100,150,150,1,0,50)
    await uc._dispatch_bug_alert(offer(100),summary,AlertChannelConfig(webhook_enabled=True))
    notifier.send.assert_awaited_once()


def test_notification_payload_text():
    p=DealNotificationPayload("Alert","Notebook","Store","R$ 100","R$ 120","https://example.org",
                              median_price_brl="R$ 200",discount_pct=50)
    assert "50.0%" in p.format_whatsapp_text()
