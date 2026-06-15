---
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Youni Lab — Component Specs
# 元件規格書（v2.2）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

name:     Youni Lab Component Specs
version:  "2.2"
total:    38
note:     All colors synced from Figma Design Tokens (ref → sys → comp).
          Refer to DESIGN.md for brand foundations.
          v2.1 adds 14 components: Sidebar/Nav, Page Header, Stat Card,
          Pagination, Empty State, Notification Item, User Row, Date Picker,
          Dropdown Menu (enhanced), Select (multi-tag), Radio Card,
          Star Rating, Toggle Group (enhanced), Choicebox (enhanced).


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Avatar — 頭像
# 使用者頭像或縮寫，支援狀態指示與堆疊
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

avatar:
  shape:            circle
  sizes:            [24, 32, 40, 48, 64]    # 5 種尺寸
  font-size-ratio:  0.38                     # 縮寫字號 = 尺寸 × 0.38
  font-weight:      600                      # Semibold
  status-dot-ratio: 0.28                     # 狀態燈 = 尺寸 × 0.28
  status-dot-border: 2px solid surface-default
  stack-overlap:    -10px                    # 堆疊重疊量

  # 狀態色
  status-colors:
    online:   '#52C41A'     # 在線（綠）
    away:     '#FDB338'     # 離開（琥珀）
    busy:     '#F5222D'     # 忙碌（紅）
    offline:  '#BFBFBF'     # 離線（灰）

  # 縮寫背景色池（依名字首字 hash 分配）
  palette:
    - '#0A2B41'
    - '#0958D9'
    - '#389E0D'
    - '#D68C24'
    - '#7C3AED'
    - '#CF1322'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Badge — 標籤 / 徽章
# 狀態標記、資料型態識別
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

badge:
  font-weight:   500
  border-width:  1px
  display:       inline-flex          # v2.2：固定不換行
  white-space:   nowrap               # ⚠ 必須：內容定義寬度，永不被欄寬擠成直排
  align-items:   center

  # 三種尺寸
  sizes:
    sm:   { fontSize: 11px, padding: '1px 6px' }
    md:   { fontSize: 12px, padding: '2px 8px' }
    lg:   { fontSize: 13px, padding: '3px 10px' }

  # 圓角
  radius:
    badge:  6px       # 一般狀態標籤
    pill:   9999px    # 資料型態專用（整數、文字、布林、日期）

  # ⚠ Pill 使用規則：rounded-full 僅限資料型態標籤，普通狀態標籤用 badge（6px）
  pill-rule: reserved for data-type labels only

  # 7 種語意色
  variants:
    default:  { bg: '#F5F5F5', label: '#595959', border: '#D9D9D9' }   # 預設
    primary:  { bg: '#E7EAEC', label: '#0A2B41', border: '#9AABB7' }   # 品牌
    info:     { bg: '#E6F4FF', label: '#0958D9', border: '#91CAFF' }   # 資訊
    success:  { bg: '#F6FFED', label: '#389E0D', border: '#B7EB8F' }   # 成功
    warning:  { bg: '#FFFCF0', label: '#AD6800', border: '#FFC861' }   # 警告
    error:    { bg: '#FFF1F0', label: '#CF1322', border: '#FFA39E' }   # 錯誤
    purple:   { bg: '#F5F3FF', label: '#7C3AED', border: '#DDD6FE' }   # 圖表分類


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Breadcrumbs — 麵包屑導覽
# 頁面層級定位
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

breadcrumbs:
  font-size:        14px
  gap:              8px
  separator:        '/'
  separator-color:  '#8C8C8C'

  active:           { color: '#1F1F1F', weight: 500 }     # 目前頁（最後一層）
  inactive:         { color: '#8C8C8C', weight: 400 }     # 上層頁面
  hover:            { color: '#1F1F1F' }                   # hover 變深


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Button — 按鈕
# 觸發動作或事件的核心互動元件
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

button:
  font-weight:  500

  # 三種尺寸 ──────────────────────────
  sizes:
    sm:                                      # 小型
      height:     32px
      fontSize:   12px
      lineHeight: 18px
      paddingX:   12px
      paddingY:   4px
      radius:     4px
      iconSize:   16px
      gap:        4px

    md:                                      # 標準（預設）
      height:     40px
      fontSize:   14px
      lineHeight: 22px
      paddingX:   20px
      paddingY:   8px
      radius:     8px
      iconSize:   16px
      gap:        4px

    lg:                                      # 大型
      height:     48px
      fontSize:   16px
      lineHeight: 24px
      paddingX:   24px
      paddingY:   12px
      radius:     8px
      iconSize:   20px
      gap:        8px

  # 四種形狀 ──────────────────────────
  shapes:
    default:      standard button           # 標準按鈕（文字 + 可選 icon）
    icon-square:  { radius: 8px }           # 方形 icon-only
    icon-circle:  { radius: 50% }           # 圓形 icon-only
    rounded:                                 # 行銷用全圓角
      radius:   9999px
      height:   44px
      paddingX: 24px
      shadow:   '0 2px 8px rgba(0,0,0,0.08)'

  # 5 種樣式 × 4 種狀態 ──────────────
  variants:

    primary:                                 # 主要操作（儲存、確認）
      bg:             '#0A2B41'
      bgHover:        '#2E4A5E'
      bgPressed:      '#061A28'
      bgDisabled:     '#F0F0F0'
      label:          '#FFFFFF'
      labelDisabled:  '#BFBFBF'
      border:         '#0A2B41'
      borderFocused:  '#718491'

    secondary:                               # 次要操作（取消、返回）
      bg:             '#FFFFFF'
      bgHover:        '#FAFAFA'
      bgPressed:      '#F5F5F5'
      bgDisabled:     '#F0F0F0'
      label:          '#1F1F1F'
      labelDisabled:  '#BFBFBF'
      border:         '#D9D9D9'
      borderFocused:  '#718491'

    error:                                   # 危險操作（刪除、移除）
      bg:             '#F5222D'
      bgHover:        '#FF4D4F'
      bgPressed:      '#CF1322'
      bgDisabled:     '#F0F0F0'
      label:          '#FFFFFF'
      labelDisabled:  '#BFBFBF'

    ghost:                                   # 幽靈按鈕（低權重輔助）
      bg:             transparent
      bgHover:        '#FAFAFA'
      bgPressed:      '#F5F5F5'
      label:          '#1F1F1F'
      labelDisabled:  '#BFBFBF'

    warning:                                 # 警告操作
      bg:             '#FDB338'
      bgHover:        '#FFC861'
      bgPressed:      '#D68C24'
      bgDisabled:     '#F0F0F0'
      label:          '#FFFFFF'
      labelDisabled:  '#BFBFBF'

  # 行為規則 ──────────────────────────
  focus-ring:     '0 0 0 3px rgba(10,43,65,0.08)'
  pair-pattern:   "outline cancel (left) + filled confirm (right)"   # 配對模式
  label-rule:     "verb + noun (Save Project, Delete Key)"           # 標籤命名規則
  loading:        dot-pulse animation replacing label text            # 載入狀態
  disabled:       opacity or explicit disabled tokens, never both     # 禁用狀態


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Card — 卡片
# 內容容器，分為 header / body / footer 三區
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

