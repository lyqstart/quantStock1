from app.collect.executor import ITEM_FIELDS, ITEM_MODELS

def test_minute_and_financial_items_are_registered() -> None:
    items={'stock_minute','financial_income','financial_indicator'}
    assert items <= ITEM_FIELDS.keys()
    assert items <= ITEM_MODELS.keys()

def test_minute_provider_fields_do_not_request_synthetic_frequency() -> None:
    assert 'frequency' not in ITEM_FIELDS['stock_minute']
    assert 'trade_time' in ITEM_FIELDS['stock_minute']

def test_financial_fields_keep_revision_identity() -> None:
    assert {'ann_date','end_date','update_flag'} <= set(ITEM_FIELDS['financial_indicator'])
    assert {'ann_date','f_ann_date','end_date','report_type','update_flag'} <= set(ITEM_FIELDS['financial_income'])
