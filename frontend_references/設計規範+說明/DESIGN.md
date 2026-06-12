---
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Youni Lab Design System
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

name:          Youni Lab Design System
version:       "2.1"
token_source:  Figma Variables
architecture:  ref → sys → comp


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Philosophy — 設計理念
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

philosophy:

  - principle:    Human-Centered
    description:  AI is a collaborative partner, not just a tool.
                  The interface should minimize cognitive load.

  - principle:    Natural Interaction
    description:  Reduce learning cost through natural language
                  and clear structure.

  - principle:    Warm Trust
    description:  Deliver a stable, reassuring experience
                  under rigorous information architecture.


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Principles — 設計原則
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

principles:

  - name:  Restraint is Power
    rule:  Brand colors gain impact through scarcity.
           Primary navy appears only at highest-weight interaction points.
           Accent amber ≤5% of screen area.

  - name:  Strong Spatial Contrast
    rule:  Dark navigation + white workspace.
           Sidebar provides spatial orientation.
           Main area stays white for maximum readability.

  - name:  Spacious Immersive
    rule:  Layout density between standard SaaS and marketing sites.
           Generous card gaps (24px), comfortable row heights (48px),
           ample padding (20-24px).

  - name:  Progressive Radius
    rule:  Larger elements get larger radius.
           12px cards > 8px buttons > 6px badges > 4px small elements.
           No 0px sharp corners. No >16px except full.

  - name:  Weight-Driven Hierarchy
    rule:  Hierarchy through font weight first, color second, size last.
           Regular → Medium → Semibold → Bold.
           Max 5 font sizes per page.

  - name:  Minimal Tables
    rule:  Horizontal dividers only. No vertical lines.
           Low-profile headers. 48px row height.
           Hover feedback with subtle gray.

  - name:  Clear Intent
    rule:  "Button pairs: outline cancel + filled confirm (confirm on right).
           Danger = red fill. Add item = dashed border.
           Labels use verb + noun."

  - name:  Tonal Layering over Shadows
    rule:  Depth through color tones and borders, not heavy shadows.
           Shadows only for floating elements
           (modal, drawer, card hover, focus ring).

  - name:  Brand Consistency
    rule:  Logo min height 32px, 2x clearance.
           Dark logo on light bg, white logo on dark bg.
           No logo on complex backgrounds.


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Colors — 色彩系統
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

