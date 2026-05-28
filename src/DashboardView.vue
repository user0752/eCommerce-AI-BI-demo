<template>
  <div class="dashboard-container">
    <!-- 顶部标题栏 -->
    <div class="dashboard-header">
      <div class="dh-left">
        <span class="dh-icon">💻</span>
        <span class="dh-title">贵州区域电商数据可视化大屏--推算系数：全量 GMV ≈ 当前 GMV / 0.0015，数据仅供学习参考。</span>
      </div>
      <div class="dh-right">
        <span class="dh-city-label">当前展示：</span>
        <span class="dh-city-name">{{ currentCity }}</span>
        <span class="dh-cycle">{{ cycleIndex + 1 }}/{{ cities.length }}</span>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="dashboard-body" v-if="!dashLoading && !dashError">
      <!-- 第一行：区域消费概览 + 城市销售排名 -->
      <div class="dash-row row-1">
        <div class="dash-card card-region-overview">
          <div class="card-header">
            <span class="card-icon">🏙️</span>
            <span class="card-title">2025年贵州区域消费概览</span>
            <span class="card-city-tag">{{ currentCity }}</span>
          </div>
          <div class="card-body" v-if="currentRegionData">
            <div class="kpi-grid">
              <div class="kpi-item">
                <div class="kpi-value kpi-primary">{{ formatNum(currentRegionData.total_sale_amount) }}</div>
                <div class="kpi-label">总销售额(元)</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-value kpi-secondary">{{ formatNum(currentRegionData.total_order_count) }}</div>
                <div class="kpi-label">总订单数</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-value kpi-info">{{ formatNum(currentRegionData.total_active_user) }}</div>
                <div class="kpi-label">活跃用户</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-value kpi-success">{{ formatPayRate(currentRegionData.total_pay_rate) }}</div>
                <div class="kpi-label">付费率</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-value kpi-warning">{{ formatNum(currentRegionData.city_avg_order_value) }}</div>
                <div class="kpi-label">客单价(元)</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-value kpi-rose">{{ currentRegionData.main_consume_category }}</div>
                <div class="kpi-label">主力消费类别</div>
              </div>
              <div class="kpi-item">
                <div class="kpi-value kpi-purple">{{ formatNum(currentRegionData.main_category_avg_price) }}</div>
                <div class="kpi-label">主品类均价(元)</div>
              </div>
            </div>
          </div>
          <div class="card-body" v-else>
            <div class="no-data">暂无数据</div>
          </div>
        </div>

        <div class="dash-card card-city-ranking">
          <div class="card-header">
            <span class="card-icon">🏆</span>
            <span class="card-title">区域城市2025年度销售额排名</span>
          </div>
          <div class="card-body">
            <div id="chart-city-ranking" class="chart-box" v-if="regionData.length > 0"></div>
            <div class="no-data" v-else>暂无数据</div>
          </div>
        </div>
      </div>

      <!-- 第二行：商品品类分布 + 用户画像 -->
      <div class="dash-row row-2">
        <div class="dash-card card-product">
          <div class="card-header">
            <span class="card-icon">📦</span>
            <span class="card-title">贵州2025年度商品品类销售分布</span>
            <span class="card-city-tag">{{ currentProductCategory }}</span>
          </div>
          <div class="card-body">
            <div id="chart-product-pie" class="chart-box" v-if="productData.length > 0"></div>
            <div class="no-data" v-else>暂无数据</div>
          </div>
        </div>

        <div class="dash-card card-user-age">
          <div class="card-header">
            <span class="card-icon">👤</span>
            <span class="card-title">贵州2025年度用户年龄段消费画像</span>
            <span class="card-city-tag">{{ currentAgeGroup }}</span>
          </div>
          <div class="card-body">
            <div id="chart-user-age" class="chart-box" v-if="userProfileData.age_data && userProfileData.age_data.length > 0"></div>
            <div class="no-data" v-else>暂无数据</div>
          </div>
        </div>
      </div>

      <!-- 第三行：交互漏斗 + 交互趋势 -->
      <div class="dash-row row-3">
        <div class="dash-card card-funnel">
          <div class="card-header">
            <span class="card-icon">🔄</span>
            <span class="card-title">贵州2025年度用户行为转化漏斗</span>
          </div>
          <div class="card-body">
            <div id="chart-funnel" class="chart-box" v-if="interactionData.funnel_data && interactionData.funnel_data.total_pv"></div>
            <div class="no-data" v-else>暂无数据</div>
          </div>
        </div>

        <div class="dash-card card-trend">
          <div class="card-header">
            <span class="card-icon">📈</span>
            <span class="card-title">贵州2025年度交互行为月度趋势</span>
          </div>
          <div class="card-body">
            <div id="chart-trend" class="chart-box" v-if="interactionData.trend_data && interactionData.trend_data.length > 0"></div>
            <div class="no-data" v-else>暂无数据</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div class="dashboard-loading" v-if="dashLoading">
      <div class="loading-spinner"></div>
      <p>正在加载数据，请稍候...</p>
    </div>

    <!-- 错误状态 -->
    <div class="dashboard-error" v-if="dashError && !dashLoading">
      <div class="error-icon">⚠️</div>
      <p>{{ dashError }}</p>
      <button class="retry-btn" @click="retryLoad">重新加载</button>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import api from './api'