card:
  bg:               '#FFFFFF'
  border:           '1px solid #D9D9D9'
  radius:           12px
  padding:          24px              # 標準
  padding-compact:  20px              # 緊湊

  header:                              # 頂部區域
    padding:      '16px 24px'
    borderBottom: '1px solid #F0F0F0'

  footer:                              # 底部操作區
    padding:      '12px 24px'
    bg:           '#FAFAFA'
    borderTop:    '1px solid #F0F0F0'

  hover:                               # 可 hover 卡片
    transform:    translateY(-2px)
    shadow:       '0 4px 16px rgba(0,0,0,0.06)'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Checkbox — 勾選框
# 勾選 / 未勾選 / 部分選取 三態切換
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

checkbox:
  size:           16px
  radius:         4px
  border:         '1.5px solid #D9D9D9'     # 未勾選
  borderHover:    '1.5px solid #0A2B41'     # hover

  checked:                                   # 已勾選
    bg:    '#0A2B41'
    icon:  '#FFFFFF'                         # 白色勾勾

  indeterminate:                             # 部分選取（全選切換用）
    bg:    '#0A2B41'
    icon:  '#FFFFFF'
    shape: horizontal-line                   # 橫線圖標

  disabled:       { opacity: 0.5 }

  label:                                     # 右側文字
    gap:       8px
    fontSize:  14px
    weight:    400


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Choicebox — 卡片式選擇器
# 比 Radio/Checkbox 更豐富的選擇元件
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

choicebox:
  radius:          10px
  border:          '1.5px solid #D9D9D9'      # 未選中
  borderSelected:  '1.5px solid #0A2B41'      # 選中
  bgSelected:      '#F0F4F7'                  # 選中背景
  padding:         '14px 16px'

  checkIcon:                                   # 右上角勾選圈
    size:   18px
    bg:     '#0A2B41'
    icon:   '#FFFFFF'
    shape:  circle

  modes:           [single, multi]             # 支援單選 / 多選
  disabled:        { opacity: 0.5 }

  # v2.1 補充 ──────────────────────────
  layouts:
    horizontal:                                # 橫向多欄排列（onboarding 用）
      columns:    'auto-fill, minmax(120px,1fr)'
      gap:        12px
    vertical:                                  # 垂直列表
      gap:        10px

  icon-variant:                                # icon + 標題 + 描述 版型
    icon:         { fontSize: 22px, marginBottom: 6px }
    title:        { fontSize: 13px, weight: 600 }
    description:  { fontSize: 11px, color: '#8C8C8C' }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Drawer — 側邊抽屜
# 從螢幕邊緣滑入的面板
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

drawer:
  width:        400px
  maxWidth:     90vw
  sides:        [left, right]            # 支援左右兩側

  overlay:      'rgba(0,0,0,0.4)'        # 遮罩
  overlayBlur:  2px
  shadow:       '-4px 0 24px rgba(0,0,0,0.1)'
  animation:    '0.25s ease slideIn'     # 滑入動畫

  header:                                 # 頂部標題列
    padding:      '20px 24px'
    borderBottom: '1px solid #D9D9D9'
    titleSize:    16px
    titleWeight:  600

  body:                                   # 內容區
    padding:      '20px 24px'

  close:                                  # 關閉按鈕
    size:     18px
    color:    '#8C8C8C'
    hoverBg:  '#FAFAFA'
    radius:   6px


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Feedback — 回饋收集
# Emoji 評分 / Yes-No 快速回饋
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

feedback:

  emoji:                                  # Emoji 評分模式
    size:       24px
    padding:    8px
    radius:     8px
    selected:   { border: '2px solid #0A2B41', bg: '#E7EAEC' }
    unselected: { border: '2px solid transparent', bg: transparent }

  inline:                                 # Yes/No 快速模式
    button:
      padding:   '4px 12px'
      radius:    6px
      border:    '1px solid #D9D9D9'
      fontSize:  13px
    buttonHover: { borderColor: '#0A2B41' }
    container:   { padding: '8px 16px', radius: 8px, border: '1px solid #D9D9D9' }

  confirmation:                           # 提交後確認文字
    color:   '#389E0D'
    weight:  500


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Input — 文字輸入框
# 單行文字輸入，支援前後綴、標籤、錯誤提示
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

input:

  # 背景色 ────────────────────────────
  bg:             '#FFFFFF'
  bgDisabled:     '#F0F0F0'

  # 邊框狀態 ──────────────────────────
  border:         '1px solid #D9D9D9'     # 預設
  borderHover:    '1px solid #BFBFBF'     # hover
  borderFocused:  '1px solid #0A2B41'     # 聚焦
  borderError:    '1px solid #F5222D'     # 錯誤
  borderDisabled: '1px solid #F0F0F0'     # 禁用

  # 聚焦光環 ──────────────────────────
  focusRing:      '0 0 0 3px rgba(10,43,65,0.08)'     # 品牌藍光環
  errorRing:      '0 0 0 3px rgba(245,34,45,0.08)'    # 紅色光環

  # 標籤 ──────────────────────────────
  label:
    fontSize:  13px
    weight:    500
    gap:       6px           # 標籤與輸入框間距
    color:     '#1F1F1F'

  # 其他 ──────────────────────────────
  placeholder:    '#BFBFBF'
  prefix-suffix:  { color: '#8C8C8C' }    # 前後綴文字色
  error-text:     { color: '#CF1322', fontSize: 13px, gap: 6px }
  disabled:       { opacity: 0.5 }

  # 三種尺寸 ──────────────────────────
  sizes:
    sm:   { height: 32px, fontSize: 13px, paddingX: 10px, radius: 8px }
    md:   { height: 40px, fontSize: 14px, paddingX: 12px, radius: 8px }
    lg:   { height: 48px, fontSize: 16px, paddingX: 16px, radius: 8px }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Modal — 對話框
# 疊層彈窗，用於需要使用者注意的操作
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