colors:

  # Brand ─────────────────────────────
  primary:          '#0A2B41'
  primary-hover:    '#2E4A5E'
  primary-pressed:  '#061A28'
  primary-light:    '#E7EAEC'

  accent:           '#FDB338'
  accent-hover:     '#FFC861'
  accent-pressed:   '#D68C24'

  # Semantic ──────────────────────────
  info:             '#1677FF'
  info-light:       '#E6F4FF'
  info-text:        '#0958D9'
  info-border:      '#91CAFF'

  success:          '#52C41A'
  success-light:    '#F6FFED'
  success-text:     '#389E0D'
  success-border:   '#B7EB8F'

  warning:          '#FDB338'
  warning-light:    '#FFFCF0'
  warning-text:     '#AD6800'
  warning-border:   '#FFC861'

  error:            '#F5222D'
  error-light:      '#FFF1F0'
  error-text:       '#CF1322'
  error-border:     '#FFA39E'

  # Text ──────────────────────────────
  text-primary:     '#1F1F1F'
  text-secondary:   '#595959'
  text-description: '#8C8C8C'
  text-disabled:    '#BFBFBF'
  text-inverse:     '#FFFFFF'

  # Surface ───────────────────────────
  surface-page:     '#F5F5F5'
  surface-default:  '#FFFFFF'
  surface-secondary:'#FAFAFA'
  surface-tertiary: '#F5F5F5'
  surface-disabled: '#F0F0F0'
  surface-inverse:  '#1F1F1F'

  # Border ────────────────────────────
  border-default:   '#D9D9D9'
  border-strong:    '#BFBFBF'
  border-subtle:    '#F0F0F0'
  overlay:          'rgba(0,0,0,0.4)'

  # Ratio ─────────────────────────────
  color-ratio:
    white-gray:     '70-75%'
    navy:           '15-20%'
    semantic:       '5-8%'
    amber:          '≤5%'

  # Scales (ref) ──────────────────────
  theme-scale:
    - '#E7EAEC'  # 50
    - '#C4CDD3'  # 100
    - '#9AABB7'  # 200
    - '#718491'  # 300
    - '#4D6577'  # 400
    - '#2E4A5E'  # 500
    - '#0A2B41'  # 600 ← primary
    - '#082335'  # 700
    - '#061A28'  # 800
    - '#04111B'  # 900

  blue-scale:
    - '#E6F4FF'  # 50
    - '#BAE0FF'  # 100
    - '#91CAFF'  # 200
    - '#69B1FF'  # 300
    - '#4096FF'  # 400
    - '#1677FF'  # 500
    - '#0958D9'  # 600
    - '#003EB3'  # 700

  green-scale:
    - '#F6FFED'  # 50
    - '#D9F7BE'  # 100
    - '#B7EB8F'  # 200
    - '#95DE64'  # 300
    - '#73D13D'  # 400
    - '#52C41A'  # 500
    - '#389E0D'  # 600

  orange-scale:
    - '#FFFCF0'  # 50
    - '#FFF1B8'  # 100
    - '#FFC861'  # 200
    - '#FDB338'  # 300 ← accent
    - '#F09C20'  # 400
    - '#D68C24'  # 500
    - '#AD6800'  # 600

  red-scale:
    - '#FFF1F0'  # 50
    - '#FFCCC7'  # 100
    - '#FFA39E'  # 200
    - '#FF7875'  # 300
    - '#FF4D4F'  # 400
    - '#F5222D'  # 500
    - '#CF1322'  # 600

  neutral-scale:
    - '#FFFFFF'  # 0
    - '#FAFAFA'  # 50
    - '#F5F5F5'  # 100
    - '#F0F0F0'  # 200
    - '#D9D9D9'  # 300
    - '#BFBFBF'  # 400
    - '#8C8C8C'  # 500
    - '#595959'  # 600
    - '#434343'  # 700
    - '#262626'  # 800
    - '#1F1F1F'  # 900
    - '#000000'  # 1000

  purple-scale:
    - '#F5F3FF'  # 50
    - '#EDE9FE'  # 100
    - '#DDD6FE'  # 200
    - '#C4B5FD'  # 300
    - '#A78BFA'  # 400
    - '#8B5CF6'  # 500
    - '#7C3AED'  # 600
    - '#6D28D9'  # 700


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Typography — 字體排版
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

typography:

  font-family:      "'Inter', 'Noto Sans TC', -apple-system, sans-serif"
  font-family-mono: "'IBM Plex Mono', 'Menlo', monospace"

  #               size    weight  lineHeight
  display:      { size: 36px, weight: 700, lineHeight: 44px }
  h1:           { size: 28px, weight: 700, lineHeight: 36px }
  h2:           { size: 24px, weight: 600, lineHeight: 32px }
  h3:           { size: 20px, weight: 600, lineHeight: 28px }
  h4:           { size: 16px, weight: 600, lineHeight: 24px }
  body-lg:      { size: 16px, weight: 400, lineHeight: 24px }
  body-md:      { size: 14px, weight: 400, lineHeight: 22px }
  body-sm:      { size: 13px, weight: 400, lineHeight: 20px }
  caption:      { size: 12px, weight: 400, lineHeight: 18px }
  overline:     { size: 11px, weight: 500, lineHeight: 16px, letterSpacing: 0.06em }
  label:        { size: 13px, weight: 500, lineHeight: 18px }
  code:         { size: 13px, weight: 400, lineHeight: 20px, family: mono }
  data-lg:      { size: 28px, weight: 600, lineHeight: 36px }
  data-md:      { size: 20px, weight: 600, lineHeight: 28px }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Spacing / Radius / Border — 間距系統
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

spacing:
  base:   8px
  xs:     2px
  sm:     4px
  md:     8px
  lg:     16px
  xl:     24px
  2xl:    32px
  3xl:    48px
  4xl:    64px

rounded:
  none:   0px
  sm:     4px       # small button, checkbox
  md:     8px       # button, input, toast
  lg:     12px      # card, table, modal
  xl:     16px
  full:   9999px    # pill, avatar, switch