// 统一图表色板（深蓝科技风）
const CHART_COLORS = ['#00D9FF', '#1890FF', '#722ED1', '#EB2F96', '#FA8C16', '#52C41A']

export default {
  name: 'DashboardView',
  setup() {
    const regionData = ref([])
    const productData = ref([])
    const userProfileData = ref({ age_data: [], gender_data: [], city_data: [] })
    const interactionData = ref({ trend_data: [], funnel_data: {} })

    const cities = ref([])
    const cycleIndex = ref(0)
    const currentCity = ref('')
    let cycleTimer = null
    let funnelLoopTimer = null
    let chartInstances = {}

    const ageGroups = ref([])
    const ageCycleIndex = ref(0)
    const currentAgeGroup = ref('')
    let ageCycleTimer = null

    const productCategories = ref([])
    const productCycleIndex = ref(0)
    const currentProductCategory = ref('')
    let productCycleTimer = null

    const currentRegionData = ref(null)
    const dashLoading = ref(true)
    const dashError = ref('')
    const retryCount = ref(0)

    function formatNum(val) {
      if (!val && val !== 0) return '-'
      const num = Number(val)
      if (isNaN(num)) return val
      if (num >= 10000) {
        return (num / 10000).toFixed(1) + '万'
      }
      return num.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
    }

    function formatPayRate(val) {
      if (!val && val !== 0) return '-'
      const num = Number(val)
      if (isNaN(num)) return '-'
      // 数据库存的是小数(0.5689)，乘以100转为百分比
      return (num * 100).toFixed(2) + '%'
    }

    async function loadAllData() {
      dashLoading.value = true
      dashError.value = ''
      try {
        console.log('[Dashboard] 开始加载数据...')
        const [region, product, profile, interaction] = await Promise.all([
          api.getDashboardRegionConsume(),
          api.getDashboardProductFeature(),
          api.getDashboardUserProfile(),
          api.getDashboardInteraction()
        ])

        console.log('[Dashboard] API 响应:', { region, product, profile, interaction })

        regionData.value = region.data || []
        productData.value = product.data || []
        userProfileData.value = profile.data || { age_data: [], gender_data: [], city_data: [] }
        interactionData.value = interaction.data || { trend_data: [], funnel_data: {} }

        console.log('[Dashboard] 解析后的数据:', {
          regionData: regionData.value,
          productData: productData.value,
          userProfileData: userProfileData.value,
          interactionData: interactionData.value
        })

        cities.value = regionData.value.map(r => r.city_name).filter(Boolean)
        if (cities.value.length > 0) {
          currentCity.value = cities.value[0]
          updateCurrentRegionData()
        }

        // 先关闭loading让v-if的DOM容器渲染出来
        dashLoading.value = false
        await nextTick()
        renderAllCharts()
      } catch (err) {
        console.error('[Dashboard] 加载可视化数据失败:', err)
        dashLoading.value = false
        dashError.value = '数据加载失败，请检查后端服务和数据库是否正常运行。错误: ' + (err.message || '未知错误')
      }
    }

    function retryLoad() {
      retryCount.value = 0
      loadAllData()
    }

    function updateCurrentRegionData() {
      const found = regionData.value.find(r => r.city_name === currentCity.value)
      currentRegionData.value = found || null
    }

    function startAgeCycle() {
      const ageData = userProfileData.value?.age_data || []
      ageGroups.value = ageData.map(d => d.age_group).filter(Boolean)
      if (ageGroups.value.length === 0) return
      currentAgeGroup.value = ageGroups.value[0]
      if (ageGroups.value.length <= 1) return
      ageCycleTimer = setInterval(() => {
        ageCycleIndex.value = (ageCycleIndex.value + 1) % ageGroups.value.length
        currentAgeGroup.value = ageGroups.value[ageCycleIndex.value]
        renderUserAge()
      }, 3000)
    }

    function startProductCycle() {
      const data = productData.value || []
      productCategories.value = data.map(d => d.product_category).filter(Boolean)
      if (productCategories.value.length === 0) return
      currentProductCategory.value = productCategories.value[0]
      if (productCategories.value.length <= 1) return
      productCycleTimer = setInterval(() => {
        productCycleIndex.value = (productCycleIndex.value + 1) % productCategories.value.length
        currentProductCategory.value = productCategories.value[productCycleIndex.value]
        renderProductPie()
      }, 3000)
    }

    function startCycle() {
      if (!cities.value || cities.value.length <= 1) return
      cycleTimer = setInterval(() => {
        cycleIndex.value = (cycleIndex.value + 1) % cities.value.length
        currentCity.value = cities.value[cycleIndex.value]
        updateCurrentRegionData()
      }, 3000)
    }

    // ============ ECharts 渲染 ============

    function getOrCreateChart(id) {
      const dom = document.getElementById(id)
      if (!dom) {
        console.warn(`[Dashboard] 图表容器 #${id} 不存在`)
        return null
      }
      if (chartInstances[id]) {
        try {
          chartInstances[id].dispose()
        } catch (e) {
          console.warn(`[Dashboard] 销毁旧图表实例失败:`, e)
        }
      }
      try {
        const chart = echarts.init(dom)
        chartInstances[id] = chart
        return chart
      } catch (e) {
        console.error(`[Dashboard] 初始化图表 #${id} 失败:`, e)
        return null
      }
    }

    // 统一的深色 tooltip 样式
    const darkTooltip = {
      backgroundColor: 'rgba(10, 22, 40, 0.92)',
      borderColor: 'rgba(0, 217, 255, 0.25)',
      borderWidth: 1,
      padding: [10, 14],
      textStyle: { color: '#e2e8f0', fontSize: 13 }
    }

    // 统一的坐标轴线样式
    const axisLineStyle = 'rgba(0, 217, 255, 0.18)'
    const splitLineStyle = 'rgba(0, 217, 255, 0.07)'
    const axisLabelColor = '#6B8594'

    function renderAllCharts() {
      console.log('[Dashboard] 开始渲染图表...')
      try {
        renderCityRanking()
      } catch (e) { console.error('城市排名图渲染失败:', e) }
      try {
        renderProductPie()
      } catch (e) { console.error('商品饼图渲染失败:', e) }
      try {
        renderUserAge()
      } catch (e) { console.error('用户画像渲染失败:', e) }
      try {
        renderFunnel()
      } catch (e) { console.error('漏斗图渲染失败:', e) }
      try {
        renderTrend()
      } catch (e) { console.error('趋势图渲染失败:', e) }
      console.log('[Dashboard] 图表渲染完成')
    }

    function renderCityRanking() {
      const chart = getOrCreateChart('chart-city-ranking')
      if (!chart) return
      const data = regionData.value
      const cityNames = data.map(d => d.city_name)
      const saleAmounts = data.map(d => d.total_sale_amount)

      chart.setOption({
        tooltip: {
          ...darkTooltip,
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: p => `${p[0].name}<br/>销售额：<b>${Number(p[0].value).toLocaleString()}</b> 元`
        },
        grid: { left: '3%', right: '8%', bottom: '8%', top: '8%', containLabel: true },
        xAxis: {
          type: 'category',
          data: cityNames,
          axisLabel: { color: axisLabelColor, fontSize: 11 },
          axisLine: { lineStyle: { color: axisLineStyle } },
          axisTick: { show: false }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            color: axisLabelColor, fontSize: 10,
            formatter: v => v >= 10000 ? (v/10000).toFixed(0) + '万' : v
          },
          splitLine: { lineStyle: { color: splitLineStyle, type: 'dashed' } },
          axisLine: { show: false }
        },
        series: [{
          type: 'bar',
          data: saleAmounts,
          barMaxWidth: 30,
          itemStyle: {
            borderRadius: [5, 5, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#00D9FF' },
              { offset: 1, color: '#1890FF' }
            ])
          },
          emphasis: {
            itemStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: '#22D3EE' },
                { offset: 1, color: '#722ED1' }
              ]),
              shadowBlur: 12,
              shadowColor: 'rgba(0, 217, 255, 0.3)'
            }
          },
          label: { show: true, position: 'top', color: '#00D9FF', fontSize: 10,
            formatter: p => p.value >= 10000 ? (p.value/10000).toFixed(0)+'万' : p.value }
        }],
        animationDuration: 1200,
        animationEasing: 'cubicOut'
      })
    }

    function renderProductPie() {
      const chart = getOrCreateChart('chart-product-pie')
      if (!chart) return
      const data = productData.value || []
      if (data.length === 0) return

      const categoryColors = {
        '数码电子': ['#00D9FF', '#1890FF'],
        '服装服饰': ['#722ED1', '#EB2F96'],
        '美妆护肤': ['#EB2F96', '#FF6B9D'],
        '食品生鲜': ['#52C41A', '#73D13D'],
        '家居家电': ['#FA8C16', '#FFC53D'],
        '图书影音': ['#13C2C2', '#36CFC9'],
        '运动户外': ['#F5222D', '#FF7875'],
        '母婴玩具': ['#722ED1', '#9254DE']
      }
      
      const getCategoryColor = (category, index) => {
        if (categoryColors[category]) {
          return categoryColors[category]
        }
        const fallbackColors = [
          ['#00D9FF', '#1890FF'],
          ['#722ED1', '#EB2F96'],
          ['#52C41A', '#73D13D'],
          ['#FA8C16', '#FFC53D'],
          ['#13C2C2', '#36CFC9'],
          ['#EB2F96', '#FF6B9D']
        ]
        return fallbackColors[index % fallbackColors.length]
      }

      const currentCategory = currentProductCategory.value || data[0]?.product_category
      const currentData = data.find(d => d.product_category === currentCategory) || data[0]
      const currentIndex = data.findIndex(d => d.product_category === currentCategory)
      
      const totalSales = data.reduce((sum, d) => sum + (d.total_sale_amount || 0), 0)
      const percentage = totalSales > 0 ? ((currentData.total_sale_amount / totalSales) * 100) : 0
      
      const rank = currentIndex + 1
      const isChampion = rank === 1

      const colors = getCategoryColor(currentData.product_category, currentIndex)

      const startAngle = 90
      const endAngle = startAngle - (percentage * 3.6)

      chart.setOption({
        tooltip: {
          ...darkTooltip,
          trigger: 'item',
          formatter: function(params) {
            return `${currentData.product_category}<br/>
                    销售额: <b>${Number(currentData.total_sale_amount || 0).toLocaleString()}</b> 元<br/>
                    销量: <b>${Number(currentData.total_sale_quantity || 0).toLocaleString()}</b> 件<br/>
                    占比: <b>${percentage.toFixed(1)}%</b>`
          }
        },
        series: [
          {
            type: 'pie',
            radius: ['60%', '80%'],
            center: ['35%', '50%'],
            startAngle: startAngle,
            endAngle: endAngle,
            data: [{
              value: currentData.total_sale_amount || 0,
              name: currentData.product_category,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
                  { offset: 0, color: colors[0] },
                  { offset: 1, color: colors[1] }
                ])
              }
            }],
            label: { show: false },
            emphasis: {
              itemStyle: { shadowBlur: 25, shadowColor: `${colors[0]}80` }
            }
          },
          {
            type: 'pie',
            radius: ['60%', '80%'],
            center: ['35%', '50%'],
            startAngle: endAngle,
            endAngle: startAngle,
            data: [{
              value: 100,
              name: '',
              itemStyle: { color: 'rgba(30, 58, 95, 0.3)' }
            }],
            label: { show: false },
            emphasis: { disabled: true }
          }
        ],
        graphic: [
          {
            type: 'text',
            right: '5%',
            top: '18%',
            style: {
              text: `${percentage.toFixed(1)}%`,
              fill: colors[0],
              fontSize: 36,
              fontWeight: 'bold'
            }
          },
          {
            type: 'text',
            right: '5%',
            top: '34%',
            style: {
              text: currentData.product_category,
              fill: colors[0],
              fontSize: 16,
              fontWeight: 'bold'
            }
          },
          {
            type: 'text',
            right: '5%',
            top: '45%',
            style: {
              text: isChampion ? '🏆 销量冠军' : `第${rank}名`,
              fill: isChampion ? '#FA8C16' : '#B4C6D7',
              fontSize: 14,
              fontWeight: 'bold'
            }
          },
          {
            type: 'text',
            right: '5%',
            top: '56%',
            style: {
              text: `💰 ${Number(currentData.total_sale_amount || 0).toLocaleString()} 元`,
              fill: colors[0],
              fontSize: 13
            }
          },
          {
            type: 'text',
            right: '5%',
            top: '68%',
            style: {
              text: `📦 ${Number(currentData.total_sale_quantity || 0).toLocaleString()} 件`,
              fill: '#B4C6D7',
              fontSize: 12
            }
          }
        ],
        animationDuration: 800,
        animationEasing: 'cubicOut'
      }, true)
    }

    function renderUserAge() {
      const chart = getOrCreateChart('chart-user-age')
      if (!chart) return
      const data = userProfileData.value.age_data || []
      if (data.length === 0) return

      const currentData = data.find(d => d.age_group === currentAgeGroup.value) || data[0]
      
      const maxConsumption = Math.max(...data.map(d => d.avg_consumption || 0))
      const maxOrderValue = Math.max(...data.map(d => d.avg_order_value || 0))
      const maxRepurchase = Math.max(...data.map(d => d.avg_repurchase || 0))
      
      const indicator = [
        { name: '平均消费(元)', max: maxConsumption * 1.2 },
        { name: '客单价(元)', max: maxOrderValue * 1.2 },
        { name: '复购次数', max: Math.max(maxRepurchase * 1.2, 10) },
        { name: '用户数量', max: Math.max(...data.map(d => d.user_count || 0)) * 1.2 }
      ]
      
      const values = [
        currentData.avg_consumption || 0,
        currentData.avg_order_value || 0,
        currentData.avg_repurchase || 0,
        currentData.user_count || 0
      ]

      chart.setOption({
        tooltip: {
          ...darkTooltip,
          trigger: 'item',
          formatter: function(params) {
            return `${currentData.age_group}消费画像<br/>
                    平均消费: <b>${Number(currentData.avg_consumption || 0).toLocaleString()}</b> 元<br/>
                    客单价: <b>${Number(currentData.avg_order_value || 0).toLocaleString()}</b> 元<br/>
                    复购次数: <b>${currentData.avg_repurchase || 0}</b> 次<br/>
                    用户数量: <b>${currentData.user_count || 0}</b> 人`
          }
        },
        radar: {
          indicator: indicator,
          shape: 'polygon',
          splitNumber: 4,
          center: ['50%', '50%'],
          radius: '65%',
          axisName: {
            color: '#00D9FF',
            fontSize: 11,
            padding: [3, 5]
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(0, 217, 255, 0.15)',
              type: 'dashed'
            }
          },
          splitArea: {
            show: true,
            areaStyle: {
              color: ['rgba(0, 217, 255, 0.02)', 'rgba(0, 217, 255, 0.05)', 'rgba(0, 217, 255, 0.08)', 'rgba(0, 217, 255, 0.12)']
            }
          },
          axisLine: {
            lineStyle: {
              color: 'rgba(0, 217, 255, 0.2)'
            }
          }
        },
        series: [{
          type: 'radar',
          data: [{
            value: values,
            name: currentData.age_group,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: {
              color: '#00D9FF',
              width: 2
            },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 217, 255, 0.5)' },
                { offset: 1, color: 'rgba(0, 217, 255, 0.15)' }
              ])
            },
            itemStyle: {
              color: '#00D9FF',
              borderColor: '#fff',
              borderWidth: 1
            }
          }],
          animationDuration: 800,
          animationEasing: 'cubicOut'
        }],
        graphic: [{
          type: 'text',
          right: '5%',
          top: '8%',
          style: {
            text: `${currentData.age_group}`,
            fill: '#00D9FF',
            fontSize: 16,
            fontWeight: 'bold'
          }
        }]
      }, true)
    }

    // 漏斗流式动画状态
    let funnelAnimStep = 0
    let funnelAnimTimers = []

    function clearFunnelAnimTimers() {
      funnelAnimTimers.forEach(t => clearTimeout(t))
      funnelAnimTimers = []
    }

    function renderFunnel() {
      const chart = getOrCreateChart('chart-funnel')
      if (!chart) return
      const funnel = interactionData.value.funnel_data || {}
      const pv = funnel.total_pv || 0
      const fav = funnel.total_fav || 0
      const cart = funnel.total_cart || 0
      const buy = funnel.total_buy || 0

      const formatRate = (current, previous) => {
        if (!previous || previous === 0) return '100%'
        return ((current / previous) * 100).toFixed(1) + '%'
      }

      // 漏斗数据：从上到下 浏览→收藏→加购→购买
      const funnelLayers = [
        { name: '浏览', value: pv, color: '#1890FF', colorEnd: '#00D9FF' },
        { name: '收藏', value: fav, color: '#722ED1', colorEnd: '#B37FEB' },
        { name: '加购', value: cart, color: '#EB2F96', colorEnd: '#FF85C0' },
        { name: '购买', value: buy, color: '#52C41A', colorEnd: '#95DE64' }
      ]

      // 保存到实例上供循环使用
      chart._funnelLayers = funnelLayers
      chart._funnelMeta = { pv, fav, cart, buy, formatRate }

      // 启动流式动画
      startFunnelFlowAnimation(chart)
    }

    function startFunnelFlowAnimation(chart) {
      clearFunnelAnimTimers()
      funnelAnimStep = 0

      const layers = chart._funnelLayers
      const { pv, fav, cart, buy, formatRate } = chart._funnelMeta
      const layerDelay = 600 // 每层间隔(ms)
      const layerAnimDuration = 800 // 每层动画时长(ms)

      // 先清空图表，准备流式渲染
      chart.setOption({
        series: [{
          type: 'funnel',
          data: [],
          label: { show: false }
        }]
      }, true)

      // 逐层添加数据，形成流式效果
      layers.forEach((layer, index) => {
        const timer = setTimeout(() => {
          const currentData = layers.slice(0, index + 1).map((item, i) => {
            let rate = '100%'
            if (item.name === '收藏') rate = formatRate(fav, pv)
            else if (item.name === '加购') rate = formatRate(cart, fav)
            else if (item.name === '购买') rate = formatRate(buy, cart)

            return {
              name: item.name,
              value: item.value,
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                  { offset: 0, color: item.color },
                  { offset: 1, color: item.colorEnd }
                ]),
                borderColor: 'rgba(0, 217, 255, 0.15)',
                borderWidth: 1,
                shadowBlur: i === index ? 12 : 0,
                shadowColor: i === index ? `${item.color}60` : 'transparent'
              }
            }
          })

          chart.setOption({
            tooltip: {
              ...darkTooltip,
              trigger: 'item',
              formatter: function(params) {
                const name = params.name
                const value = params.value
                let rate = '100%'
                if (name === '收藏') rate = formatRate(fav, pv)
                else if (name === '加购') rate = formatRate(cart, fav)
                else if (name === '购买') rate = formatRate(buy, cart)
                return `${name}<br/>次数：<b>${Number(value).toLocaleString()}</b> 次<br/>转化率：${rate}`
              }
            },
            series: [{
              type: 'funnel',
              left: '5%',
              top: 10,
              bottom: 10,
              width: '55%',
              sort: 'descending',
              gap: 4,
              label: {
                show: true,
                position: 'right',
                formatter: function(params) {
                  const name = params.name
                  let rate = '100%'
                  if (name === '收藏') rate = formatRate(fav, pv)
                  else if (name === '加购') rate = formatRate(cart, fav)
                  else if (name === '购买') rate = formatRate(buy, cart)
                  return `{name|${name}}  {value|${Number(params.value).toLocaleString()}次}  {rate|转化率 ${rate}}`
                },
                rich: {
                  name: {
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#F0F4F8',
                    padding: [0, 0, 0, 0]
                  },
                  value: {
                    fontSize: 12,
                    fontWeight: 500,
                    color: '#A8B8C8',
                    padding: [0, 0, 0, 8]
                  },
                  rate: {
                    fontSize: 11,
                    fontWeight: 500,
                    color: '#00D9FF',
                    padding: [0, 0, 0, 8]
                  }
                },
                lineHeight: 20
              },
              labelLine: {
                show: true,
                lineStyle: {
                  color: 'rgba(0, 217, 255, 0.25)',
                  width: 1
                },
                length: 12,
                length2: 8
              },
              emphasis: {
                label: { fontSize: 13 },
                itemStyle: { shadowBlur: 15, shadowColor: 'rgba(0,217,255,0.4)' }
              },
              data: currentData,
              animationDuration: layerAnimDuration,
              animationEasing: 'cubicOut',
              animationDelay: function(idx) {
                // 最新加入的那一层有入场动画，之前的层保持不动
                return idx === index ? 0 : 0
              }
            }]
          })

          // 最后一层渲染完成后，设置循环定时器
          if (index === layers.length - 1) {
            scheduleFunnelLoop(chart)
          }
        }, index * layerDelay)

        funnelAnimTimers.push(timer)
      })
    }

    function scheduleFunnelLoop(chart) {
      // 等待所有层渲染完毕后，停留一段时间再重新开始
      const loopDelay = 3000 // 完整展示停留时间(ms)

      const loopTimer = setTimeout(() => {
        // 检查图表是否还存在
        if (!chart || chart.isDisposed()) return
        startFunnelFlowAnimation(chart)
      }, loopDelay)

      funnelAnimTimers.push(loopTimer)
    }

    function startFunnelLoop() {
      const chart = chartInstances['chart-funnel']
      if (!chart) return
      startFunnelFlowAnimation(chart)
    }

    function renderTrend() {
      const chart = getOrCreateChart('chart-trend')
      if (!chart) return
      const data = interactionData.value.trend_data || []
      if (data.length === 0) {
        return
      }

      const months = data.map(d => d.stat_month)
      const pvData = data.map(d => d.pv_count)
      const favData = data.map(d => d.fav_count)
      const cartData = data.map(d => d.cart_count)
      const buyData = data.map(d => d.buy_count)

      chart.setOption({
        tooltip: {
          ...darkTooltip,
          trigger: 'axis'
        },
        legend: {
          data: ['浏览', '收藏', '加购', '购买'],
          bottom: 0,
          textStyle: { color: axisLabelColor, fontSize: 11 },
          itemWidth: 16,
          itemHeight: 3
        },
        grid: { left: '3%', right: '5%', bottom: '18%', top: '8%', containLabel: true },
        xAxis: {
          type: 'category',
          data: months,
          boundaryGap: false,
          axisLabel: { color: axisLabelColor, fontSize: 10, rotate: 30 },
          axisLine: { lineStyle: { color: axisLineStyle } },
          axisTick: { show: false }
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: axisLabelColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitLineStyle, type: 'dashed' } },
          axisLine: { show: false }
        },
        series: [
          {
            name: '浏览', type: 'line', data: pvData, smooth: true,
            lineStyle: { width: 2, color: '#00D9FF' },
            itemStyle: { color: '#00D9FF' },
            areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(0, 217, 255, 0.2)' },
              { offset: 1, color: 'rgba(0, 217, 255, 0.01)' }
            ])},
            symbolSize: 5
          },
          {
            name: '收藏', type: 'line', data: favData, smooth: true,
            lineStyle: { width: 2, color: '#722ED1' },
            itemStyle: { color: '#722ED1' },
            symbolSize: 5
          },
          {
            name: '加购', type: 'line', data: cartData, smooth: true,
            lineStyle: { width: 2, color: '#FA8C16' },
            itemStyle: { color: '#FA8C16' },
            symbolSize: 5
          },
          {
            name: '购买', type: 'line', data: buyData, smooth: true,
            lineStyle: { width: 2, color: '#52C41A' },
            itemStyle: { color: '#52C41A' },
            symbolSize: 5
          }
        ],
        animationDuration: 1200
      })
    }

    // 监听城市变化，高亮排名图
    watch(currentCity, () => {
      const chart = chartInstances['chart-city-ranking']
      if (chart && regionData.value.length > 0) {
        const idx = regionData.value.findIndex(r => r.city_name === currentCity.value)
        chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: idx >= 0 ? idx : 0 })
        chart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: idx >= 0 ? idx : 0 })
      }
    })

    onMounted(async () => {
      window.addEventListener('resize', handleResize)
      await loadAllData()
      // 数据加载完成后再启动轮播
      if (!dashError.value) {
        startCycle()
        startAgeCycle()
        startProductCycle()
      }
    })

    onUnmounted(() => {
      if (cycleTimer) clearInterval(cycleTimer)
      if (ageCycleTimer) clearInterval(ageCycleTimer)
      if (productCycleTimer) clearInterval(productCycleTimer)
      clearFunnelAnimTimers()
      window.removeEventListener('resize', handleResize)
      Object.values(chartInstances).forEach(c => c && c.dispose())
    })

    function handleResize() {
      Object.values(chartInstances).forEach(c => c && c.resize())
    }

    return {
      regionData, productData, userProfileData, interactionData,
      cities, cycleIndex, currentCity, currentRegionData,
      ageGroups, ageCycleIndex, currentAgeGroup,
      productCategories, productCycleIndex, currentProductCategory,
      dashLoading, dashError, retryLoad,
      formatNum, formatPayRate
    }
  }
}
</script>