modal:
  bg:           '#FFFFFF'
  radius:       12px
  overlay:      'rgba(0,0,0,0.4)'
  overlayBlur:  2px
  shadow:       '0 20px 60px rgba(0,0,0,0.15)'
  animation:    'scale(0.96→1) 0.2s ease'     # 縮放進場

  header:
    padding:      '20px 24px'
    borderBottom: '1px solid #F0F0F0'
    titleSize:    16px
    titleWeight:  600

  body:
    padding:      '20px 24px'

  footer:                                       # 底部按鈕區
    padding:      '16px 24px'
    borderTop:    '1px solid #F0F0F0'

  close:
    size:     18px
    color:    '#8C8C8C'
    hoverBg:  '#FAFAFA'
    radius:   6px

  # 三種寬度
  sizes:
    sm:   360px     # 確認對話框
    md:   480px     # 表單編輯
    lg:   640px     # 複雜內容


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Note — 提示 / 警告區塊
# 重要訊息的區塊元件，5 種語意
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

note:
  radius:   8px
  padding:  '12px 16px'

  icon:     { gap: 10px }                  # 圖示與文字間距
  title:    { fontSize: 14px, weight: 600 }
  body:     { fontSize: 14px, weight: 400, color: '#595959' }

  # 5 種語意色
  variants:
    default:  { bg: '#FAFAFA', label: '#1F1F1F', border: '#D9D9D9', icon: 'ℹ' }   # 一般提示
    info:     { bg: '#E6F4FF', label: '#0958D9', border: '#91CAFF', icon: 'ℹ' }   # 資訊
    success:  { bg: '#F6FFED', label: '#389E0D', border: '#B7EB8F', icon: '✓' }   # 成功
    warning:  { bg: '#FFFCF0', label: '#AD6800', border: '#FFC861', icon: '⚠' }   # 警告
    error:    { bg: '#FFF1F0', label: '#CF1322', border: '#FFA39E', icon: '✕' }   # 錯誤


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Progress — 進度條
# 顯示任務完成進度
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

progress:
  track:      '#F0F0F0'                     # 軌道背景
  radius:     9999px                        # 全圓角
  animation:  'width 0.4s ease'             # 填充動畫
  label:      { fontSize: 12px, family: mono }

  # 三種高度
  sizes:
    sm:   4px       # 微型
    md:   8px       # 標準
    lg:   12px      # 醒目

  # 5 種顏色
  colors:
    primary:  '#0A2B41'     # 品牌深藍
    info:     '#1677FF'     # 藍色
    success:  '#52C41A'     # 綠色
    warning:  '#FDB338'     # 琥珀
    error:    '#F5222D'     # 紅色


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Radio — 單選按鈕
# 多個選項中選擇一個
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

radio:
  size:         16px
  shape:        circle
  border:       '1.5px solid #D9D9D9'       # 未選中
  borderHover:  '1.5px solid #0A2B41'       # hover
  selected:     '5px solid #0A2B41'         # 選中（縮圈效果）
  innerFill:    '#FFFFFF'                   # 內圈白色
  disabled:     { opacity: 0.5 }

  label:        { gap: 8px, fontSize: 14px, weight: 400 }
  optionGap:    12px                        # 選項之間間距
  layouts:      [vertical, horizontal]       # 支援垂直 / 水平排列

  # v2.1 補充 ──────────────────────────
  card-variant:                              # Radio Card 卡片式變體
    border:         '1.5px solid #D9D9D9'
    borderSelected: '1.5px solid #0A2B41'
    bgSelected:     '#F0F4F7'
    radius:         10px
    padding:        '14px 16px'
    checkDot:                                # 右上角選取指示器
      size:         18px
      shape:        circle
      border:       '1.5px solid #D9D9D9'
      selectedBg:   '#0A2B41'
      selectedIcon: '#FFFFFF'
    anatomy:        [icon(optional), title, description]
    gap:            10px


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Search Input — 搜尋輸入框
# 帶搜尋圖示、清除鈕、鍵盤快捷鍵
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

search-input:
  height:   40px
  radius:   8px

  icon:                                      # 左側搜尋圖示
    size:   16px
    left:   12px
    color:  '#8C8C8C'

  clear:                                     # 右側清除按鈕
    size:   24px
    right:  8px
    radius: 4px
    bg:     '#FAFAFA'
    color:  '#8C8C8C'

  shortcut:                                  # ⌘K 快捷鍵提示
    keys:       ['⌘', 'K']
    escLabel:   'Esc'                        # 有輸入時顯示 Esc
    badge:
      height:   20px
      radius:   4px
      border:   '1px solid #D9D9D9'
      bg:       '#FAFAFA'
      fontSize: 11px
      color:    '#8C8C8C'

  escape-behavior: clears input value        # 按 Escape 清除


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Select — 下拉選單
# 繼承 Input 的邊框和尺寸規格
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

select:
  inherits:   input sizes and border styles   # 與 Input 共用邊框樣式

  chevron:                                     # 右側箭頭
    size:     16px
    color:    '#8C8C8C'
    position: right

  features:   [prefix, label, error, disabled]

  sizes:
    sm:   { height: 32px, fontSize: 13px }
    md:   { height: 40px, fontSize: 14px }
    lg:   { height: 48px, fontSize: 16px }

  # v2.1 補充 ──────────────────────────
  multi-tag:                                   # 多選 Tag 模式
    minHeight:    40px
    padding:      '4px 36px 4px 12px'         # 右側留 chevron 空間
    wrapBehavior: wrap                         # 超過寬度自動換行
    tag:
      bg:         '#E7EAEC'
      color:      '#0A2B41'
      fontSize:   12px
      fontWeight: 500
      padding:    '2px 6px'
      radius:     4px
      removeIcon: { size: 11px, opacity: 0.6, hoverOpacity: 1 }
    focused:
      borderColor: '#0A2B41'
      shadow:      '0 0 0 3px rgba(10,43,65,0.08)'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Spinner — 載入動畫
# 圓形旋轉 + 脈動圓點兩種模式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

spinner:

  circle:                                     # 圓形旋轉
    sizes:         [16, 20, 28, 36]
    strokeWidth:   3px
    trackOpacity:  0.2                        # 軌道透明度
    animation:     'rotate 1s linear infinite'
    defaultColor:  '#0A2B41'

  dots:                                       # 脈動圓點
    sizes:     [4, 6, 8]
    animation: 'dotPulse 1.2s ease-in-out'
    stagger:   0.15s                          # 每顆圓點的延遲

  # 可用顏色
  colors:
    - '#0A2B41'     # 品牌深藍
    - '#1677FF'     # 藍色
    - '#52C41A'     # 綠色
    - '#F5222D'     # 紅色
    - '#8C8C8C'     # 灰色


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Switch — 開關
# 開/關 兩態切換
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