border:
  default:  1px
  medium:   1.5px   # checkbox, radio, choicebox
  strong:   2px     # focus indicator, tab underline


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Shadow / Opacity / Animation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

shadow:
  xs:           '0 1px 2px rgba(0,0,0,0.05)'
  sm:           '0 1px 3px rgba(0,0,0,0.08)'       # card hover, toggle
  md:           '0 4px 6px rgba(0,0,0,0.07)'       # dropdown
  lg:           '0 8px 24px rgba(0,0,0,0.1)'       # drawer
  xl:           '0 20px 60px rgba(0,0,0,0.15)'     # modal
  focus:        '0 0 0 3px rgba(10,43,65,0.08)'    # focus ring
  error-focus:  '0 0 0 3px rgba(245,34,45,0.08)'   # error focus ring

opacity:
  disabled:     0.4
  hover:        0.85
  overlay:      0.4

animation:
  fast:         150ms     # hover, focus
  normal:       200ms     # switch, transform
  slow:         250ms     # drawer slide
  progress:     400ms     # progress bar fill
  spinner:      1s        # spinner rotation
  easing:       ease


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Layout — 佈局
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

layout:
  sidebar:
    width:      220-260px
    bg:         primary
  content:
    maxWidth:   1200px
  density:      spacious-immersive
  card-gap:     24px
  card-padding: 24px
  table-row-height: 48px


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Icon System — 圖示系統（v2.1 新增）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

icon-system:

  library:        Google Material Symbols
  style:          Rounded
  cdn:            "https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,300,0,0"

  # 預設軸值（font-variation-settings）
  default-axes:
    FILL:   0       # 線條風格（0 = outline, 1 = filled）
    wght:   300     # 筆畫粗細（Light）
    GRAD:   0
    opsz:   20      # 光學尺寸

  # 情境軸值規則
  filled-rule: "FILL:1 僅用於 active/selected 狀態，或需要強調的場景"
  weight-rule: "導覽 icon 用 300，強調用 400"

  # 尺寸對照
  sizes:
    xs:   14px    # 徽章、標籤內
    sm:   16px    # 按鈕、輸入框
    md:   18px    # 導覽列（Sidebar nav item 標準）
    lg:   20px    # 大型按鈕、標題旁
    xl:   24px    # 空狀態圖示

  # 顏色規則
  color-rule:
    nav-default:  '#8C8C8C'     # 未選中導覽圖示
    nav-active:   '#0A2B41'     # 選中導覽圖示
    button:       inherit       # 繼承按鈕文字色
    muted:        '#BFBFBF'     # 禁用 / 輔助


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Admin Layout — 後台佈局規格（v2.1 新增）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

admin-layout:

  type:           sidebar + topbar + main-content

  sidebar:
    width:        240px
    widthCollapsed: 56px                        # 收折狀態，icon-only
    bg:           '#FFFFFF'
    style:        Light Sidebar                 # 白底深字（參考 Metronic Demo6）
    position:     fixed left                    # 固定左側

    logo:
      height:       56px                        # 與 topbar 同高
      padding:      '0 14px'
      img:          { tag: '<img>', height: 24px, widthAuto: true }
      collapse-btn:
        icon:       sidebar                     # Feather Icons
        size:       18px
        position:   right                       # 展開時靠右，收折時置中
        radius:     6px
        hoverBg:    '#F0F0F0'

    collapsed:
      width:        56px
      logo:         hidden
      nav-label:    hidden
      section-heading: hidden
      nav-badge:    hidden
      search:       hidden
      spaces:       hidden
      user-info:    hidden
      icon:         centered

  topbar:
    height:       60px
    bg:           '#FFFFFF'
    border:       '1px solid #F0F0F0'
    shadow:       '0 1px 3px rgba(0,0,0,0.05)'

  content:
    marginLeft:   240px                      # 對應 sidebar 寬度
    padding:      '24px 32px'
    bg:           '#F5F5F5'                  # surface-page
    minHeight:    100vh
    maxWidth:     none                       # 全寬，內部 card 自行約束

  page-max-width:  1200px                    # 內容區最大寬度

  breakpoints:
    collapse-sidebar: 1024px                 # 以下 sidebar 收折
    mobile:           768px


---
