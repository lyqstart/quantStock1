-- 分钟数据压缩策略：30天以上的分钟数据启用压缩
-- 对应 DD-CORE-020 / REQ-CORE-030

-- 启用 clean.stock_minute hypertable 压缩
-- segmentby=security_code: 按股票代码分段（查询高频过滤条件）
-- orderby=trade_time DESC: 按交易时间倒序（最新数据优先）
ALTER TABLE clean.stock_minute SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'security_code',
  timescaledb.compress_orderby = 'trade_time DESC'
);

-- 添加压缩策略：自动压缩 30 天以上的数据 chunk
SELECT add_compression_policy('clean.stock_minute', INTERVAL '30 days');