switch:
  activeBg:     '#0A2B41'                     # 開啟背景
  inactiveBg:   '#D9D9D9'                     # 關閉背景
  dot:                                         # 滑塊圓點
    bg:       '#FFFFFF'
    shadow:   '0 1px 3px rgba(0,0,0,0.15)'
  animation:    '0.2s ease'                   # 滑動動畫
  disabled:     { opacity: 0.5 }
  label:        { gap: 8px, fontSize: 14px }

  # 兩種尺寸
  sizes:
    sm:   { trackW: 32px, trackH: 18px, dot: 14px }   # 小型
    md:   { trackW: 40px, trackH: 22px, dot: 18px }   # 標準


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Table — 表格
# 結構化資料展示，僅水平分隔線
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

table:
  # ── 儲存格規則（v2.2 新增）──
  cell:
    white-space:    nowrap            # B 端表格不換行；內容過長以橫向卷動處理（見 RWD）
    vertical-align: middle            # 所有儲存格垂直置中，避免列高變動時 checkbox/內容對不齊
    overflow-x:     auto              # 欄位總寬超出時容器橫向卷動
  # ⚠ 含 Badge 的儲存格：nowrap 之外，務必設欄位最小寬度（min-width）
  #    CJK 文字在空間不足時即使 nowrap 仍會直排，根因是欄寬不夠而非屬性。
  #    狀態欄（「營業中」三字 Badge）min-width ≥ 100px（內容約 54px + padding 32px + 餘裕）

  container:                                   # 外層容器
    radius:   12px
    border:   '1px solid #D9D9D9'
    overflow: hidden

  header:                                      # 表頭
    height:    40px
    paddingX:  16px
    paddingY:  10px
    fontSize:  13px
    weight:    500
    color:     '#595959'
    border:    '1px solid #D9D9D9'
    bg:        '#FFFFFF'

  body:                                        # 內容行
    rowHeight: 48px
    paddingX:  16px
    paddingY:  14px
    fontSize:  14px
    color:     '#1F1F1F'

  divider:    '1px solid #F0F0F0'             # 行分隔線
  hoverBg:    '#FAFAFA'                       # hover 背景
  stripeBg:   '#FAFAFA'                       # 斑馬紋

  sort-icon:                                   # 排序圖示
    size:           12px
    activeColor:    '#1F1F1F'
    inactiveColor:  '#8C8C8C'

  # ⚠ 規則：僅水平分隔線，禁止垂直線
  rule: horizontal dividers only, never vertical lines


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tabs — 頁籤
# 同一空間切換不同面板
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tabs:
  activeColor:    '#1F1F1F'
  activeWeight:   500
  inactiveColor:  '#8C8C8C'
  inactiveWeight: 400
  disabled:       { opacity: 0.4 }

  primary:                                     # 底線指示器風格
    height:       40px
    padding:      '10px 16px'
    fontSize:     14px
    indicator:    '2px solid #0A2B41'          # 底線
    borderBottom: '1px solid #D9D9D9'          # 容器底線

  secondary:                                   # Pill 風格
    height:           32px
    padding:          '6px 16px'
    fontSize:         14px
    containerBg:      '#FAFAFA'
    containerRadius:  8px
    containerPadding: 3px
    activeBg:         '#FFFFFF'                # 選中背景
    activeRadius:     6px
    activeShadow:     '0 1px 3px rgba(0,0,0,0.08)'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Textarea — 多行輸入框
# 繼承 Input 的邊框和聚焦樣式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

textarea:
  inherits:    input border and focus styles   # 與 Input 共用邊框樣式
  padding:     12px
  fontSize:    14px
  lineHeight:  1.6
  radius:      8px
  minRows:     3                               # 最小 3 行
  resize:      vertical                        # 僅垂直拉伸

  counter:                                      # 字數計數器（可選）
    fontSize:  12px
    family:    mono
    position:  bottom-right
    color:     '#8C8C8C'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Toast — 通知提示
# 短暫顯示的操作回饋
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

toast:
  bg:         '#1F1F1F'                        # 深色背景
  label:      '#FFFFFF'
  padding:    '10px 16px'
  radius:     8px
  minWidth:   200px
  fontSize:   14px
  shadow:     '0 4px 14px rgba(0,0,0,0.15)'
  duration:   2500ms                           # 自動消失時間
  animation:  'fadeIn + translateY(12px→0) 0.25s ease'
  position:   fixed bottom center              # 固定底部置中
  stacking:   column-reverse with 8px gap      # 多筆堆疊

  # 語意圖標
  icons:
    success:  { symbol: '✓', color: '#52C41A' }     # 成功
    error:    { symbol: '✕', color: '#F5222D' }     # 錯誤
    warning:  { symbol: '⚠', color: '#FDB338' }     # 警告


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Toggle — 按鈕群組切換
# Pill 風格的互斥選項群組
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

toggle:

  container:                                    # 外層容器
    bg:       '#FAFAFA'
    border:   '1px solid #D9D9D9'
    radius:   8px
    padding:  3px

  button:                                       # 每個選項按鈕
    padding:  '6px 16px'
    radius:   6px
    fontSize: 13px

  active:                                       # 選中狀態
    bg:       '#FFFFFF'
    shadow:   '0 1px 3px rgba(0,0,0,0.08)'
    color:    '#1F1F1F'
    weight:   500

  inactive:                                     # 未選中
    bg:       transparent
    color:    '#8C8C8C'
    weight:   400

  # v2.1 補充 ──────────────────────────
  variants:
    text:       standard text label buttons     # 預設
    icon-text:  { gap: 6px }                   # icon + 文字
    icon-only:  { padding: '7px 10px' }        # 僅 icon（更緊湊）

  layouts:
    horizontal: default                         # 水平排列（預設）
    vertical:   { flexDirection: column, width: fit-content }  # 垂直排列

  icon:
    size:    16px
    family:  'Material Symbols Rounded'
    weight:  300
    fill:    0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tooltip — 文字提示
# hover 時顯示的浮動提示文字
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

tooltip:
  bg:         '#1F1F1F'
  label:      '#FFFFFF'
  padding:    '5px 10px'
  fontSize:   12px
  radius:     6px
  offset:     8px                              # 與觸發元素的距離
  animation:  'fadeIn 0.15s ease'
  positions:  [top, bottom, left, right]       # 4 個方向
  zIndex:     9999


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# v2.1 新增元件（14 個）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Dropdown Menu — 下拉選單（強化版）
# 右鍵選單 / 操作清單 / 功能快捷
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

