"""ETL 业务逻辑。

本包的所有"业务硬编码"必须以 **provider / 配置文件** 形式注入,禁止在代码里
出现真实品牌名 / 客户代号 / 仓库名 / 厂商字符串(对应 PLAN.md §6 P0)。

子模块:
  - brand:     自营品牌白名单抽象(BrandWhitelistProvider)
  - rules:     业务规则阈值加载(BusinessRules)
  - pipeline:  ETL 步骤注册表 + DefaultPipeline
"""