<style scoped>
/* ============================================================================
   DashboardView.vue - 数据可视化大屏样式升级版
   关键词：深空科技 · 发光质感 · 数据呼吸感 · 精致排版
   ============================================================================ */

.dashboard-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-neutral-bg);
  color: var(--color-neutral-text-primary);
  overflow: hidden;
  font-family: var(--font-family-base);
}

/* ===== 顶部标题栏 ===== */
.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-xl);
  height: 48px;
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  flex-shrink: 0;
  position: relative;
}

/* 标题栏底部发光线 */
.dashboard-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.25), rgba(114, 46, 209, 0.15), transparent);
}

.dh-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
}

.dh-icon { 
  font-size: 1.1rem; 
}

.dh-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-s);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 0.02em;
  background: linear-gradient(90deg, #00D9FF, #1890FF, #722ED1);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.dh-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  font-size: var(--font-size-xs);
}

.dh-city-label { 
  color: var(--text-tertiary); 
}

.dh-city-name {
  font-family: var(--font-family-display);
  font-size: var(--font-size-m);
  font-weight: var(--font-weight-bold);
  color: #00D9FF;
  animation: pulseGlow 3s ease-in-out infinite;
}

@keyframes pulseGlow {
  0%, 100% { 
    text-shadow: 0 0 8px rgba(0, 217, 255, 0.2); 
  }
  50% { 
    text-shadow: 0 0 18px rgba(0, 217, 255, 0.5), 0 0 40px rgba(0, 217, 255, 0.15); 
  }
}