dropdown-menu:
  bg:         '#FFFFFF'
  border:     '1px solid #D9D9D9'
  radius:     10px
  padding:    4px
  minWidth:   200px
  shadow:     '0 4px 16px rgba(0,0,0,0.08)'
  zIndex:     1000
  animation:  'fadeIn + scaleY(0.97→1) 150ms ease'

  item:
    padding:      '8px 10px'
    radius:       6px
    fontSize:     13px
    color:        '#1F1F1F'
    gap:          8px
    hoverBg:      '#FAFAFA'
    icon:         { size: 16px, opacity: 0.7 }
    shortcut:     { fontSize: 11px, color: '#8C8C8C', marginLeft: auto }
    submenu-arrow:{ fontSize: 10px, color: '#8C8C8C', marginLeft: auto }

  variants:
    danger:   { color: '#CF1322', hoverBg: '#FFF1F0' }
    disabled: { color: '#BFBFBF', pointerEvents: none }

  section-label:
    fontSize:      10px
    fontWeight:    500
    letterSpacing: 0.06em
    textTransform: uppercase
    color:         '#8C8C8C'
    padding:       '6px 10px 2px'

  divider:
    height:   1px
    bg:       '#F0F0F0'
    margin:   '4px 0'

  badge:
    marginLeft: auto


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Star Rating — 星級評分
# 互動式評分 / 唯讀展示
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

star-rating:
  gap:            4px
  activeFilter:   none
  inactiveFilter: 'grayscale(1) opacity(0.35)'

  sizes:
    sm:  { fontSize: 14px, gap: 2px }
    md:  { fontSize: 20px, gap: 4px }

  interactive:
    hoverTransform: scale(1.1)
    transition:     150ms
    cursor:         pointer

  readonly:
    cursor:         default
    pointerEvents:  none

  label:
    fontSize:   13px
    color:      '#595959'
    marginLeft: 6px
    format:     '{value} / 5.0'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Sidebar / Nav — 左側導覽列（Light）
# 後台主要佈局元件
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

sidebar:
  width:          240px
  widthCollapsed: 56px                          # 收折狀態，icon-only
  bg:             '#FFFFFF'
  border:         '1px solid #D9D9D9'
  radius:         14px
  shadow:         '0 2px 8px rgba(0,0,0,0.06)'

  # ── 圖標規格（此元件單獨使用 Feather Icons）──
  icon:
    family:       'Feather Icons'               # 全站統一 Feather
    size:         20px
    stroke-width: 2
    stroke-linecap:  round
    stroke-linejoin: round
    fill:         none
    color-default: '#8C8C8C'
    color-active:  '#0A2B41'

  # ── Logo 區 ──────────────────────────
  logo:
    height:       56px                          # 與 topbar 同高
    padding:      '0 14px'
    borderBottom: '1px solid #F0F0F0'
    display:      flex / alignItems center / justifyContent space-between

    img:
      tag:        '<img>'
      height:     24px
      widthAuto:  true
      align:      left                          # 靠左對齊
      collapsed:  hidden                        # 收折時隱藏

    collapse-btn:                               # PRO badge 已移除，改為收折按鈕
      icon:       sidebar                       # Feather Icons
      size:       18px
      btnSize:    28px
      radius:     6px
      color:      '#8C8C8C'
      hoverBg:    '#F0F0F0'
      position-expanded:  right                 # 展開時靠右
      position-collapsed: center                # 收折時置中

  # ── 搜尋框 ────────────────────────────
  search:
    margin:     '10px 12px'
    height:     34px
    bg:         '#FAFAFA'
    border:     '1px solid #D9D9D9'
    radius:     8px
    padding:    '7px 10px'
    icon:       { name: search, size: 14px, color: '#8C8C8C' }
    placeholder:{ fontSize: 12px, color: '#BFBFBF' }
    shortcut:   { fontSize: 10px, color: '#8C8C8C', keys: '⌘/' }
    collapsed:  hidden

  # ── 捲動導覽區 ────────────────────────
  nav:
    paddingY:   4px
    scrollbar:  { width: 4px, thumb: '#D9D9D9', radius: 2px }

  # ── Section heading ───────────────────
  section-heading:
    fontSize:      12px                         # 10px → 12px
    fontWeight:    400                          # 600 → 400（細體）
    letterSpacing: 0.06em
    textTransform: uppercase
    color:         '#BFBFBF'
    padding:       '16px 16px 6px'             # 10px 16px 4px → 16px 16px 6px
    collapsed:     hidden

  # ── Nav item ──────────────────────────
  nav-item:
    icon-size:  16px                            # v2.2：20px → 16px
    padding:    '10px 12px'                     # 7px 12px → 10px 12px
    margin:     '1px 8px'
    radius:     8px
    fontSize:   14px                            # v2.2 調整為 14px
    gap:        8px
    states:
      default:  { bg: transparent,  color: '#595959', weight: 400 }
      hover:    { bg: '#FAFAFA',    color: '#1F1F1F', weight: 400 }
      active:   { bg: '#E7EAEC',    color: '#0A2B41', weight: 500 }
      disabled: { color: '#BFBFBF', pointerEvents: none }
    icon-color:
      default:  '#8C8C8C'
      active:   '#0A2B41'
    badge:
      marginLeft: auto
      fontSize:   10px
      fontWeight: 600
      padding:    '1px 6px'
      radius:     9999px
      variants:
        blue:   { bg: '#E6F4FF', color: '#0958D9' }
        amber:  { bg: '#FFFCF0', color: '#AD6800' }
        green:  { bg: '#F6FFED', color: '#389E0D' }
        gray:   { bg: '#FAFAFA', color: '#8C8C8C', border: '1px solid #D9D9D9' }
    chevron:
      icon:       chevron-right                 # Feather Icons
      size:       14px
      color:      '#BFBFBF'
      openIcon:   chevron-up
      transition: 200ms

  # ── Sub-item ──────────────────────────
  sub-item:
    paddingLeft: 10px
    fontSize:    13px                           # 12px → 13px
    padding:     '8px 10px'                    # 5px 10px → 8px 10px
    dot:
      size:          5px
      shape:         circle
      color-default: '#BFBFBF'
      color-active:  '#0A2B41'

  # ── Spaces 區 ─────────────────────────
  spaces:
    item:   { padding: '9px 12px', margin: '1px 8px', radius: 8px, hoverBg: '#FAFAFA' }
    dot:    { size: 8px, radius: 2px }
    name:   { fontSize: 14px, color: '#595959' }

  # ── Favorites 已移除 ──────────────────
  # favorites: removed

  # ── User card 已移除（v2.2）──────────
  # 帳號區塊移至 Top Header 右側使用者選單，避免與 Top Header 重複。
  # Sidebar 不再包含底部 user-card。
  user-card: removed

  # ── 收折狀態 ──────────────────────────
  collapsed:
    width:        56px
    logo:         hidden
    search:       hidden
    nav-label:    hidden
    nav-badge:    hidden
    section-heading: hidden
    spaces:       hidden
    user-info:    hidden
    icon:         { justify: center, padding: '11px 0' }
    collapse-btn: { justify: center }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Page Header — 頁面標題列
