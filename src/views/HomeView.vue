<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <div class="header-logo">
          <span class="header-icon">🌏</span>
        </div>
        <div class="header-text">
          <h1>黔数智析 </h1>
          <p class="header-subtitle">—— 基于本地大模型的区域电商智能可视化分析平台</p>
        </div>
        <div class="header-actions">
          <button 
            class="header-action-btn" 
            @click="showSessionList = true"
            title="对话历史"
          >
            <span>📋</span>
          </button>
          <div class="user-menu" v-if="currentUser">
            <button class="user-badge" @click="toggleUserMenu">
              <div class="user-avatar">
                <img 
                  v-if="currentUser.avatar && currentUser.avatar.startsWith('/uploads/')" 
                  :src="currentUser.avatar" 
                  alt="头像"
                  class="user-avatar-image"
                />
                <span v-else>
                  {{ currentUser.role === 'admin' ? '👑' : '👤' }}
                </span>
              </div>
              <span class="user-name">{{ currentUser.username }}</span>
              <span class="user-menu-arrow" :class="{ 'open': userMenuOpen }">▼</span>
            </button>
            <div class="user-menu-dropdown" v-if="userMenuOpen" @click.stop>
              <div class="user-menu-header">
                <div class="user-menu-avatar">
                  <img 
                    v-if="currentUser.avatar && currentUser.avatar.startsWith('/uploads/')" 
                    :src="currentUser.avatar" 
                    alt="头像"
                    class="user-avatar-image"
                  />
                  <span v-else>
                    {{ currentUser.role === 'admin' ? '👑' : '👤' }}
                  </span>
                </div>
                <div class="user-menu-info">
                  <div class="user-menu-username">{{ currentUser.username }}</div>
                  <div class="user-menu-role">{{ currentUser.role === 'admin' ? '管理员' : '普通用户' }}</div>
                </div>
              </div>
              <div class="user-menu-divider"></div>
              <button class="user-menu-item" @click="openUserProfile">
                <span class="menu-icon">👤</span>
                <span>个人资料</span>
              </button>
              <button class="user-menu-item" @click="openChangePassword">
                <span class="menu-icon">🔒</span>
                <span>修改密码</span>
              </button>
              <div class="user-menu-divider"></div>
              <button class="user-menu-item logout" @click="handleLogout">
                <span class="menu-icon">🚪</span>
                <span>退出登录</span>
              </button>
            </div>
          </div>
          <button
            v-if="isAdmin"
            class="header-action-btn"
            @click="showAdmin = !showAdmin"
            :class="{ active: showAdmin }"
            title="数据围栏"
          >
            <span>🛡️</span>
          </button>
          <button class="header-action-btn logout-btn" @click="handleLogout" title="退出登录">
            <span>🚪</span>
          </button>
        </div>
      </div>
    </header>

    <transition name="slide-down">
      <div class="admin-panel" v-if="showAdmin">
        <div class="admin-header">
          <h3>🏦 数据围栏 & 知识管理后台</h3>
          <button class="admin-close" @click="showAdmin = false">✕</button>
        </div>

        <div class="admin-metrics" v-if="fenceMetrics">
          <div class="metric-card metric-total">
            <div class="metric-icon">📋</div>
            <div class="metric-value">{{ fenceMetrics.total_queries }}</div>
            <div class="metric-label">总查询量</div>
          </div>
          <div class="metric-card metric-success">
            <div class="metric-icon">✅</div>
            <div class="metric-value">{{ fenceMetrics.success_rate }}%</div>
            <div class="metric-label">成功率</div>
          </div>
          <div class="metric-card metric-fallback">
            <div class="metric-icon">🛡️</div>
            <div class="metric-value">{{ fenceMetrics.fallback_rate }}%</div>
            <div class="metric-label">兜底率</div>
          </div>
          <div class="metric-card metric-clarify">
            <div class="metric-icon">💬</div>
            <div class="metric-value">{{ fenceMetrics.clarify_rate }}%</div>
            <div class="metric-label">澄清率</div>
          </div>
        </div>

        <div class="admin-section" v-if="fenceMetrics && fenceMetrics.status_distribution">
          <h4>意图状态分布</h4>
          <div class="status-bars">
            <div class="status-row" v-for="(count, status) in fenceMetrics.status_distribution" :key="status">
              <span class="status-label">{{ statusLabels[status] || status }}</span>
              <div class="status-bar-bg">
                <div
                  class="status-bar-fill"
                  :class="status"
                  :style="{ width: (count / fenceMetrics.total_queries * 100) + '%' }"
                ></div>
              </div>
              <span class="status-count">{{ count }}</span>
            </div>
          </div>
        </div>

        <div class="admin-section" v-if="fenceMetrics && fenceMetrics.top_fallback_questions && fenceMetrics.top_fallback_questions.length > 0">
          <h4>🔴 高频兜底问题 TOP 10</h4>
          <div class="question-list">
            <div class="question-item fallback" v-for="(item, i) in fenceMetrics.top_fallback_questions" :key="i">
              <span class="q-rank">{{ i + 1 }}</span>
              <span class="q-text">{{ item.query_text }}</span>
              <span class="q-count">{{ item.cnt }}次</span>
            </div>
          </div>
        </div>

        <div class="admin-section" v-if="fenceMetrics && fenceMetrics.top_clarify_questions && fenceMetrics.top_clarify_questions.length > 0">
          <h4>🟡 高频澄清问题 TOP 10</h4>
          <div class="question-list">
            <div class="question-item clarify" v-for="(item, i) in fenceMetrics.top_clarify_questions" :key="i">
              <span class="q-rank">{{ i + 1 }}</span>
              <span class="q-text">{{ item.query_text }}</span>
              <span class="q-count">{{ item.cnt }}次</span>
            </div>
          </div>
        </div>

        <div class="admin-section">
          <div class="section-header">
            <h4>📋 审计日志</h4>
            <div class="filter-tabs">
              <button
                v-for="tab in ['all', 'success', 'fallback', 'clarify']"
                :key="tab"
                class="filter-btn"
                :class="{ active: logFilter === tab }"
                @click="loadAuditLogs(tab)"
              >
                {{ tab === 'all' ? '全部' : statusLabels[tab] || tab }}
              </button>
            </div>
          </div>
          <div class="log-table-wrap" v-if="auditLogs.length > 0">
            <table class="log-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>问题</th>
                  <th>意图</th>
                  <th>工具</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in auditLogs" :key="log.id">
                  <td class="log-time">{{ log.created_at }}</td>
                  <td class="log-question" :title="log.query_text">{{ log.query_text }}</td>
                  <td>{{ log.intent }}</td>
                  <td>{{ log.tool_used }}</td>
                  <td>
                    <span class="status-tag" :class="log.status">
                      {{ statusLabels[log.status] || log.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="empty-logs">暂无日志数据</div>
        </div>

        <button class="refresh-btn" @click="refreshAdmin" :disabled="adminLoading">
          {{ adminLoading ? '刷新中...' : '🔄 刷新数据' }}
        </button>
      </div>
    </transition>

    <div class="app-body">
      <div class="dashboard-panel">
        <DashboardView />
      </div>

      <div class="chat-panel">
        <aside class="sidebar" :class="{ 'sidebar-open': sidebarOpen }" v-if="isAdmin">
        <div class="sidebar-header">
          <h2>控制面板</h2>
          <button class="sidebar-close" @click="sidebarOpen = false" v-if="sidebarOpen">✕</button>
        </div>

        <button class="new-session-btn" @click="createNewSession">
          <span class="btn-icon">✏️</span>
          新建会话
        </button>

        <div class="session-list">
          <h3 class="section-title">会话历史</h3>
          <div v-if="sessions.length === 0" class="empty-sessions">
            暂无会话历史
          </div>
          <div
            v-for="session in sessions"
            :key="session.id"
            class="session-item"
            :class="{ active: currentSessionId === session.id }"
          >
            <div class="session-info" @click="loadSession(session.id)">
              <span class="session-icon">📘</span>
              <div class="session-detail">
                <span class="session-name">{{ session.name }}</span>
                <span class="session-meta">{{ session.messageCount }} 条消息</span>
              </div>
            </div>
            <button class="session-delete" @click.stop="deleteSession(session.id)" title="删除会话">
              🗑
            </button>
          </div>
        </div>

        <div class="project-info">
          <h3 class="section-title">项目信息</h3>
          <div class="info-card">
            <p><strong>参赛项目：</strong>全国大学生计算机设计大赛</p>
            <p><strong>赛道：</strong>大数据应用赛道</p>
            <p class="info-features"><strong>核心功能：</strong></p>
            <ol>
              <li>基于应用层数据的精准问答</li>
              <li>经济规律挖掘与分析</li>
              <li>数据来源可溯源</li>
              <li>AI 可视化图表生成</li>
              <li>数据围栏与知识闭环管理</li>
            </ol>
          </div>
        </div>
      </aside>

      <transition name="fade">
        <div class="sidebar-overlay" v-if="sidebarOpen" @click="sidebarOpen = false"></div>
      </transition>

      <main class="chat-area">
        <button v-if="isAdmin" class="sidebar-toggle" @click="sidebarOpen = !sidebarOpen">
          <span v-if="!sidebarOpen">☰</span>
          <span v-else>✕</span>
        </button>

        <transition name="fade">
          <div class="loading-overlay" v-if="isLoading">
            <div class="loading-content">
              <div class="loading-spinner"></div>
              <p>正在加载应用层数据，请稍候...</p>
            </div>
          </div>
        </transition>

        <div class="chat-messages" ref="messagesContainer">
          <div v-if="messages.length === 0" class="welcome-container">
            <div class="welcome-card">
              <div class="welcome-icon">🐳</div>
              <h2>欢迎使用区域电商智能数据分析助手</h2>
              <p>我可以帮您分析贵州电商平台的用户行为、消费数据和商品特征，支持自动生成可视化图表。</p>
              <div class="quick-questions">
                <button
                  v-for="(q, idx) in quickQuestions"
                  :key="idx"
                  class="quick-question-btn"
                  @click="sendQuickQuestion(q)"
                >
                  <span class="qq-icon">{{ qIcons[idx] }}</span>
                  <span>{{ q }}</span>
                </button>
              </div>
            </div>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="chat-message"
            :class="msg.role"
          >
            <div class="message-avatar" :class="msg.role">
              {{ msg.role === 'user' ? '👨‍🎓' : '🐳' }}
            </div>

            <div class="message-bubble" :class="msg.role">
              <div v-if="msg.role === 'assistant' && msg.thinking" class="thinking-section">
                <button
                  class="thinking-toggle"
                  :class="{ 'thinking-active': expandedThinking[index] }"
                  @click="toggleThinking(index)"
                >
                  <span v-if="msg.streaming" class="thinking-indicator">🧠</span>
                  <span v-else class="thinking-indicator">✅</span>
                  {{ expandedThinking[index] ? '收起思考过程 ▲' : '查看思考过程 ▼' }}
                </button>
                <transition name="expand">
                  <div v-if="expandedThinking[index]" class="thinking-content">
                    {{ msg.thinking }}
                  </div>
                </transition>
              </div>

              <div
                v-if="msg.role === 'assistant'"
                class="answer-content"
                :key="'msg-' + index"
                v-html="renderContent(msg.content, index)"
              ></div>
              <div v-else class="answer-content">{{ msg.content }}</div>

              <span v-if="msg.streaming" class="typing-cursor">|</span>
            </div>
          </div>

          <transition name="fade">
            <div v-if="isThinking" class="chat-message assistant">
              <div class="message-avatar assistant">🐳</div>
              <div class="message-bubble assistant thinking-bubble">
                <div class="thinking-anim">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
                <span class="thinking-text">AI 正在分析您的问题...</span>
              </div>
            </div>
          </transition>
        </div>

        <div class="chat-input-area">
          <div class="input-container">
            <input
              type="text"
              class="chat-input"
              v-model="inputText"
              @keydown.enter="sendMessage"
              placeholder="请输入你的数据分析问题..."
              :disabled="isLoading || isStreaming"
            />
            <button
              class="send-btn"
              @click="sendMessage"
              :disabled="!inputText.trim() || isLoading || isStreaming"
            >
              <span class="send-icon">↑</span>
            </button>
          </div>
          <p class="input-hint">按 Enter 发送 · 支持查询贵州各城市电商消费、用户行为、商品分析</p>
        </div>
      </main>
      </div>
    </div>
  </div>

  <!-- 个人资料模态框 -->
  <div class="modal-overlay" v-if="showUserProfile" @click="showUserProfile = false">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>👤 个人资料</h3>
        <button class="modal-close" @click="showUserProfile = false">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input
            type="text"
            v-model="profileForm.username"
            class="form-input"
            placeholder="请输入用户名"
            maxlength="20"
          />
        </div>
        <div class="form-group">
          <label class="form-label">头像</label>
          <div class="avatar-selector">
            <button 
              v-for="avatar in ['👤', '👑', '🌟', '🔥', '💎', '🚀']"
              :key="avatar"
              class="avatar-option"
              :class="{ active: profileForm.avatar === avatar }"
              @click="profileForm.avatar = avatar"
            >
              {{ avatar }}
            </button>
          </div>
          <div class="avatar-upload">
            <input 
              type="file" 
              id="avatar-upload" 
              class="avatar-upload-input"
              accept="image/*"
              @change="handleAvatarUpload"
            />
            <label for="avatar-upload" class="avatar-upload-label">
              📁 上传自定义头像
            </label>
          </div>
        </div>
        <div v-if="profileError" class="form-error">{{ profileError }}</div>
        <div v-if="profileSuccess" class="form-success">{{ profileSuccess }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="showUserProfile = false">取消</button>
        <button 
          class="btn btn-primary" 
          @click="updateProfile"
          :disabled="profileLoading"
        >
          {{ profileLoading ? '更新中...' : '更新资料' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 修改密码模态框 -->
  <div class="modal-overlay" v-if="showChangePassword" @click="showChangePassword = false">
    <div class="modal-content" @click.stop>
      <div class="modal-header">
        <h3>🔒 修改密码</h3>
        <button class="modal-close" @click="showChangePassword = false">✕</button>
      </div>
      <div class="modal-body">
        <div class="form-group">
          <label class="form-label">原密码</label>
          <input
            type="password"
            v-model="passwordForm.oldPassword"
            class="form-input"
            placeholder="请输入原密码"
          />
        </div>
        <div class="form-group">
          <label class="form-label">新密码</label>
          <input
            type="password"
            v-model="passwordForm.newPassword"
            class="form-input"
            placeholder="请输入新密码（至少6个字符）"
          />
        </div>
        <div class="form-group">
          <label class="form-label">确认新密码</label>
          <input
            type="password"
            v-model="passwordForm.confirmPassword"
            class="form-input"
            placeholder="请再次输入新密码"
          />
        </div>
        <div v-if="passwordError" class="form-error">{{ passwordError }}</div>
        <div v-if="passwordSuccess" class="form-success">{{ passwordSuccess }}</div>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" @click="showChangePassword = false">取消</button>
        <button 
          class="btn btn-primary" 
          @click="changePassword"
          :disabled="passwordLoading"
        >
          {{ passwordLoading ? '修改中...' : '修改密码' }}
        </button>
      </div>
    </div>
  </div>

  <!-- 会话历史弹窗 -->
  <div class="modal-overlay" v-if="showSessionList" @click="showSessionList = false">
    <div class="session-list-modal" @click.stop>
      <div class="modal-header">
        <h3>📋 对话历史</h3>
        <button class="modal-close" @click="showSessionList = false">✕</button>
      </div>
      <div class="session-list-body">
        <button class="new-session-btn-popup" @click="createNewSessionFromPopup">
          <span class="btn-icon">✏️</span>
          新建会话
        </button>
        <div class="session-list-container">
          <div v-if="sessions.length === 0" class="empty-sessions-popup">
            暂无对话历史
          </div>
          <div
            v-for="session in sessions"
            :key="session.id"
            class="session-item-popup"
            :class="{ active: currentSessionId === session.id }"
          >
            <div class="session-info-popup" @click="selectSession(session.id)">
              <span class="session-icon">📘</span>
              <div class="session-detail-popup">
                <span class="session-name-popup">{{ session.name }}</span>
                <span class="session-meta-popup">{{ session.messageCount }} 条消息</span>
              </div>
            </div>
            <button class="session-delete-popup" @click.stop="deleteSession(session.id)" title="删除会话">
              🗑
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, nextTick, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import * as echarts from 'echarts'
import api from '../api'
import DashboardView from '../DashboardView.vue'

const CHART_COLORS = ['#00D9FF', '#1890FF', '#722ED1', '#EB2F96', '#FA8C16', '#52C41A']
const MAX_MESSAGES = 50

export default {
  name: 'HomeView',
  components: { DashboardView },
  setup() {
    const router = useRouter()

    const currentUser = ref(null)
    const isAdmin = computed(() => currentUser.value && currentUser.value.role === 'admin')

    // 用户菜单状态
    const userMenuOpen = ref(false)
    const showUserProfile = ref(false)
    const showChangePassword = ref(false)

    // 个人资料表单
    const profileForm = reactive({
      username: '',
      avatar: ''
    })

    // 修改密码表单
    const passwordForm = reactive({
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    })

    // 表单状态
    const profileLoading = ref(false)
    const passwordLoading = ref(false)
    const profileError = ref('')
    const passwordError = ref('')
    const profileSuccess = ref('')
    const passwordSuccess = ref('')

    const messages = ref([])
    const inputText = ref('')
    const isLoading = ref(true)
    const isThinking = ref(false)
    const isStreaming = ref(false)
    const sidebarOpen = ref(false)
    const showSessionList = ref(false)
    const messagesContainer = ref(null)
    const currentSessionId = ref(null)
    const sessions = ref([])
    const expandedThinking = reactive({})

    const showAdmin = ref(false)
    const fenceMetrics = ref(null)
    const auditLogs = ref([])
    const logFilter = ref('all')
    const adminLoading = ref(false)

    const chartInstanceMap = new Map()
    let currentAbortController = null

    const statusLabels = {
      success: '成功',
      fallback: '兜底',
      clarify: '澄清'
    }

    const quickQuestions = [
      '贵州区域消费分析',
      '为什么贵阳的消费这么高？',
      '各品类的销量、销售额、转化率雷达图',
      '生成一个展示商品品类销售额占比的饼图。',
      '贵州各城市的平均客单价是多少？生成柱形图',
      '生成一个展示遵义月度用户行为趋势的折线图',
      '哪些城市的消费增长潜力最大？结合用户规模和客单价分析。',
      '如果要在贵州新增一个商品品类，你会推荐什么？基于现有数据分析。',
      '影响用户购买决策的关键因素有哪些？从用户行为数据中分析。',
    ]

    const qIcons = ['🔍', '📊', '📱', '📀', '📊', '📑','🏆','🧮','🙋‍♂️']

    function initUser() {
      const userStr = localStorage.getItem('user') || sessionStorage.getItem('user')
      if (userStr) {
        try {
          currentUser.value = JSON.parse(userStr)
        } catch (e) {
          currentUser.value = null
        }
      }
    }

    function handleLogout() {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      sessionStorage.removeItem('token')
      sessionStorage.removeItem('user')
      currentUser.value = null
      router.push('/login')
    }

    function toggleUserMenu() {
      userMenuOpen.value = !userMenuOpen.value
    }

    function openUserProfile() {
      userMenuOpen.value = false
      profileForm.username = currentUser.value.username
      profileForm.avatar = currentUser.value.role === 'admin' ? '👑' : '👤'
      profileError.value = ''
      profileSuccess.value = ''
      showUserProfile.value = true
    }

    function openChangePassword() {
      userMenuOpen.value = false
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
      passwordError.value = ''
      passwordSuccess.value = ''
      showChangePassword.value = true
    }

    async function handleAvatarUpload(event) {
      const file = event.target.files[0]
      if (!file) return

      // 验证文件类型
      const allowedExtensions = ['png', 'jpg', 'jpeg', 'webp']
      const fileExtension = file.name.split('.').pop().toLowerCase()
      if (!allowedExtensions.includes(fileExtension)) {
        profileError.value = '只支持上传png、jpg、jpeg、webp格式的图片'
        return
      }

      // 验证文件大小（2MB）
      if (file.size > 2 * 1024 * 1024) {
        profileError.value = '头像文件大小不能超过2MB'
        return
      }

      profileLoading.value = true
      profileError.value = ''
      profileSuccess.value = ''

      try {
        const res = await api.uploadAvatar(file)
        if (res.code === 200) {
          // 更新用户信息中的头像
          currentUser.value.avatar = res.data.avatar_url
          const storage = localStorage.getItem('token') ? localStorage : sessionStorage
          storage.setItem('user', JSON.stringify(currentUser.value))
          profileSuccess.value = '头像上传成功'
        } else {
          profileError.value = res.message || '上传失败'
        }
      } catch (err) {
        if (err.response && err.response.data) {
          profileError.value = err.response.data.message || '上传失败'
        } else {
          profileError.value = '网络错误，请检查后端服务'
        }
      } finally {
        profileLoading.value = false
        // 清空文件输入，允许重复选择同一文件
        event.target.value = ''
      }
    }

    async function updateProfile() {
      if (!profileForm.username.trim()) {
        profileError.value = '用户名不能为空'
        return
      }
      if (profileForm.username.length < 3 || profileForm.username.length > 20) {
        profileError.value = '用户名长度需在3-20个字符之间'
        return
      }

      profileLoading.value = true
      profileError.value = ''
      profileSuccess.value = ''

      try {
        const res = await api.updateProfile({
          username: profileForm.username
        })
        if (res.code === 200) {
          currentUser.value.username = res.data.username
          const storage = localStorage.getItem('token') ? localStorage : sessionStorage
          storage.setItem('user', JSON.stringify(currentUser.value))
          profileSuccess.value = '个人资料更新成功'
          setTimeout(() => {
            showUserProfile.value = false
          }, 1500)
        } else {
          profileError.value = res.message || '更新失败'
        }
      } catch (err) {
        if (err.response && err.response.data) {
          profileError.value = err.response.data.message || '更新失败'
        } else {
          profileError.value = '网络错误，请检查后端服务'
        }
      } finally {
        profileLoading.value = false
      }
    }

    async function changePassword() {
      if (!passwordForm.oldPassword) {
        passwordError.value = '原密码不能为空'
        return
      }
      if (!passwordForm.newPassword) {
        passwordError.value = '新密码不能为空'
        return
      }
      if (passwordForm.newPassword.length < 6) {
        passwordError.value = '新密码长度不能少于6个字符'
        return
      }
      if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        passwordError.value = '两次输入的密码不一致'
        return
      }

      passwordLoading.value = true
      passwordError.value = ''
      passwordSuccess.value = ''

      try {
        const res = await api.changePassword({
          old_password: passwordForm.oldPassword,
          new_password: passwordForm.newPassword
        })
        if (res.code === 200) {
          passwordSuccess.value = '密码修改成功'
          setTimeout(() => {
            showChangePassword.value = false
          }, 1500)
        } else {
          passwordError.value = res.message || '修改失败'
        }
      } catch (err) {
        if (err.response && err.response.data) {
          passwordError.value = err.response.data.message || '修改失败'
        } else {
          passwordError.value = '网络错误，请检查后端服务'
        }
      } finally {
        passwordLoading.value = false
      }
    }

    onMounted(async () => {
      initUser()
      try {
        await api.checkStatus()
        isLoading.value = false
      } catch (err) {
        isLoading.value = false
        console.error('后端连接失败:', err)
      }
      if (isAdmin.value) {
        loadSessions()
      }

      // 点击外部关闭菜单
      document.addEventListener('click', handleClickOutside)
    })

    onUnmounted(() => {
      if (currentAbortController) {
        currentAbortController.abort()
        currentAbortController = null
      }
      disposeAllChartInstances()
      document.removeEventListener('click', handleClickOutside)
    })

    function handleClickOutside(event) {
      const userMenu = document.querySelector('.user-menu')
      if (userMenu && !userMenu.contains(event.target)) {
        userMenuOpen.value = false
      }
    }

    watch(showAdmin, (val) => {
      if (val) refreshAdmin()
    })

    function disposeChartInstance(containerId) {
      if (chartInstanceMap.has(containerId)) {
        const entry = chartInstanceMap.get(containerId)
        entry.resizeObserver.disconnect()
        entry.instance.dispose()
        chartInstanceMap.delete(containerId)
      }
    }

    function disposeAllChartInstances() {
      for (const [containerId, entry] of chartInstanceMap) {
        entry.resizeObserver.disconnect()
        entry.instance.dispose()
      }
      chartInstanceMap.clear()
    }

    onUnmounted(() => {
      if (currentAbortController) {
        currentAbortController.abort()
        currentAbortController = null
      }
      disposeAllChartInstances()
    })

    function scrollToBottom() {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTo({
            top: messagesContainer.value.scrollHeight,
            behavior: 'smooth'
          })
        }
      })
    }

    function isChartConfig(obj) {
      if (!obj || typeof obj !== 'object') return false
      if (obj.type && ['bar', 'line', 'pie', 'scatter', 'radar'].includes(obj.type)) return true
      if (obj.type === 'radar' && obj.indicators) return true
      if ((obj.xAxis || obj.yAxis || obj.data) && !Array.isArray(obj)) return true
      return false
    }

    function extractJsonByBrackets(text, startIdx, openChar, closeChar) {
      let depth = 0
      let inString = false
      let escape = false
      for (let i = startIdx; i < text.length; i++) {
        const ch = text[i]
        if (escape) { escape = false; continue }
        if (ch === '\\') { escape = true; continue }
        if (ch === '"') { inString = !inString; continue }
        if (inString) continue
        if (ch === '[' || ch === '{') depth++
        else if (ch === ']' || ch === '}') {
          depth--
          if (depth === 0 && ch === closeChar) {
            return i + 1
          }
        }
      }
      return -1
    }

    function extractBareJsonArray(text) {
      const markers = [
        '[{"value":',
        '"data": [',
        '"data":[',
        '[{"name":'
      ]
      
      for (const marker of markers) {
        const idx = text.indexOf(marker)
        if (idx === -1) continue

        const arrayStart = text.indexOf('[', idx)
        if (arrayStart === -1) continue

        const endIdx = extractJsonByBrackets(text, arrayStart, '[', ']')
        if (endIdx === -1) continue

        try {
          const candidate = text.substring(arrayStart, endIdx)
          const arr = JSON.parse(candidate)
          if (Array.isArray(arr) && arr.length > 0) {
            return { arr, startIndex: arrayStart, endIndex: endIdx }
          }
        } catch (e) {
          continue
        }
      }
      return null
    }

    function extractBareChartObject(text) {
      const markers = [
        '{"type":"bar"',
        '{"type":"line"',
        '{"type":"pie"',
        '{"type":"scatter"',
        '{"type":"radar"',
        '{"type": "bar"',
        '{"type": "line"',
        '{"type": "pie"',
        '{"type": "scatter"',
        '{"type": "radar"',
      ]

      for (const marker of markers) {
        const idx = text.indexOf(marker)
        if (idx === -1) continue

        const endIdx = extractJsonByBrackets(text, idx, '{', '}')
        if (endIdx === -1) continue

        try {
          const candidate = text.substring(idx, endIdx)
          const obj = JSON.parse(candidate)
          if (isChartConfig(obj)) {
            return { obj, startIndex: idx, endIndex: endIdx }
          }
        } catch (e) {
          continue
        }
      }
      return null
    }

    function tryFixBareChartJson(arr) {
      if (!Array.isArray(arr) || arr.length === 0) return null
      const first = arr[0]
      if (!first || typeof first !== 'object' || !Array.isArray(first.value) || !first.name) return null

      const valueLen = arr[0].value.length
      if (valueLen === 0) return null

      const dimNames = []
      if (valueLen >= 1) dimNames.push('销量')
      if (valueLen >= 2) dimNames.push('销售额')
      if (valueLen >= 3) dimNames.push('转化率')
      if (valueLen > 3) {
        for (let i = 3; i < valueLen; i++) {
          dimNames.push(`指标${i + 1}`)
        }
      }

      const dimValues = Array.from({ length: valueLen }, () => [])
      arr.forEach(item => {
        item.value.forEach((v, i) => { if (i < valueLen) dimValues[i].push(v) })
      })

      const indicators = dimValues.map((vals, idx) => ({
        name: dimNames[idx] || `指标${idx + 1}`,
        max: Math.max(...vals) * 1.2 || 1
      }))

      return {
        type: 'radar',
        title: '多维度数据分析',
        indicators: indicators,
        data: arr.map(item => ({
          value: item.value,
          name: item.name
        }))
      }
    }

    function renderContent(text, msgIndex) {
      if (!text) return ''

      let chartSeq = 0

      let processed = text.replace(/```chart\s*\n([\s\S]*?)```/g, (match, jsonStr) => {
        try {
          const chartConfig = JSON.parse(jsonStr.trim())
          const chartId = `msg-${msgIndex}-chart-${chartSeq++}`
          return `<div id="${chartId}" class="ai-chart-container" style="width:100%;height:340px;margin:16px 0;border-radius:12px;"></div>`
        } catch (e) {
          console.warn('图表JSON解析失败:', e)
          return `<div class="chart-error">⚠️ 图表数据解析失败</div>`
        }
      })

      processed = processed.replace(/```(?:json)?\s*\n([\s\S]*?)```/g, (match, jsonStr) => {
        const trimmed = jsonStr.trim()
        try {
          const parsed = JSON.parse(trimmed)
          if (isChartConfig(parsed)) {
            const chartId = `msg-${msgIndex}-chart-${chartSeq++}`
            return `<div id="${chartId}" class="ai-chart-container" data-bare-chart='${JSON.stringify(parsed)}' style="width:100%;height:340px;margin:16px 0;border-radius:12px;"></div>`
          }
        } catch (e) {}
        return match
      })

      const bareObjResult = extractBareChartObject(processed)
      if (bareObjResult) {
        const chartId = `msg-${msgIndex}-chart-${chartSeq++}`
        const placeholder = `<div id="${chartId}" class="ai-chart-container" data-bare-chart='${JSON.stringify(bareObjResult.obj)}' style="width:100%;height:340px;margin:16px 0;border-radius:12px;"></div>`
        processed = processed.substring(0, bareObjResult.startIndex) + placeholder + processed.substring(bareObjResult.endIndex)
      }

      const bareResult = extractBareJsonArray(processed)
      if (bareResult) {
        const fixed = tryFixBareChartJson(bareResult.arr)
        if (fixed) {
          const chartId = `msg-${msgIndex}-chart-${chartSeq++}`
          const placeholder = `<div id="${chartId}" class="ai-chart-container" data-bare-chart='${JSON.stringify(fixed)}' style="width:100%;height:340px;margin:16px 0;border-radius:12px;"></div>`
          processed = processed.substring(0, bareResult.startIndex) + placeholder + processed.substring(bareResult.endIndex)
        }
      }

      processed = processed.replace(/```chart\s*\n([\s\S]*)$/g, (match, partialJson) => {
        return `<div class="chart-loading" style="padding:14px;text-align:center;color:#6B8594;font-size:0.88rem;">📊 图表生成中...</div>`
      })

      return marked.parse(processed)
    }

    function renderChart(containerId, config) {
      const container = document.getElementById(containerId)
      if (!container) return
      doRenderChart(container, config)
    }

    function doRenderChart(container, config) {
      if (!container) return

      const containerId = container.id
      disposeChartInstance(containerId)

      const chart = echarts.init(container)

      const colorSchemes = {
        primary: CHART_COLORS,
        business: ['#1890FF', '#722ED1', '#EB2F96', '#FA8C16', '#52C41A', '#00D9FF'],
        vibrant: ['#00D9FF', '#1890FF', '#722ED1', '#EB2F96', '#FA8C16', '#52C41A', '#22D3EE']
      }
      const colors = colorSchemes.primary

      let option = {}

      const baseConfig = {
        title: {
          text: config.title || '数据可视化图表',
          left: 'center',
          top: 10,
          textStyle: { fontSize: 15, fontWeight: 600, color: '#B4C6D7' }
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(10, 22, 40, 0.92)',
          borderColor: 'rgba(0, 217, 255, 0.2)',
          textStyle: { color: '#e2e8f0' },
          formatter: function(params) {
            if (config.type === 'pie') return '{b}: {c} ({d}%)'
            let result = params[0].name + '<br/>'
            for (let i = 0; i < params.length; i++) {
              const item = params[i]
              const value = typeof item.value === 'number' ? item.value.toLocaleString() : item.value
              const seriesName = item.seriesName || '数据'
              result += `${item.marker} ${seriesName}: ${value}<br/>`
            }
            return result
          }
        },
        color: colors,
        grid: { left: '3%', right: '4%', bottom: '12%', top: '18%', containLabel: true },
        animation: true,
        animationDuration: 1000,
        animationEasing: 'cubicOut'
      }

      if (config.type === 'pie') {
        let pieData = config.yAxis || config.data || []
        if (Array.isArray(pieData) && pieData.length > 0) {
          if (typeof pieData[0] === 'object' && pieData[0] !== null && ('name' in pieData[0]) && ('value' in pieData[0])) {
          } else if (typeof pieData[0] === 'number') {
            const names = config.xAxis || pieData.map((_, i) => `类别${i + 1}`)
            pieData = names.map((name, i) => ({ name: String(name), value: pieData[i] || 0 }))
          } else if (typeof pieData[0] === 'string') {
            pieData = pieData.map((s, i) => ({ name: String(s), value: 0 }))
          }
        }
        pieData = pieData.filter(item => item.value > 0)

        option = {
          ...baseConfig,
          tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)',
            backgroundColor: 'rgba(10, 22, 40, 0.92)',
            borderColor: 'rgba(0, 217, 255, 0.2)',
            textStyle: { color: '#e2e8f0' }
          },
          legend: { orient: 'horizontal', bottom: 0, textStyle: { fontSize: 12, color: '#B4C6D7' } },
          series: [{
            type: 'pie',
            radius: ['30%', '60%'],
            center: ['50%', '50%'],
            data: pieData,
            emphasis: {
              itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.3)' },
              label: { show: true, fontSize: 14, fontWeight: 'bold' }
            },
            label: {
              formatter: '{b}\n{d}%',
              fontSize: 11,
              color: '#B4C6D7'
            },
            animationType: 'scale',
            animationEasing: 'elasticOut',
            itemStyle: {
              borderRadius: 4,
              borderColor: '#1E3A5F',
              borderWidth: 2
            }
          }]
        }
      } else if (config.type === 'line') {
        option = {
          ...baseConfig,
          xAxis: {
            type: 'category',
            data: config.xAxis || [],
            axisLabel: {
              rotate: config.xAxis && config.xAxis.length > 6 ? 25 : 0,
              fontSize: 11,
              color: '#6B8594'
            },
            axisLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.15)' } },
            axisTick: { show: false },
          },
          yAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.06)', type: 'dashed' } },
            axisLine: { show: false },
            axisLabel: { color: '#6B8594' }
          },
          series: [{
            type: 'line',
            data: config.yAxis || [],
            smooth: true,
            areaStyle: {
              color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: 'rgba(0, 217, 255, 0.2)' },
                  { offset: 1, color: 'rgba(0, 217, 255, 0.01)' },
                ]
              }
            },
            lineStyle: { width: 2.5 },
            symbol: 'circle',
            symbolSize: 6,
            animationDuration: 1200,
            animationEasing: 'cubicOut',
            markPoint: config.showMarkPoint ? {
              data: [
                { type: 'max', name: '最大值' },
                { type: 'min', name: '最小值' }
              ]
            } : undefined,
            markLine: config.showMarkLine ? {
              data: [{ type: 'average', name: '平均值' }]
            } : undefined
          }]
        }
      } else if (config.type === 'scatter') {
        option = {
          ...baseConfig,
          xAxis: {
            type: 'value',
            scale: true,
            axisLabel: { color: '#6B8594' },
            axisLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.15)' } },
            splitLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.06)', type: 'dashed' } }
          },
          yAxis: {
            type: 'value',
            scale: true,
            axisLabel: { color: '#6B8594' },
            axisLine: { show: false },
            splitLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.06)', type: 'dashed' } }
          },
          series: [{
            type: 'scatter',
            data: config.data || config.yAxis || [],
            symbolSize: function(data) {
              return Math.sqrt(data[2]) || 10
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            },
            itemStyle: {
              opacity: 0.8
            }
          }]
        }
      } else if (config.type === 'radar') {
        option = {
          ...baseConfig,
          tooltip: { trigger: 'item' },
          radar: {
            indicator: config.indicators || [],
            shape: 'circle',
            splitNumber: 5,
            axisName: {
              color: '#6B8594',
              fontSize: 12
            },
            splitLine: {
              lineStyle: {
                color: ['rgba(0, 217, 255, 0.18)', 'rgba(0, 217, 255, 0.12)', 'rgba(0, 217, 255, 0.06)']
              }
            },
            splitArea: {
              areaStyle: {
                color: ['rgba(0, 217, 255, 0.06)', 'rgba(0, 217, 255, 0.03)', 'rgba(0, 217, 255, 0.01)']
              }
            }
          },
          series: [{
            type: 'radar',
            data: config.data || config.yAxis || [],
            symbolSize: 4,
            lineStyle: {
              width: 2
            },
            areaStyle: {
              opacity: 0.3
            },
            label: {
              show: false
            }
          }]
        }
      } else {
        option = {
          ...baseConfig,
          xAxis: {
            type: 'category',
            data: config.xAxis || [],
            axisLabel: {
              rotate: config.xAxis && config.xAxis.length > 6 ? 25 : 0,
              fontSize: 11,
              color: '#6B8594'
            },
            axisLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.15)' } },
            axisTick: { show: false },
          },
          yAxis: {
            type: 'value',
            splitLine: { lineStyle: { color: 'rgba(0, 217, 255, 0.06)', type: 'dashed' } },
            axisLine: { show: false },
            axisLabel: { color: '#6B8594' }
          },
          series: [{
            type: 'bar',
            data: config.yAxis || [],
            barMaxWidth: 40,
            itemStyle: {
              borderRadius: [6, 6, 0, 0],
              color: {
                type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: '#00D9FF' },
                  { offset: 1, color: '#1890FF' },
                ]
              }
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.3)'
              }
            },
            label: {
              show: config.showLabel || false,
              position: 'top',
              color: '#B4C6D7',
              fontSize: 11
            },
            animationDuration: 800,
            animationEasing: 'cubicOut',
          }]
        }
      }

      chart.setOption(option)

      const ro = new ResizeObserver(() => chart.resize())
      ro.observe(container)

      chartInstanceMap.set(containerId, { instance: chart, resizeObserver: ro })
    }

    function toggleThinking(index) {
      expandedThinking[index] = !expandedThinking[index]
    }

    function sendQuickQuestion(q) {
      inputText.value = q
      sendMessage()
    }

    async function sendMessage() {
      const question = inputText.value.trim()
      if (!question || isStreaming.value || isLoading.value) return

      messages.value.push({
        role: 'user',
        content: question
      })
      inputText.value = ''
      scrollToBottom()

      const aiMessage = reactive({
        role: 'assistant',
        content: '',
        thinking: '',
        streaming: true
      })
      messages.value.push(aiMessage)
      const aiMsgIndex = messages.value.length - 1
      isStreaming.value = true

      if (currentAbortController) {
        currentAbortController.abort()
      }
      currentAbortController = new AbortController()

      try {
        await api.streamAsk(question, (event) => {
          if (event.type === 'thinking_start') {
            isThinking.value = true
          } else if (event.type === 'thinking_content') {
            aiMessage.thinking = event.content
            if (!expandedThinking[aiMsgIndex]) {
              expandedThinking[aiMsgIndex] = true
            }
            scrollToBottom()
          } else if (event.type === 'thinking_end') {
            isThinking.value = false
            expandedThinking[aiMsgIndex] = false
          } else if (event.type === 'content') {
            aiMessage.content += event.content
            scrollToBottom()
          } else if (event.type === 'error') {
            aiMessage.content += (aiMessage.content ? '\n\n' : '') + '⚠️ ' + (event.content || '处理请求时出错')
            aiMessage.streaming = false
            isStreaming.value = false
            isThinking.value = false
            scrollToBottom()
            autoSaveSession()
          } else if (event.type === 'done') {
            aiMessage.streaming = false
            isStreaming.value = false
            currentAbortController = null
            scrollToBottom()
            nextTick(() => {
              renderChartsForMessage(aiMsgIndex)
            })
            trimMessages()
            autoSaveSession()
          }
        }, currentAbortController.signal)
      } catch (err) {
        if (err.name === 'AbortError') return
        aiMessage.content = '抱歉，连接后端服务失败，请确保后端服务已启动。'
        aiMessage.streaming = false
        isStreaming.value = false
        isThinking.value = false
        currentAbortController = null
        console.error('请求失败:', err)
      }
    }

    function renderChartsForMessage(msgIndex) {
      nextTick(() => {
        const msgEl = messagesContainer.value
        if (!msgEl) return

        const allMsgDivs = msgEl.querySelectorAll('.chat-message')
        const targetMsgDiv = allMsgDivs[msgIndex]
        if (!targetMsgDiv) return

        const chartContainers = targetMsgDiv.querySelectorAll('.ai-chart-container')
        const msg = messages.value[msgIndex]
        if (!msg || !msg.content) return

        const configs = []
        const chartBlockRegex = /```chart\s*\n([\s\S]*?)```/g
        let m
        while ((m = chartBlockRegex.exec(msg.content)) !== null) {
          try {
            configs.push(JSON.parse(m[1].trim()))
          } catch (e) {
            console.warn('图表JSON解析失败:', e)
          }
        }

        const jsonBlockRegex = /```json\s*\n([\s\S]*?)```/g
        while ((m = jsonBlockRegex.exec(msg.content)) !== null) {
          try {
            const parsed = JSON.parse(m[1].trim())
            if (isChartConfig(parsed)) {
              configs.push(parsed)
            }
          } catch (e) {}
        }

        if (configs.length < chartContainers.length) {
          for (const container of chartContainers) {
            const bareAttr = container.getAttribute('data-bare-chart')
            if (bareAttr) {
              try {
                configs.push(JSON.parse(bareAttr))
              } catch (e) {
                console.warn('裸图表JSON解析失败:', e)
              }
            }
          }
        }

        for (let i = 0; i < chartContainers.length && i < configs.length; i++) {
          const container = chartContainers[i]
          if (!chartInstanceMap.has(container.id)) {
            doRenderChart(container, configs[i])
          }
        }
      })
    }

    function trimMessages() {
      if (messages.value.length <= MAX_MESSAGES) return
      const removed = messages.value.splice(0, messages.value.length - MAX_MESSAGES)
      disposeAllChartInstances()
      for (let i = 0; i < messages.value.length; i++) {
        renderChartsForMessage(i)
      }
    }

    function createNewSession() {
      if (messages.value.length > 0) {
        saveSession()
      }
      disposeAllChartInstances()
      messages.value = []
      currentSessionId.value = null
      sidebarOpen.value = false
    }

    async function saveSession() {
      if (messages.value.length === 0) return
      const sessionData = {
        messages: messages.value.map(m => ({
          role: m.role,
          content: m.content,
          thinking: m.thinking || ''
        }))
      }
      try {
        if (currentSessionId.value) {
          await api.updateSession(currentSessionId.value, sessionData)
        } else {
          const res = await api.createSession(sessionData)
          currentSessionId.value = res.id
          loadSessions()
        }
      } catch (err) {
        saveToLocal()
      }
    }

    let saveTimer = null
    function autoSaveSession() {
      if (saveTimer) clearTimeout(saveTimer)
      saveTimer = setTimeout(() => {
        saveSession()
      }, 2000)
    }

    function saveToLocal() {
      const data = {
        messages: messages.value,
        timestamp: new Date().toISOString()
      }
      localStorage.setItem('current_chat', JSON.stringify(data))
    }

    async function loadSessions() {
      try {
        const res = await api.getSessions()
        sessions.value = res.sessions || []
      } catch (err) {
        console.error('加载会话列表失败:', err)
      }
    }

    async function loadSession(id) {
      try {
        const res = await api.getSession(id)
        disposeAllChartInstances()
        messages.value = res.messages.map(m => ({
          ...m,
          streaming: false
        }))
        currentSessionId.value = id
        sidebarOpen.value = false
        scrollToBottom()
        nextTick(() => {
          for (let i = 0; i < messages.value.length; i++) {
            renderChartsForMessage(i)
          }
        })
      } catch (err) {
        console.error('加载会话失败:', err)
      }
    }

    async function deleteSession(id) {
      if (!confirm('确定要删除这个会话吗？')) return
      try {
        await api.deleteSession(id)
        if (currentSessionId.value === id) {
          messages.value = []
          currentSessionId.value = null
        }
        loadSessions()
      } catch (err) {
        console.error('删除会话失败:', err)
      }
    }

    function selectSession(id) {
      loadSession(id)
      showSessionList.value = false
    }

    function createNewSessionFromPopup() {
      createNewSession()
      showSessionList.value = false
    }

    async function refreshAdmin() {
      adminLoading.value = true
      try {
        fenceMetrics.value = await api.getFenceMetrics()
        await loadAuditLogs(logFilter.value)
      } catch (err) {
        console.error('加载管理后台数据失败:', err)
      }
      adminLoading.value = false
    }

    async function loadAuditLogs(status = 'all') {
      logFilter.value = status
      try {
        const res = await api.getAuditLogs(status === 'all' ? '' : status)
        auditLogs.value = res.logs || []
      } catch (err) {
        console.error('加载审计日志失败:', err)
      }
    }

    return {
      currentUser, isAdmin, handleLogout,
      // 用户菜单
      userMenuOpen, showUserProfile, showChangePassword,
      profileForm, passwordForm,
      profileLoading, passwordLoading,
      profileError, passwordError,
      profileSuccess, passwordSuccess,
      toggleUserMenu, openUserProfile, openChangePassword,
      updateProfile, changePassword,
      // 其他状态
      messages, inputText, isLoading, isThinking, isStreaming,
      sidebarOpen, messagesContainer, currentSessionId, sessions,
      expandedThinking, quickQuestions, qIcons,
      showAdmin, fenceMetrics, auditLogs, logFilter, adminLoading,
      statusLabels, scrollToBottom, renderContent,
      toggleThinking, sendQuickQuestion, sendMessage,
      createNewSession, loadSession, deleteSession,
      refreshAdmin, loadAuditLogs,
      showSessionList, selectSession, createNewSessionFromPopup,
    }
  }
}
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background-color: var(--color-neutral-bg);
}

.app-header {
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  padding: 0 var(--spacing-xl);
  height: var(--header-height);
  display: flex;
  align-items: center;
  z-index: 100;
  flex-shrink: 0;
  position: relative;
}

.app-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.3), rgba(114, 46, 209, 0.2), transparent);
}

.header-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-l);
  width: 100%;
}

.header-logo {
  width: 42px; height: 42px;
  border-radius: var(--radius-m);
  background: var(--color-accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xl);
  flex-shrink: 0;
  box-shadow: var(--shadow-glow);
  transition: all var(--transition-spring);
  position: relative;
}

.header-logo::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: calc(var(--radius-m) + 2px);
  background: var(--color-accent-gradient);
  opacity: 0;
  z-index: -1;
  filter: blur(8px);
  transition: opacity var(--transition-normal);
}

.header-logo:hover {
  transform: rotate(15deg) scale(1.08);
}

.header-logo:hover::before {
  opacity: 0.5;
}

.header-text {
  flex: 1;
  min-width: 0;
}

.header-text h1 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: var(--line-height-tight);
  letter-spacing: -0.02em;
  margin-bottom: 1px;
  background: linear-gradient(135deg, #F0F4F8 30%, #00D9FF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-subtitle {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-normal);
  letter-spacing: 0.02em;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-s);
  flex-shrink: 0;
}

.header-action-btn {
  width: 38px; height: 38px;
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border);
  background: var(--color-neutral-surface);
  cursor: pointer;
  font-size: var(--font-size-l);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-spring);
  flex-shrink: 0;
  color: var(--text-tertiary);
}

.header-action-btn:hover {
  border-color: rgba(0, 217, 255, 0.4);
  background: rgba(0, 217, 255, 0.08);
  color: #00D9FF;
  transform: scale(1.05);
  box-shadow: var(--shadow-glow);
}

.header-action-btn.active {
  border-color: rgba(0, 217, 255, 0.5);
  background: rgba(0, 217, 255, 0.12);
  color: #00D9FF;
  box-shadow: var(--shadow-glow);
}

.header-action-btn.logout-btn:hover {
  border-color: rgba(235, 47, 150, 0.4);
  background: rgba(235, 47, 150, 0.08);
  color: #EB2F96;
}

.user-menu {
  position: relative;
  z-index: 1000;
}

.user-badge {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-m);
  border-radius: var(--radius-full);
  background: rgba(0, 217, 255, 0.08);
  border: 1px solid rgba(0, 217, 255, 0.15);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-spring);
  font-weight: var(--font-weight-medium);
}

.user-badge:hover {
  background: rgba(0, 217, 255, 0.12);
  border-color: rgba(0, 217, 255, 0.3);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 217, 255, 0.15);
}

.user-avatar {
  font-size: var(--font-size-s);
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-neutral-text-inverse);
  flex-shrink: 0;
  overflow: hidden;
}

.user-avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.user-name {
  font-weight: var(--font-weight-medium);
  color: #00D9FF;
  margin-right: var(--spacing-xs);
}

.user-menu-arrow {
  font-size: 10px;
  color: var(--text-tertiary);
  transition: transform var(--transition-fast);
  line-height: 1;
}

.user-menu-arrow.open {
  transform: rotate(180deg);
}

.user-menu-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: var(--spacing-xs);
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-m);
  box-shadow: var(--shadow-xl);
  min-width: 200px;
  z-index: 1000;
  animation: dropdownFadeIn 0.2s cubic-bezier(0.2, 0, 0, 1);
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-8px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.user-menu-header {
  padding: var(--spacing-l);
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  border-bottom: 1px solid var(--color-neutral-border);
}

.user-menu-avatar {
  font-size: var(--font-size-2xl);
  filter: drop-shadow(0 0 8px rgba(0, 217, 255, 0.3));
}

.user-menu-info {
  flex: 1;
  min-width: 0;
}

.user-menu-username {
  font-size: var(--font-size-s);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-menu-role {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: 2px;
}

.user-menu-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--color-accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-l);
  color: var(--color-neutral-text-inverse);
  flex-shrink: 0;
  overflow: hidden;
}

.user-menu-divider {
  height: 1px;
  background: var(--color-neutral-border);
  margin: 0;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  padding: var(--spacing-m) var(--spacing-l);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: var(--font-size-s);
  color: var(--text-secondary);
  text-align: left;
  width: 100%;
}

.user-menu-item:hover {
  background: rgba(0, 217, 255, 0.08);
  color: #00D9FF;
}

.user-menu-item.logout:hover {
  background: rgba(235, 47, 150, 0.08);
  color: #EB2F96;
}

.menu-icon {
  font-size: var(--font-size-s);
  flex-shrink: 0;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(6, 14, 26, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  backdrop-filter: blur(8px);
  animation: fadeIn 0.2s ease;
}

.modal-content {
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-l);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-width: 420px;
  max-height: 80vh;
  overflow-y: auto;
  animation: modalSlideIn 0.3s cubic-bezier(0.2, 0, 0, 1);
}

@keyframes modalSlideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xl);
  border-bottom: 1px solid var(--color-neutral-border);
}

.modal-header h3 {
  font-family: var(--font-family-display);
  font-size: var(--font-size-l);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  letter-spacing: -0.01em;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: var(--font-size-l);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  color: var(--text-tertiary);
  transition: all var(--transition-fast);
  line-height: 1;
}

.modal-close:hover {
  background: rgba(235, 47, 150, 0.1);
  color: var(--color-danger-300);
}

.modal-body {
  padding: var(--spacing-xl);
}

.modal-footer {
  display: flex;
  gap: var(--spacing-m);
  justify-content: flex-end;
  padding: var(--spacing-xl);
  border-top: 1px solid var(--color-neutral-border);
}

.form-group {
  margin-bottom: var(--spacing-l);
}

.form-label {
  display: block;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-xs);
  letter-spacing: 0.02em;
}

.form-input {
  width: 100%;
  padding: 10px 16px;
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border);
  background: var(--color-neutral-surface);
  color: var(--text-primary);
  font-size: var(--font-size-s);
  font-family: var(--font-family-base);
  outline: none;
  transition: all var(--transition-normal);
  box-sizing: border-box;
}

.form-input:focus {
  border-color: rgba(0, 217, 255, 0.4);
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.08), var(--shadow-glow);
  background: var(--color-neutral-surface-raised);
}

.form-input::placeholder {
  color: var(--text-tertiary);
}

.avatar-selector {
  display: flex;
  gap: var(--spacing-m);
  flex-wrap: wrap;
  margin-top: var(--spacing-s);
}

.avatar-option {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-s);
  border: 2px solid var(--color-neutral-border);
  background: var(--color-neutral-surface);
  cursor: pointer;
  font-size: var(--font-size-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-spring);
}

.avatar-option:hover {
  transform: scale(1.08);
  border-color: rgba(0, 217, 255, 0.3);
  box-shadow: var(--shadow-glow);
}

.avatar-option.active {
  border-color: #00D9FF;
  background: rgba(0, 217, 255, 0.1);
  box-shadow: 0 0 12px rgba(0, 217, 255, 0.3);
}

.avatar-upload {
  margin-top: var(--spacing-l);
}

.avatar-upload-input {
  display: none;
}

.avatar-upload-label {
  display: inline-block;
  padding: var(--spacing-s) var(--spacing-m);
  background: var(--color-neutral-surface);
  border: 1px solid var(--color-neutral-border);
  border-radius: var(--radius-s);
  color: var(--text-secondary);
  font-size: var(--font-size-s);
  cursor: pointer;
  transition: all var(--transition-spring);
  text-align: center;
  width: 100%;
}

.avatar-upload-label:hover {
  background: rgba(0, 217, 255, 0.08);
  border-color: rgba(0, 217, 255, 0.3);
  color: #00D9FF;
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow);
}

.form-error {
  background: rgba(235, 47, 150, 0.1);
  border: 1px solid rgba(235, 47, 150, 0.2);
  color: #EB2F96;
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-s);
  font-size: var(--font-size-xs);
  margin-bottom: var(--spacing-l);
}

.form-success {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid rgba(82, 196, 26, 0.2);
  color: #52C41A;
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-s);
  font-size: var(--font-size-xs);
  margin-bottom: var(--spacing-l);
}

.btn {
  padding: var(--spacing-m) var(--spacing-xl);
  border: none;
  border-radius: var(--radius-s);
  font-size: var(--font-size-s);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all var(--transition-spring);
  letter-spacing: 0.02em;
}

.btn-primary {
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  box-shadow: var(--shadow-glow);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.02);
  box-shadow: var(--shadow-glow-strong);
}

.btn-secondary {
  background: var(--color-neutral-surface);
  color: var(--text-secondary);
  border: 1px solid var(--color-neutral-border);
}

.btn-secondary:hover {
  background: var(--color-neutral-surface-raised);
  border-color: rgba(0, 217, 255, 0.3);
  color: var(--text-primary);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

/* 点击外部关闭菜单 */
.user-menu {
  position: relative;
}

/* 点击外部关闭菜单的逻辑通过点击事件处理 */

.admin-panel {
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-bottom: 1px solid var(--glass-border);
  padding: var(--spacing-xl);
  max-height: 50vh;
  overflow-y: auto;
  position: relative;
}

.admin-panel::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.2), transparent);
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-l);
}

.admin-header h3 {
  color: var(--text-primary);
  font-family: var(--font-family-display);
  font-size: var(--font-size-l);
  font-weight: var(--font-weight-bold);
  letter-spacing: -0.01em;
}

.admin-close {
  background: none;
  border: none;
  font-size: var(--font-size-l);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  color: var(--text-tertiary);
  transition: all var(--transition-fast);
  line-height: 1;
}

.admin-close:hover {
  background-color: rgba(235, 47, 150, 0.1);
  color: var(--color-danger-300);
}

.admin-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-m);
  margin-bottom: var(--spacing-xl);
}

.metric-card {
  background: var(--color-neutral-surface);
  border-radius: var(--radius-m);
  padding: var(--spacing-l);
  text-align: center;
  box-shadow: var(--shadow-s);
  border: 1px solid var(--color-neutral-border);
  transition: all var(--transition-spring);
  position: relative;
  overflow: hidden;
}

.metric-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--color-accent-gradient);
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
  border-color: rgba(0, 217, 255, 0.2);
}

.metric-card:hover::before {
  opacity: 1;
}

.metric-icon { font-size: var(--font-size-xl); margin-bottom: var(--spacing-xs); }

.metric-value {
  font-family: var(--font-family-display);
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin-bottom: var(--spacing-xs);
  letter-spacing: -0.03em;
  line-height: 1;
}

.metric-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-total .metric-value { color: #00D9FF; text-shadow: 0 0 20px rgba(0, 217, 255, 0.3); }
.metric-success .metric-value { color: #52C41A; text-shadow: 0 0 20px rgba(82, 196, 26, 0.3); }
.metric-fallback .metric-value { color: #EB2F96; text-shadow: 0 0 20px rgba(235, 47, 150, 0.3); }
.metric-clarify .metric-value { color: #FA8C16; text-shadow: 0 0 20px rgba(250, 140, 22, 0.3); }

.admin-section {
  background: var(--color-neutral-surface);
  border-radius: var(--radius-m);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-m);
  box-shadow: var(--shadow-s);
  border: 1px solid var(--color-neutral-border);
  transition: all var(--transition-spring);
}

.admin-section:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}

.admin-section h4 {
  margin-bottom: var(--spacing-l);
  color: var(--text-primary);
  font-family: var(--font-family-display);
  font-size: var(--font-size-m);
  font-weight: var(--font-weight-semibold);
  letter-spacing: -0.01em;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-s);
}

.section-header h4 { margin-bottom: 0; flex: 1; min-width: 200px; }

.filter-tabs {
  display: flex;
  gap: 2px;
  background: var(--color-neutral-bg);
  padding: 3px;
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border-light);
}

.filter-btn {
  padding: var(--spacing-xs) var(--spacing-m);
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  font-size: var(--font-size-xs);
  cursor: pointer;
  transition: all var(--transition-fast);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.filter-btn.active {
  background: rgba(0, 217, 255, 0.12);
  color: #00D9FF;
  box-shadow: var(--shadow-xs);
}

.filter-btn:hover:not(.active) {
  color: var(--text-secondary);
  background: rgba(0, 217, 255, 0.04);
}

.status-bars {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-s);
}

.status-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
}

.status-label {
  width: 48px;
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  flex-shrink: 0;
  font-weight: var(--font-weight-medium);
}

.status-bar-bg {
  flex: 1;
  height: 8px;
  background: var(--color-neutral-bg);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.status-bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 1s cubic-bezier(0.2, 0, 0, 1);
  min-width: 4px;
  position: relative;
}

.status-bar-fill::after {
  content: '';
  position: absolute;
  right: 0; top: 0; bottom: 0;
  width: 20px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2));
  border-radius: 0 var(--radius-full) var(--radius-full) 0;
}

.status-bar-fill.success { background: linear-gradient(90deg, #358C11, #52C41A); }
.status-bar-fill.fallback { background: linear-gradient(90deg, #A6206C, #EB2F96); }
.status-bar-fill.clarify { background: linear-gradient(90deg, #AC6210, #FA8C16); }

.status-count {
  width: 40px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  text-align: right;
  color: var(--text-primary);
  flex-shrink: 0;
  font-family: var(--font-family-display);
}

.question-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.question-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  padding: var(--spacing-s) var(--spacing-m);
  border-radius: var(--radius-s);
  font-size: var(--font-size-s);
  transition: all var(--transition-fast);
  background: var(--color-neutral-bg);
}

.question-item:hover {
  background: rgba(0, 217, 255, 0.04);
  transform: translateX(4px);
}

.question-item.fallback { border-left: 2px solid var(--color-danger-300); }
.question-item.clarify { border-left: 2px solid var(--color-warning-300); }

.q-rank {
  width: 22px; height: 22px;
  border-radius: var(--radius-xs);
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
  font-family: var(--font-family-display);
}

.q-text {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
}

.q-count {
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  flex-shrink: 0;
  font-weight: var(--font-weight-medium);
  font-family: var(--font-family-display);
}

.log-table-wrap {
  overflow-x: auto;
  border-radius: var(--radius-s);
  border: 1px solid var(--color-neutral-border);
}

.log-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-xs);
  background: var(--color-neutral-surface);
}

.log-table th {
  background: var(--color-neutral-bg);
  padding: var(--spacing-s) var(--spacing-m);
  text-align: left;
  font-weight: var(--font-weight-semibold);
  white-space: nowrap;
  border-bottom: 1px solid var(--color-neutral-border);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  position: sticky;
  top: 0;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.log-table td {
  padding: var(--spacing-s) var(--spacing-m);
  border-bottom: 1px solid var(--color-neutral-border-light);
  color: var(--text-secondary);
}

.log-table tbody tr { transition: background var(--transition-fast); }
.log-table tbody tr:hover { background: rgba(0, 217, 255, 0.04); }

.log-time {
  white-space: nowrap;
  color: var(--text-tertiary);
  font-size: var(--font-size-xs);
  font-family: var(--font-family-mono);
}

.log-question {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-tag {
  display: inline-block;
  padding: 2px var(--spacing-s);
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-tag.success {
  background: rgba(82, 196, 26, 0.1);
  color: #52C41A;
  border: 1px solid rgba(82, 196, 26, 0.2);
}

.status-tag.fallback {
  background: rgba(235, 47, 150, 0.1);
  color: #EB2F96;
  border: 1px solid rgba(235, 47, 150, 0.2);
}

.status-tag.clarify {
  background: rgba(250, 140, 22, 0.1);
  color: #FA8C16;
  border: 1px solid rgba(250, 140, 22, 0.2);
}

.empty-logs {
  text-align: center;
  color: var(--text-tertiary);
  padding: var(--spacing-2xl);
  font-size: var(--font-size-s);
}

.refresh-btn {
  display: block;
  margin: var(--spacing-xl) auto 0;
  padding: var(--spacing-m) var(--spacing-2xl);
  border: none;
  border-radius: var(--radius-s);
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-s);
  cursor: pointer;
  transition: all var(--transition-spring);
  box-shadow: var(--shadow-glow);
  position: relative;
  overflow: hidden;
  letter-spacing: 0.02em;
}

.refresh-btn::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  transition: left 0.6s;
}

.refresh-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.02);
  box-shadow: var(--shadow-glow-strong);
}

.refresh-btn:hover::after {
  left: 100%;
}

.refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none !important;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  background-color: var(--color-neutral-bg);
}

.dashboard-panel {
  width: 68%;
  flex-shrink: 0;
  overflow: hidden;
  border-right: 1px solid var(--color-neutral-border);
  background-color: var(--color-neutral-bg-alt);
  position: relative;
}

.chat-panel {
  width: 32%;
  flex-shrink: 0;
  display: flex;
  overflow: hidden;
  position: relative;
  background-color: var(--color-neutral-bg);
}

.chat-panel .sidebar {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  transform: translateX(-100%);
  box-shadow: var(--shadow-xl);
  z-index: 100;
  width: var(--sidebar-width);
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  transition: transform var(--transition-spring);
  border-right: 1px solid var(--glass-border);
}

.chat-panel .sidebar.sidebar-open {
  transform: translateX(0);
}

.chat-panel .sidebar-overlay {
  display: block;
  position: absolute;
  inset: 0;
  background: rgba(6, 14, 26, 0.6);
  z-index: 90;
  backdrop-filter: blur(6px);
}

.chat-panel .sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-right: 1px solid var(--glass-border);
  padding: var(--spacing-xl);
  overflow-y: auto;
  flex-shrink: 0;
  transition: transform var(--transition-spring);
  z-index: 50;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sidebar-overlay { display: none; }

.new-session-btn {
  width: 100%;
  padding: var(--spacing-m) var(--spacing-xl);
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  border: none;
  border-radius: var(--radius-s);
  font-size: var(--font-size-s);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-s);
  transition: all var(--transition-spring);
  box-shadow: var(--shadow-glow);
  margin-bottom: var(--spacing-xl);
  position: relative;
  overflow: hidden;
  letter-spacing: 0.01em;
}

.new-session-btn::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  transition: left 0.6s;
}

.new-session-btn:hover {
  transform: translateY(-2px) scale(1.01);
  box-shadow: var(--shadow-glow-strong);
}

.new-session-btn:hover::after {
  left: 100%;
}

.new-session-btn:active {
  transform: translateY(0) scale(0.99);
}

.section-title {
  font-size: 10px;
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-m);
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.session-list {
  margin-bottom: var(--spacing-xl);
  flex: 1;
}

.empty-sessions {
  color: var(--text-tertiary);
  font-size: var(--font-size-s);
  padding: var(--spacing-2xl);
  text-align: center;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-m);
  border-radius: var(--radius-s);
  margin-bottom: 2px;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: transparent;
  border: 1px solid transparent;
}

.session-item:hover {
  background: rgba(0, 217, 255, 0.04);
  border-color: rgba(0, 217, 255, 0.12);
  transform: translateX(3px);
}

.session-item.active {
  background: rgba(0, 217, 255, 0.06);
  border-left: 2px solid #00D9FF;
  padding-left: calc(var(--spacing-m) - 2px);
}

.session-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  flex: 1;
  min-width: 0;
}

.session-icon { font-size: var(--font-size-l); flex-shrink: 0; }

.session-detail {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.session-name {
  font-size: var(--font-size-s);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--font-weight-medium);
}

.session-meta {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: 2px;
}

.session-delete {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  transition: all var(--transition-fast);
  font-size: var(--font-size-s);
  color: var(--text-tertiary);
  line-height: 1;
}

.session-item:hover .session-delete { opacity: 0.6; }

.session-delete:hover {
  opacity: 1 !important;
  background: rgba(235, 47, 150, 0.1);
  color: #EB2F96;
}

.project-info {
  margin-top: auto;
  padding-top: var(--spacing-xl);
  border-top: 1px solid var(--color-neutral-border);
}

.info-card {
  background: var(--color-neutral-bg);
  border-radius: var(--radius-s);
  padding: var(--spacing-l);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-normal);
  color: var(--text-tertiary);
  border: 1px solid var(--color-neutral-border-light);
}

.info-card strong { color: var(--text-secondary); font-weight: var(--font-weight-semibold); }
.info-features { margin-top: var(--spacing-m); }
.info-card ol { padding-left: var(--spacing-l); margin-top: var(--spacing-xs); }
.info-card li { margin: var(--spacing-xs) 0; color: var(--text-tertiary); }

.sidebar-toggle {
  position: fixed;
  top: 74px;
  left: var(--spacing-m);
  z-index: 60;
  width: 36px; height: 36px;
  background: var(--glass-bg-heavy);
  backdrop-filter: blur(12px);
  border: 1px solid var(--color-neutral-border);
  border-radius: var(--radius-s);
  cursor: pointer;
  font-size: var(--font-size-m);
  box-shadow: var(--shadow-m);
  display: none;
  transition: all var(--transition-spring);
  color: var(--text-tertiary);
}

.sidebar-toggle:hover {
  box-shadow: var(--shadow-glow);
  transform: scale(1.08);
  border-color: rgba(0, 217, 255, 0.4);
  color: #00D9FF;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--color-neutral-bg);
  position: relative;
  min-width: 0;
  height: 100%;
}

.chat-area .message-bubble { max-width: 85%; }

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(6, 14, 26, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  backdrop-filter: blur(8px);
}

.loading-content { text-align: center; }

.loading-spinner {
  width: 36px; height: 36px;
  border: 2px solid rgba(0, 217, 255, 0.1);
  border-top-color: #00D9FF;
  border-radius: 50%;
  margin: 0 auto var(--spacing-l);
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.loading-content p { color: var(--text-tertiary); font-size: var(--font-size-s); letter-spacing: 0.01em; }

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-xl);
  scroll-behavior: smooth;
  background: var(--color-neutral-bg);
}

.welcome-container {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: var(--spacing-xl);
}

.welcome-card {
  background: var(--color-neutral-surface);
  border-radius: var(--radius-l);
  padding: var(--spacing-2xl);
  text-align: center;
  box-shadow: var(--shadow-m);
  border: 1px solid var(--color-neutral-border);
  max-width: 100%;
  width: 100%;
  animation: welcomeFadeIn 0.7s cubic-bezier(0.2, 0, 0, 1);
  transition: all var(--transition-spring);
  position: relative;
  overflow: hidden;
}

.welcome-card::before {
  content: '';
  position: absolute;
  top: -60%; left: -20%;
  width: 140%; height: 120%;
  background: radial-gradient(ellipse at center, rgba(0, 217, 255, 0.06) 0%, transparent 60%);
  pointer-events: none;
}

.welcome-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

@keyframes welcomeFadeIn {
  from { opacity: 0; transform: translateY(24px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.welcome-icon {
  font-size: 3.5rem;
  margin-bottom: var(--spacing-l);
  display: inline-block;
  animation: float 4s ease-in-out infinite;
  filter: drop-shadow(0 0 20px rgba(0, 217, 255, 0.3));
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.welcome-card h2 {
  color: var(--text-primary);
  font-family: var(--font-family-display);
  font-size: var(--font-size-2xl);
  margin-bottom: var(--spacing-m);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
  letter-spacing: -0.02em;
}

.welcome-card > p {
  color: var(--text-tertiary);
  font-size: var(--font-size-s);
  margin-bottom: var(--spacing-2xl);
  line-height: var(--line-height-relaxed);
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.quick-questions {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-s);
  max-width: 480px;
  margin: 0 auto;
}

.quick-question-btn {
  padding: var(--spacing-m) var(--spacing-l);
  background: var(--color-neutral-bg);
  border: 1px solid var(--color-neutral-border);
  border-radius: var(--radius-s);
  color: var(--text-secondary);
  font-size: var(--font-size-s);
  cursor: pointer;
  transition: all var(--transition-spring);
  text-align: left;
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  line-height: var(--line-height-snug);
}

.quick-question-btn:hover {
  background: rgba(0, 217, 255, 0.06);
  border-color: rgba(0, 217, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow);
  color: var(--text-primary);
}

.qq-icon { flex-shrink: 0; font-size: var(--font-size-l); }

.chat-message {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-m);
  margin-bottom: var(--spacing-xl);
  animation: fadeInUp 0.4s cubic-bezier(0.2, 0, 0, 1);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-avatar {
  width: 36px; height: 36px;
  border-radius: var(--radius-s);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-m);
  flex-shrink: 0;
  box-shadow: var(--shadow-s);
  transition: all var(--transition-spring);
}

.message-avatar.user {
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
}

.message-avatar.assistant {
  background: linear-gradient(135deg, #722ED1, #1890FF);
  color: var(--color-neutral-text-inverse);
}

.chat-message:hover .message-avatar {
  transform: scale(1.08);
}

.message-bubble {
  max-width: 75%;
  padding: var(--spacing-l) var(--spacing-xl);
  border-radius: var(--radius-l);
  box-shadow: var(--shadow-s);
  transition: all var(--transition-normal);
  line-height: var(--line-height-normal);
  position: relative;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.message-bubble.user {
  background: var(--color-accent-gradient);
  color: white;
  border-bottom-right-radius: var(--radius-xs);
  margin-left: auto;
  box-shadow: 0 4px 20px rgba(0, 217, 255, 0.2);
}

.message-bubble.assistant {
  background: var(--color-neutral-surface);
  color: var(--text-primary);
  border-bottom-left-radius: var(--radius-xs);
  border: 1px solid var(--color-neutral-border);
  box-shadow: var(--shadow-s);
}

.thinking-section { margin-bottom: var(--spacing-m); }

.thinking-toggle {
  background: rgba(250, 140, 22, 0.08);
  color: #FA8C16;
  border: 1px solid rgba(250, 140, 22, 0.15);
  padding: var(--spacing-xs) var(--spacing-m);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-spring);
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.thinking-toggle:hover {
  transform: scale(1.05);
  box-shadow: 0 0 12px rgba(250, 140, 22, 0.15);
  background: rgba(250, 140, 22, 0.12);
}

.thinking-toggle.thinking-active {
  background: rgba(250, 140, 22, 0.15);
  border-color: rgba(250, 140, 22, 0.3);
}

.thinking-indicator { font-size: var(--font-size-s); }

.thinking-content {
  background: var(--color-neutral-bg);
  border-radius: var(--radius-s);
  padding: var(--spacing-l);
  margin-top: var(--spacing-m);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  border: 1px solid var(--color-neutral-border-light);
  white-space: pre-wrap;
  word-break: break-word;
  line-height: var(--line-height-relaxed);
  font-family: var(--font-family-mono);
  max-height: 280px;
  overflow-y: auto;
}

.thinking-bubble { display: flex; align-items: center; gap: var(--spacing-m); }
.thinking-anim { display: flex; gap: 4px; }

.thinking-anim .dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #00D9FF;
  animation: pulse 1.4s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(0, 217, 255, 0.4);
}

.thinking-anim .dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-anim .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 100% { opacity: 0.2; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}

.thinking-text { color: var(--text-tertiary); font-size: var(--font-size-s); }

.typing-cursor {
  display: inline-block;
  animation: blink 0.7s step-end infinite;
  color: #00D9FF;
  font-weight: var(--font-weight-bold);
  margin-left: 1px;
  text-shadow: 0 0 8px rgba(0, 217, 255, 0.5);
}

@keyframes blink { 50% { opacity: 0; } }

.chat-input-area {
  padding: var(--spacing-l) var(--spacing-xl);
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border-top: 1px solid var(--color-neutral-border);
  position: relative;
}

.chat-input-area::before {
  content: '';
  position: absolute;
  top: -1px;
  left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 217, 255, 0.15), transparent);
}

.input-container {
  display: flex;
  gap: var(--spacing-m);
  max-width: 100%;
  margin: 0 auto;
}

.chat-input {
  flex: 1;
  padding: 10px 20px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-neutral-border);
  font-size: var(--font-size-s);
  font-family: var(--font-family-base);
  outline: none;
  transition: all var(--transition-normal);
  background: var(--color-neutral-surface);
  color: var(--text-primary);
}

.chat-input:focus {
  border-color: rgba(0, 217, 255, 0.4);
  background: var(--color-neutral-surface-raised);
  box-shadow: 0 0 0 3px rgba(0, 217, 255, 0.08), var(--shadow-glow);
}

.chat-input::placeholder { color: var(--text-tertiary); }

.chat-input:disabled {
  background: var(--color-neutral-bg);
  cursor: not-allowed;
  opacity: 0.5;
}

.send-btn {
  width: 44px; height: 44px;
  padding: 0;
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--font-size-xl);
  cursor: pointer;
  transition: all var(--transition-spring);
  box-shadow: var(--shadow-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.send-btn::after {
  content: '';
  position: absolute;
  top: 0; left: -100%;
  width: 100%; height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  transition: left 0.6s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px) scale(1.06);
  box-shadow: var(--shadow-glow-strong);
}

.send-btn:hover::after {
  left: 100%;
}

.send-btn:active:not(:disabled) { transform: translateY(0) scale(0.95); }

.send-btn:disabled {
  opacity: 0.25;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

.send-icon { display: block; line-height: 1; transform: rotate(45deg); }

.input-hint {
  text-align: center;
  font-size: 10px;
  color: var(--text-tertiary);
  margin-top: var(--spacing-s);
  letter-spacing: 0.02em;
}

.slide-down-enter-active,
.slide-down-leave-active {
  transition: all var(--transition-slow);
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
  margin-top: 0;
}

.fade-enter-active,
.fade-leave-active { transition: opacity var(--transition-normal); }

.fade-enter-from,
.fade-leave-to { opacity: 0; }

.expand-enter-active,
.expand-leave-active { transition: all var(--transition-slow); overflow: hidden; }

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
  margin-top: 0;
  padding-top: 0;
  padding-bottom: 0;
}

@media (max-width: 768px) {
  .dashboard-panel { display: none; }
  .chat-panel { width: 100%; border-left: none; }
  .sidebar {
    position: fixed;
    left: 0; top: 0; bottom: 0;
    transform: translateX(-100%);
    box-shadow: var(--shadow-xl);
    z-index: 100;
    width: 280px;
  }
  .sidebar.sidebar-open { transform: translateX(0); }
  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(6, 14, 26, 0.5);
    z-index: 90;
    backdrop-filter: blur(6px);
  }
  .sidebar-toggle { display: flex; align-items: center; justify-content: center; }
  .sidebar-close { display: block; }
  .header-text h1 { font-size: var(--font-size-l); }
  .header-subtitle { display: none; }
  .message-bubble { max-width: 88%; }
  .quick-questions { grid-template-columns: 1fr; }
  .admin-metrics { grid-template-columns: repeat(2, 1fr); }
  .chat-messages { padding: var(--spacing-l); }
  .chat-input-area { padding: var(--spacing-l); }
  .welcome-card { padding: var(--spacing-xl); }
  .sidebar-toggle { top: 68px; left: var(--spacing-s); }
}

@media (min-width: 769px) {
  .sidebar-close { display: none; }
}

@media (min-width: 769px) and (max-width: 1200px) {
  .dashboard-panel { width: 65%; }
  .chat-panel { width: 35%; }
}

@media (max-width: 480px) {
  .app-header { padding: 0 var(--spacing-m); }
  .header-content { gap: var(--spacing-m); }
  .header-logo { width: 34px; height: 34px; font-size: var(--font-size-m); }
  .header-text h1 { font-size: var(--font-size-m); }
  .header-action-btn { width: 32px; height: 32px; }
  .chat-messages { padding: var(--spacing-m); }
  .message-avatar { width: 30px; height: 30px; font-size: var(--font-size-s); }
  .message-bubble { padding: var(--spacing-m); max-width: 90%; }
  .quick-question-btn { padding: var(--spacing-m); }
}

/* 会话历史弹窗样式 */
.session-list-modal {
  background: var(--glass-bg-heavy);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-l);
  box-shadow: var(--shadow-xl);
  width: 90%;
  max-width: 420px;
  max-height: 70vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: modalSlideIn 0.3s cubic-bezier(0.2, 0, 0, 1);
}

.session-list-body {
  padding: var(--spacing-l);
  overflow-y: auto;
  flex: 1;
}

.new-session-btn-popup {
  width: 100%;
  padding: var(--spacing-m) var(--spacing-l);
  background: var(--color-accent-gradient);
  color: var(--color-neutral-text-inverse);
  border: none;
  border-radius: var(--radius-s);
  font-size: var(--font-size-s);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-s);
  transition: all var(--transition-spring);
  box-shadow: var(--shadow-glow);
  margin-bottom: var(--spacing-l);
}

.new-session-btn-popup:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-glow-strong);
}

.session-list-container {
  max-height: 400px;
  overflow-y: auto;
}

.empty-sessions-popup {
  color: var(--text-tertiary);
  font-size: var(--font-size-s);
  padding: var(--spacing-2xl);
  text-align: center;
}

.session-item-popup {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-m);
  border-radius: var(--radius-s);
  margin-bottom: 2px;
  cursor: pointer;
  transition: all var(--transition-fast);
  background: transparent;
  border: 1px solid transparent;
}

.session-item-popup:hover {
  background: rgba(0, 217, 255, 0.04);
  border-color: rgba(0, 217, 255, 0.12);
  transform: translateX(3px);
}

.session-item-popup.active {
  background: rgba(0, 217, 255, 0.06);
  border-left: 2px solid #00D9FF;
  padding-left: calc(var(--spacing-m) - 2px);
}

.session-info-popup {
  display: flex;
  align-items: center;
  gap: var(--spacing-m);
  flex: 1;
  min-width: 0;
}

.session-icon { font-size: var(--font-size-l); flex-shrink: 0; }

.session-detail-popup {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.session-name-popup {
  font-size: var(--font-size-s);
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--font-weight-medium);
}

.session-meta-popup {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  margin-top: 2px;
}

.session-delete-popup {
  opacity: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--radius-xs);
  transition: all var(--transition-fast);
  font-size: var(--font-size-s);
  color: var(--text-tertiary);
  line-height: 1;
}

.session-item-popup:hover .session-delete-popup { opacity: 0.6; }

.session-delete-popup:hover {
  opacity: 1 !important;
  background: rgba(235, 47, 150, 0.1);
  color: #EB2F96;
}
</style>