.dh-cycle {
  color: var(--text-tertiary);
  font-size: 10px;
  background: rgba(0, 217, 255, 0.06);
  padding: 2px var(--spacing-s);
  border-radius: var(--radius-full);
  border: 1px solid rgba(0, 217, 255, 0.08);
  font-family: var(--font-family-display);
  font-weight: var(--font-weight-medium);
}

/* ===== 主体 ===== */
.dashboard-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-m);
  gap: var(--spacing-m);
  overflow: hidden;
}

.dash-row {
  display: flex;
  gap: var(--spacing-m);
  flex: 1;
  min-height: 0;
}

/* ===== 卡片 ===== */
.dash-card {
  background: var(--color-neutral-surface);
  border: 1px solid var(--color-neutral-border);
  border-radius: var(--radius-m);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-s);
  transition: all var(--transition-spring);
  position: relative;
}

/* 卡片顶部装饰光 */
.dash-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.15), transparent);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.dash-card:hover {
  border-color: rgba(0, 217, 255, 0.2);
  box-shadow: var(--shadow-hover);
  transform: translateY(-1px);
}

.dash-card:hover::before {
  opacity: 1;
}

.card-region-overview { flex: 1.1; }
.card-city-ranking { flex: 0.9; }
.card-product { flex: 1; }
.card-user-age { flex: 1; }
.card-funnel { flex: 1; }
.card-trend { flex: 1; }

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  padding: var(--spacing-m) var(--spacing-l);
  border-bottom: 1px solid var(--color-neutral-border-light);
  flex-shrink: 0;
}