# 每個後台頁面頂部的標題 + 操作區
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

page-header:
  responsive:                                  # v2.2：防止標題與操作按鈕擠壓
    layout:    'flex-wrap：標題區 flex:1 min-width:240px（過長省略）；操作區 flex-shrink:0'
    behavior:  '寬度不足時操作按鈕整組換行至標題下方、靠左（換行堆疊）'
    applies-to: '所有「左標題 + 右操作」列：Page Header、Table Toolbar、Panel 標題列'

  bg:       '#FFFFFF'
  border:   '1px solid #D9D9D9'
  radius:   12px
  padding:  '20px 24px'
  layout:   space-between

  breadcrumb:
    fontSize:     12px
    color:        '#8C8C8C'
    separator:    '/'
    active:       { color: '#1F1F1F', weight: 500 }
    marginBottom: 4px

  title:
    fontSize:   20px
    fontWeight: 600
    color:      '#1F1F1F'

  description:
    fontSize:   13px
    color:      '#8C8C8C'
    marginTop:  2px

  actions:
    display:    flex
    gap:        8px
    alignItems: center
    flexShrink: 0

  tabs-variant:
    borderTop:  '1px solid #F0F0F0'
    marginTop:  16px


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Stat Card — KPI 數字卡片
# 儀表板數字摘要、趨勢指示
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

stat-card:
  # v2.2：圖標色塊 + 標籤 + 主數字 + 副指標細分（一卡一指標）
  bg:       '#FFFFFF'
  border:   '1px solid #E7EAEC'
  radius:   12px
  padding:  '18px 20px'
  minWidth: 180px

  icon-badge:
    size:    36px
    radius:  9px
    # 淺底用語意色系，圖示為對應語意色 Feather 18px
    tints:
      info:    { bg: '#E6F4FF', icon: '#1677FF' }
      success: { bg: '#F6FFED', icon: '#389E0D' }
      warning: { bg: '#FFFCF0', icon: '#D68C24' }
      error:   { bg: '#FFF1F0', icon: '#CF1322' }
      brand:   { bg: '#E7EAEC', icon: '#0A2B41' }
    icon-size: 18px

  label:
    fontSize:   13px
    color:      '#8C8C8C'
    gap:        10px            # 與圖標色塊間距

  value:
    fontSize:   28px
    fontWeight: 600
    color:      '#1F1F1F'
    lineHeight: 1.1

  sub-metrics:                  # 副指標細分，可 0–3 項，可省略
    fontSize:   12px
    gap:        14px
    label-color: '#8C8C8C'
    value:      { fontWeight: 600, color: 'semantic | #434343' }

  layout:     "等寬並排 gap 16px；對應 RWD：≥1440 五欄、1024–1440 兩三欄、<1024 單欄"
  note:       "一卡一指標用 Stat Card；一卡多指標用 Metric Group"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pagination — 翻頁控制
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pagination:
  gap:    4px

  button:
    minWidth: 32px
    height:   32px
    radius:   8px
    fontSize: 13px
    bg:       '#FFFFFF'
    border:   '1px solid #D9D9D9'
    color:    '#595959'
    paddingX: 8px
    states:
      hover:    { borderColor: '#BFBFBF', color: '#1F1F1F' }
      active:   { bg: '#0A2B41', borderColor: '#0A2B41', color: '#FFFFFF', weight: 500 }
      disabled: { opacity: 0.4, pointerEvents: none }

  ellipsis:
    color:   '#8C8C8C'
    padding: '0 4px'
    fontSize: 13px

  info-label:
    fontSize:   13px
    color:      '#8C8C8C'
    marginLeft: 8px

  variants:
    full:   page-numbers + prev/next
    simple: prev/next buttons + info label


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Empty State — 空狀態佔位
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

empty-state:
  textAlign: center
  padding:   '40px 24px'
  bg:        '#FFFFFF'
  border:    '1px solid #D9D9D9'
  radius:    12px

  icon:
    size:         56px
    bg:           '#FAFAFA'
    border:       '1px dashed #D9D9D9'
    radius:       14px
    fontSize:     22px
    marginBottom: 16px

  title:
    fontSize:     15px
    fontWeight:   600
    marginBottom: 6px

  description:
    fontSize:     13px
    color:        '#8C8C8C'
    maxWidth:     280px
    marginBottom: 20px
    lineHeight:   1.6

  action: button-primary (optional)

  variants:
    default:      standard padding + CTA button
    search-empty:
      padding:       '24px 16px'
      border-style:  dashed
      icon-size:     40px
      title-size:    14px
      description-size: 12px
      action:        none


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Notification Item — 通知列表項目
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

notification-item:
  padding:      '14px 16px'
  gap:          12px
  borderBottom: '1px solid #F0F0F0'
  hoverBg:      '#FAFAFA'
  transition:   150ms

  unread:
    bg:       '#F0F4FF'
    hoverBg:  '#E8EFFE'
    dot:      { size: 7px, color: '#1677FF', position: 'absolute right 16px vcenter' }

  type-icon:
    size:   16px
    radius: 50%
    border: '2px solid #FFFFFF'
    variants:
      comment:  { bg: '#1677FF' }
      task:     { bg: '#FDB338' }
      success:  { bg: '#52C41A' }
      alert:    { bg: '#F5222D' }

  text:
    fontSize:    13px
    color:       '#1F1F1F'
    lineHeight:  1.5
    name-weight: 600

  meta:
    fontSize: 11px
    color:    '#8C8C8C'
    marginTop: 3px

  inline-actions:
    gap:         6px
    marginTop:   8px
    button-size: sm

  panel:
    width:      400px
    maxHeight:  520px
    bg:         '#FFFFFF'
    border:     '1px solid #D9D9D9'
    radius:     12px
    shadow:     '0 8px 24px rgba(0,0,0,0.1)'
    header:     { padding: '14px 16px', borderBottom: '1px solid #F0F0F0', fontSize: 14px, fontWeight: 600 }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# User Row — 用戶複合列
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

