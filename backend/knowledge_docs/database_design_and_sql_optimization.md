【数据库设计与SQL优化指南】

## 一、当前数据库表结构分析

### 1.1 核心数据表
1. **ads_region_consume_analysis** - 区域消费分析表
   - 主要字段：city_name, province_name, main_consume_category, main_consume_brand, stat_month
   - 核心指标：total_sale_amount, total_order_count, total_active_user, total_pay_rate, city_avg_order_value
   - 数据粒度：城市×月份

2. **ads_product_feature_full** - 商品特征宽表
   - 主要字段：product_id, product_name, product_category, product_brand, price_level, hot_level, stat_month
   - 核心指标：total_sale_quantity, total_sale_amount, buy_conversion_rate, product_rating
   - 数据粒度：商品×月份

3. **ads_user_profile_full** - 用户画像标签表
   - 主要字段：user_id, user_gender, age_group, user_city, user_occupation, user_income_level, membership_level, rfm_segment
   - 核心指标：total_consumption, avg_order_value, repurchase_count
   - 数据粒度：用户维度（无时间维度）

4. **ads_user_item_interaction_matrix** - 用户-商品交互矩阵表
   - 主要字段：user_id, product_id, stat_month
   - 核心指标：interaction_score, pv_count, fav_count, cart_count, buy_count
   - 数据粒度：用户×商品×月份

## 二、跨表查询场景与解决方案

### 2.1 常见跨表查询需求
1. **城市+品类分析**：需要连接区域表和商品表
   - 示例：查询"贵阳数码电子品类的销售额"
   - 当前限制：区域表只有main_consume_category，商品表有product_category，两者无法直接关联

2. **用户行为分析**：需要连接用户表、商品表和交互表
   - 示例：分析"高价值用户偏好的商品品类"
   - 解决方案：通过user_id连接用户表和交互表，再通过product_id连接商品表

3. **区域用户画像**：需要连接区域表和用户表
   - 示例：分析"贵阳不同收入水平用户的消费特征"
   - 当前限制：区域表基于城市，用户表基于user_city，可以通过city_name连接

### 2.2 推荐解决方案
1. **建立维度映射表**：创建city_category_mapping表，建立城市-品类关联关系
2. **使用物化视图**：为常用跨表查询创建预计算的物化视图
3. **ETL数据整合**：在数据仓库层创建整合宽表，减少实时连接开销

## 三、SQL优化最佳实践

### 3.1 查询性能优化
1. **索引设计原则**
   - 主键索引：所有表必须有主键（建议自增ID）
   - 组合索引：对频繁查询的WHERE条件字段建立组合索引
   - 覆盖索引：对SELECT字段建立索引，避免回表查询

2. **查询优化技巧**
   - 避免SELECT *：只查询需要的字段
   - 使用EXPLAIN分析执行计划
   - 合理使用JOIN：小表驱动大表
   - 避免在WHERE子句中使用函数

### 3.2 当前表索引建议
1. **ads_region_consume_analysis**
   - 主键索引：id (自增)
   - 组合索引：(city_name, stat_month) - 用于城市时间查询
   - 组合索引：(main_consume_category, stat_month) - 用于品类分析

2. **ads_product_feature_full**
   - 主键索引：product_id
   - 组合索引：(product_category, stat_month) - 用于品类时间分析
   - 单列索引：product_brand - 用于品牌查询

3. **ads_user_item_interaction_matrix**
   - 组合索引：(user_id, product_id, stat_month) - 用于用户-商品交互查询
   - 组合索引：(product_id, stat_month) - 用于商品维度分析

## 四、时间范围处理规范

### 4.1 时间格式标准
- 数据库存储格式：YYYY-MM（如2024-01）
- 用户输入格式：
  - 完整年月：2024年1月 → 2024-01
  - 年份：2024年 → 2024-%（匹配全年）
  - 月份：1月 → %-01（匹配所有年份的1月）
  - 季度：Q1 2024 → 2024-01, 2024-02, 2024-03
  - 半年：2024年上半年 → 2024-01 至 2024-06

### 4.2 特殊时间处理
1. **最近N天**：转换为日期范围，如最近30天 → stat_month IN (最近30天包含的月份)
2. **同比环比**：需要计算时间偏移，如同比 = (当前期 - 去年同期) / 去年同期
3. **默认时间**：当用户未指定时间时，默认查询最近一个月的数据

## 五、复杂查询示例

### 5.1 跨表连接查询
```sql
-- 示例：查询贵阳数码电子品类销售额（需要维度映射）
SELECT 
    r.city_name,
    p.product_category,
    SUM(p.total_sale_amount) as category_sales
FROM ads_region_consume_analysis r
JOIN city_category_mapping m ON r.city_name = m.city_name
JOIN ads_product_feature_full p ON m.product_category = p.product_category
WHERE r.city_name = '贵阳'
    AND p.product_category = '数码电子'
    AND r.stat_month LIKE '2024-%'
    AND p.stat_month LIKE '2024-%'
GROUP BY r.city_name, p.product_category;
```

### 5.2 用户行为漏斗分析
```sql
-- 示例：分析用户从浏览到购买的转化漏斗
SELECT 
    u.age_group,
    u.user_income_level,
    COUNT(DISTINCT CASE WHEN i.pv_count > 0 THEN i.user_id END) as pv_users,
    COUNT(DISTINCT CASE WHEN i.fav_count > 0 THEN i.user_id END) as fav_users,
    COUNT(DISTINCT CASE WHEN i.cart_count > 0 THEN i.user_id END) as cart_users,
    COUNT(DISTINCT CASE WHEN i.buy_count > 0 THEN i.user_id END) as buy_users
FROM ads_user_profile_full u
JOIN ads_user_item_interaction_matrix i ON u.user_id = i.user_id
WHERE u.user_city = '贵阳'
    AND i.stat_month LIKE '2024-%'
GROUP BY u.age_group, u.user_income_level;
```

## 六、系统局限性说明

### 6.1 当前架构限制
1. **跨表连接成本高**：实时连接多张大表会影响查询性能
2. **维度不一致**：区域表的消费类别与商品表的商品类别无法直接关联
3. **时间粒度单一**：所有表都使用月度统计，无法支持更细粒度（如日级）分析

### 6.2 改进建议
1. **数据仓库重构**：建立统一维度模型，消除跨表连接障碍
2. **预计算层**：针对常见分析场景创建预计算表
3. **缓存机制**：对高频查询结果实施缓存，减少数据库压力

## 七、关键词
数据库设计 SQL优化 跨表查询 索引设计 时间处理 维度建模 性能调优 数据仓库