.card-icon { 
  font-size: 0.85rem; 
}

.card-title {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-text-secondary);
  letter-spacing: 0.02em;
}

.card-city-tag {
  margin-left: auto;
  padding: 4px var(--spacing-m);
  border-radius: var(--radius-full);
  background: rgba(0, 217, 255, 0.12);
  color: #00D9FF;
  font-size: 14px;
  font-weight: var(--font-weight-bold);
  font-family: var(--font-family-display);
  border: 1px solid rgba(0, 217, 255, 0.2);
}

.card-body {
  flex: 1;
  padding: var(--spacing-m) var(--spacing-l);
  min-height: 0;
  position: relative;
}

.chart-box {
  width: 100%;
  height: 100%;
  min-height: 80px;
}

/* ===== KPI 网格 ===== */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-m);
  height: 100%;
  align-content: center;
}

.kpi-item {
  text-align: center;
  padding: var(--spacing-m) var(--spacing-s);
  background: var(--color-neutral-bg);
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border-light);
  transition: all var(--transition-spring);
  position: relative;
  overflow: hidden;
}

/* KPI 顶部装饰线 */
.kpi-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 20%;
  right: 20%;
  height: 1px;
  background: var(--color-accent-gradient);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.kpi-item:hover {
  background: rgba(0, 217, 255, 0.04);
  border-color: rgba(0, 217, 255, 0.15);
  transform: translateY(-2px);
}