user-row:
  padding:    '12px 16px'
  gap:        12px
  bg:         '#FFFFFF'
  border:     '1px solid #D9D9D9'
  radius:     10px
  hoverBg:    '#FAFAFA'
  transition: 150ms

  avatar:
    size:       36px
    radius:     50%
    fontSize:   13px
    fontWeight: 600
    status-dot: { size: 10px, border: '2px solid #FFFFFF' }
    dot-colors:
      online:  '#52C41A'
      away:    '#FDB338'
      offline: '#BFBFBF'

  info:
    name:   { fontSize: 14px, fontWeight: 500, color: '#1F1F1F' }
    email:  { fontSize: 12px, color: '#8C8C8C' }

  right:
    gap:    8px
    badge:  status badge
    action: ghost button sm

  table-variant:
    border:   none
    radius:   0
    padding:  '0 4px'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Date Picker — 日期選擇器
# 單日 / 日期範圍
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

date-picker:
  bg:       '#FFFFFF'
  border:   '1px solid #D9D9D9'
  radius:   12px
  padding:  16px
  width:    280px
  shadow:   '0 8px 24px rgba(0,0,0,0.1)'
  zIndex:   1050

  header:
    marginBottom: 12px
    month-label:  { fontSize: 14px, fontWeight: 600 }
    nav-btn:      { size: 28px, radius: 6px, border: '1px solid #D9D9D9', hoverBg: '#FAFAFA' }

  weekdays:
    fontSize:   11px
    fontWeight: 500
    color:      '#8C8C8C'

  day:
    aspectRatio: 1
    radius:      6px
    fontSize:    13px
    states:
      default:     { color: '#595959', hoverBg: '#FAFAFA' }
      today:       { color: '#0A2B41', fontWeight: 600 }
      selected:    { bg: '#0A2B41', color: '#FFFFFF', fontWeight: 500 }
      in-range:    { bg: '#E7EAEC', color: '#0A2B41' }
      other-month: { color: '#BFBFBF' }
      disabled:    { color: '#BFBFBF', cursor: not-allowed }

  footer:
    borderTop:  '1px solid #F0F0F0'
    marginTop:  12px
    paddingTop: 12px
    today-link: ghost button sm
    actions:    [cancel secondary-sm, confirm primary-sm]

  trigger-input:
    height:      40px
    paddingLeft: 36px
    icon:        { name: calendar_month, left: 12px, size: 16px, color: '#8C8C8C' }

  range-variant:
    two-inputs:    start-date → end-input
    gap:           6px
    separator:     '→'
    focused-input: { borderColor: '#0A2B41', shadow: '0 0 0 3px rgba(10,43,65,0.08)' }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Top Header — 全域頂欄（v2.2 新增）
# 位於 content 區內（Sidebar 通頂），sticky 固定
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

top-header:
  height:       56px
  bg:           '#FFFFFF'
  border-bottom: '1px solid #F0F0F0'
  padding:      '0 16px'
  position:     'sticky top'
  scroll-shadow: '0 1px 2px rgba(0,0,0,0.04)'

  left:         Breadcrumbs                  # 13px，當前層 500 #1F1F1F；末段為當前頁
  right:        [search, bell, avatar]       # v2.2：搜尋 icon（開 Command Palette）→ 通知 → 頭像
  removed:      help-circle                  # v2.2 移除幫助鈕

  icon-button:
    size:       32px
    radius:     6px
    icon:       18px Feather '#595959'
    hoverBg:    '#F0F0F0'
    gap:        8px
  notify-dot:   { size: 8px, color: '#F5222D', border: '1.5px #FFFFFF' }
  search:       'icon 按鈕（非常駐輸入框）；點擊或 ⌘K 開啟 Command Palette'
  avatar:       '28px 圓形 + chevron-down；點擊開使用者下拉（個人資料／帳號設定／登出[danger]）'
  divider:      '頭像前 1px #F0F0F0 分隔，高 20px'

  # 分工（v2.2 更新）：搜尋改為 Top Header 右側 icon（開 Palette）；麵包屑在左；頁面標題與操作 → Page Header
  responsibility: "Top Header：左麵包屑 + 右側搜尋 icon／通知／頭像；不放常駐搜尋框、不放幫助"



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Command Palette — 全域指令／搜尋（v2.2 新增）
# 由 Top Header 搜尋 icon 或 ⌘K / Ctrl+K 開啟
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

command-palette:
  trigger:      'Top Header 搜尋 icon、或鍵盤 ⌘K / Ctrl+K'
  overlay:      'rgba(0,0,0,0.4) 全屏遮罩，z-index 1200（同 modal 層級）'
  position:     '置中偏上，距頂 120px'
  panel:        '寬 560（max 90vw）/ 圓角 12 / shadow 0 20px 60px rgba(0,0,0,0.15)'
  input:
    height:     '約 48（padding 14px 16px）'
    icon:       '左側 search 18px #8C8C8C'
    placeholder:'搜尋客戶、任務、關鍵字…'
    esc-hint:   '右側 ESC 鍵提示（11px / 邊框 pill）'
  list:
    section:    '分組標題 11px #BFBFBF uppercase（快速操作／前往…）'
    item:       '高 約 40 / 圓角 8 / icon 16px + 標籤 14px / hover #FAFAFA'
    max-height: '360px，超出捲動'
  close:        '點遮罩、按 ESC、或選取項目後關閉'
  behavior:     '可搜功能、客戶、任務；鍵盤上下選擇、Enter 執行（實作層）'

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Metric Group — 指標組（v2.2 新增）
# 一卡多指標橫排，共用標題，對應「本月預測」「本週摘要」
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

metric-group:
  bg:       '#FFFFFF'
  border:   '1px solid #E7EAEC'
  radius:   12px
  padding:  '20px 24px'

  title:    { fontSize: 14px, fontWeight: 600, color: '#1F1F1F', marginBottom: 18px }
  metrics:  { layout: 'space-around', align: center }
  metric-label: { fontSize: 13px, color: '#8C8C8C', marginBottom: 8px }
  metric-value: { fontSize: 24px, fontWeight: 700, color: 'semantic | #1F1F1F' }
  footer:   { fontSize: 13px, color: '#BFBFBF', borderTop: '1px solid #F0F0F0', optional: true }

  count:    "建議 2–5 個指標；過多改用多張卡或表格"
  note:     "一卡一指標且醒目 → Stat Card；一卡多指標緊湊 → Metric Group"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Chart — 圖表（v2.2 新增）
# SVG 繪製，無外部圖表庫；配色見 DESIGN.md › data-viz
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

chart:
  implementation: inline SVG
  palette:        Blue 色階（同色系深淺，見 DESIGN.md）
  single-series:  '#1677FF'                  # 主藍

  line:
    stroke:       '2px 主色 / 圓端點'
    point:        '半徑 3.5 / 白底 + 2px 描邊 / hover tooltip'
    area-fill:    '主色 6% 透明（選用）'
    gridline:     '水平 1px #F0F0F0；無垂直格線'

  bar:
    radius:       4px
    width:        '上限 36px、約欄寬 56%'
    gridline:     '水平 1px #F0F0F0'

  pie-donut:
    slice:        '依色板取色 / 圓餅含 1.5px 白色分隔'
    donut-inner:  '外徑 60%；中心可放總計（22px 600）'
    legend:       '右側直列：色塊 10×10 圓角 3 + 標籤 13px + 數值 mono 12px'
    max-categories: 6

  stage-bar:                                 # 階段分布橫條
    序號:   '20×20 圓角 5 / #F0F0F0 / 11px 600 #8C8C8C'
    label:  '13px #434343 固定寬'
    bar:    '高 14px / 圓角 7 / 軌道 #F0F0F0 / 填充主藍 / 過場 width .4s'
    pct:    '13px #1F1F1F 靠右'
    count:  '13px mono #8C8C8C 靠右'
    row-gap: 12px

  ranking-bar:                               # 排行橫條
    bar:    '高 18px / 圓角 5 / 軌道 #F5F5F5 / 長度 = 值÷最大值'
    normal: '主藍'
    warning: '超門檻用 #F5222D，數值同步轉紅'
    sort:   '由大到小'

  segmented-bar:                             # 分段比例條
    bar:    '高 32px / 圓角 8 / 整體 100% / 段間 2px 白縫'
    segment: '依色板取色 / 段內置中白字 13px 500'
    count:  '建議 2–4 段'

  states:
    empty:    "置中『尚無資料』13px #BFBFBF"
    loading:  "Spinner 置中"
    tooltip:  "深色 #1F1F1F / 圓角 6 / 白字"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Table Toolbar — 表格工具列（v2.2 新增）
# 表格上方查詢與操作列，勾選後切換批次操作列
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

table-toolbar:
  container:    '與表格同一張卡片（圓角 12），位於表頭上方'
  height:       64px
  padding:      '12px 16px'
  border-bottom: '1px solid #F0F0F0'
  gap:          8px

  layout:       '左：搜尋 → 篩選 → 已套用標籤；右：次要操作 → 主操作（最右）'
  search:       'Input md 40px / 寬 220px / 內嵌 search icon 14px #BFBFBF'
  filter-tag:   '高 28 / pill / 12px / 可單獨移除（× icon 12px）'

  batch-bar:                                 # 勾選 ≥1 列時整條取代
    bg:           '#F0F7FF'
    border-bottom: '1px solid #BAD9FF'
    left:         '已選 N 筆（14px 500 #0A2B41，數字 600） → 取消選取（13px #1677FF）'
    right:        '批次操作（危險操作放最右，不使用紅色 hover）'
    exit:         '取消選取、全部取消勾選、或操作完成後自動清空'

  select-col:   '寬 48px / checkbox 16px 圓角 4 / 表頭支援全選與半選'
  selected-row: '背景 #F0F7FF（高於 hover #FAFAFA）'

  # Row Actions（列操作區）
  row-actions:
    column:       '固定最右欄，表頭「操作」，內容靠右'
    max-visible:  '4 顆 + 更多；順序 eye → edit-2 → trash-2 → more-horizontal（複製等低頻收進更多）'
    button:       '24×24 圓形 / bg #F0F0F0 / hover #E5E5E5 / icon 14px #595959→#434343'
    no-red-hover: true                       # 所有按鈕統一灰階，無紅色變化
    danger:       '不用紅色樣式；刪除以 Modal 二次確認'
    tooltip:      'hover 顯示操作名稱，按鈕上方 8px（沿用 Tooltip 樣式）'
    more-menu:    '對齊按鈕右緣向下展開 / 點外部關閉 / 收納低頻操作'
    event:        'stopPropagation，不觸發列點擊與勾選'
    overflow:     '欄位過多時表格 overflow-x:auto，操作欄 position:sticky right:0 固定右側（-4px 0 8px 陰影區隔），永遠可見'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Description List — 描述列表（v2.2 新增）
# 詳情頁 label–value 成對排列
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

description-list:
  label:    { fontSize: 13px, color: '#8C8C8C' }
  value:    { fontSize: 14px, color: '#1F1F1F', lineHeight: 22px }
  empty:    "顯示「–」#BFBFBF；不留空白、不寫「無」"

  horizontal:                                # 水平式
    label-width:  '120px（依最長 label 可調 96–160）'
    row-padding:  '10px 0'
    divider:      '1px #F5F5F5'

  grid:                                      # 網格式
    columns:      '2–3 欄'
    column-gap:   32px
    row-gap:      16px
    label:        '在上，與 value 間距 4px'

  copyable-value: 'mono 13px + 複製按鈕 24×24（icon 14px / hover #F0F0F0）/ 複製後轉 check #389E0D'
  status-value:   '沿用 Badge md（12px / padding 2px 8px / pill）'
  responsive:     '網格式 <1200 降 2 欄、<768 降 1 欄'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Steps — 步驟條（v2.2 新增）
# 多步驟流程導航，三態
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

steps:
  circle:       '28×28 / 數字 13px / 完成後換 check 14px'
  title:        '13px / 與圓圈間距 8px / 進行中 600、其餘 400'
  connector:    '高 2px / 圓角 1 / 已完成段 #0A2B41、未完成段 #E5E7EB / 過場 200ms'

  states:
    done:       '圓 #0A2B41 + check #FFFFFF；標題 #434343；可點擊返回'
    current:    '白底 + 2px #0A2B41 邊框 / 數字 600 #0A2B41；標題 600 #1F1F1F'
    upcoming:   '白底 + 1.5px #D9D9D9 邊框 / 數字 #BFBFBF；標題 #BFBFBF；不可點擊'

  navigation:   '已完成步驟可點擊返回；未完成步驟不可跳轉'
  buttons:      '靠右：上一步在左、下一步／完成在右（精靈慣例，見 DESIGN.md button-conventions）'
  count:        '建議 3–5 步；超過應重新切分流程'
  responsive:   '<768 僅顯示進行中步驟與「第 N 步，共 M 步」'


---