.kpi-item:hover::before {
  opacity: 1;
}

.kpi-value {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xxl);
  font-weight: var(--font-weight-bold);
  letter-spacing: -0.03em;
  margin-bottom: 2px;
  line-height: 1;
}

/* KPI 颜色 - 发光质感 */
.kpi-primary { color: #00D9FF; text-shadow: 0 0 16px rgba(0, 217, 255, 0.3); }
.kpi-secondary { color: #1890FF; text-shadow: 0 0 16px rgba(24, 144, 255, 0.3); }
.kpi-info { color: #22D3EE; text-shadow: 0 0 16px rgba(34, 211, 238, 0.3); }
.kpi-success { color: #52C41A; text-shadow: 0 0 16px rgba(82, 196, 26, 0.3); }
.kpi-warning { color: #FA8C16; text-shadow: 0 0 16px rgba(250, 140, 22, 0.3); }
.kpi-rose { color: #EB2F96; font-size: var(--font-size-l); text-shadow: 0 0 16px rgba(235, 47, 150, 0.3); }
.kpi-purple { color: #722ED1; text-shadow: 0 0 16px rgba(114, 46, 209, 0.3); }

.kpi-label {
  font-size: 10px;
  color: var(--color-neutral-text-tertiary);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.no-data {
  text-align: center;
  color: var(--color-neutral-text-tertiary);
  padding: var(--spacing-2xl);
  font-size: var(--font-size-xs);
}

/* ===== 加载状态 ===== */
.dashboard-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-l);
  color: var(--color-neutral-text-tertiary);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid rgba(0, 217, 255, 0.1);
  border-top-color: #00D9FF;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ===== 错误状态 ===== */
.dashboard-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-l);
  color: var(--color-neutral-text-tertiary);
}

.error-icon {
  font-size: 2rem;
}

.retry-btn {
  padding: var(--spacing-s) var(--spacing-xl);
  background: rgba(0, 217, 255, 0.06);
  border: 1px solid rgba(0, 217, 255, 0.2);
  color: #00D9FF;
  border-radius: var(--radius-s);
  cursor: pointer;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-spring);
}

.retry-btn:hover {
  background: rgba(0, 217, 255, 0.12);
  border-color: rgba(0, 217, 255, 0.35);
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

/* ===== 响应式 ===== */
@media (max-width: 1400px) {
  .kpi-grid { 
    grid-template-columns: repeat(3, 1fr); 
  }
}

@media (max-width: 1000px) {
  .kpi-grid { 
    grid-template-columns: repeat(2, 1fr); 
  }
}
</style>
