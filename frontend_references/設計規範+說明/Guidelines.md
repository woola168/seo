# Youni Lab 設計系統指南

---

## 設計理念

### 以人為本

AI 是協作夥伴，而不是單純工具。界面應該降低理解成本——使用者不需要學習「如何操作 AI」，而是 AI 主動適應人的思考方式。這意味著：資訊架構要清晰直覺、操作路徑要可預測、回饋要即時可見。

### 自然互動

透過自然語言與清晰結構，減少學習成本。使用者用自己的話描述需求，系統用結構化的結果回應。界面的視覺語言也遵循同樣邏輯——用顏色暗示語意、用間距劃分層次、用動態回饋確認操作，讓每一步互動都感覺「理所當然」。

### 有溫度的信任

在嚴謹的資訊架構下，提供穩定、安心的使用體驗。信任來自一致性——相同的操作永遠產生相同的結果，相同的顏色永遠代表相同的意義。柔和的圓角、充足的留白、克制的品牌色，共同營造出專業但不冰冷的氛圍。

---

## 一、設計原則

> 以下 9 條原則是所有視覺決策的依據。具體數值請見第二節。

---

### 原則 1：克制即力量

品牌色的影響力來自稀缺，而非鋪張。深海軍藍只出現在最高權重的互動節點（側邊欄、主按鈕、標題），琥珀黃只做視覺焦點的最後一筆（Logo 圖示、極少數強調），用量控制在 5% 以下。

整體界面保持 70-75% 白色與淺灰，讓品牌色在大量留白中「呼吸」而非壓迫。

> 呼應理念「有溫度的信任」——克制的色彩讓界面穩定可預測，使用者不會被視覺噪音干擾。

---

### 原則 2：強對比分區

界面採用「深色導航 + 白色作業區」的雙色分區模式。深色側邊欄提供空間定位感，讓使用者一眼區分「我在哪」與「我在做什麼」。主要作業區保持純白，確保資料與文字的最高可讀性。

> 呼應理念「以人為本」——清晰的空間劃分降低認知負擔，使用者不需要思考就能定位自己。

---

### 原則 3：寬鬆沉浸

佈局密度定位為「寬鬆沉浸型」——介於一般 SaaS 與行銷官網之間。慷慨的卡片間距、充足的內部留白、舒適的表格行高，讓資料在空白中自然分組。

寧可留白過多，不要擁擠。這是為長時間數據分析場景設計的——降低視覺疲勞，讓使用者能專注在資料本身。

> 呼應理念「自然互動」——充足的呼吸空間讓資訊層次自然浮現，不需要額外的裝飾來劃分區塊。

---

### 原則 4：柔和漸進的圓角

拒絕生硬直角（0px）與過度圓潤（>16px）。在 4px 到 12px 之間建立遞進系統：大元件用大圓角，小元件用小圓角，形成天然的視覺層次。

唯一例外是 Pill 標籤（全圓角），這是「資料型態識別」的專屬視覺語言，不可濫用於一般 UI 標籤。

> 呼應理念「有溫度的信任」——中等圓角傳達專業但不冰冷的品牌調性。

---

### 原則 5：字重驅動層次

視覺層次首先透過字重建立（Regular → Medium → Semibold → Bold），其次是顏色（深 → 中 → 淺灰），最後才是字號。同一頁面控制在 5 種字號以內。

數據數字一律使用 Semibold，強化視覺衝擊力。次要資訊用灰色降權，而非縮小字號。

> 呼應理念「以人為本」——清晰的層次讓使用者的視線自然流動，不需要「找」重點。

---

### 原則 6：極簡表格

表格只使用水平分隔線，不使用垂直線或格線框。表頭低調（中灰、Medium），資料行慷慨（48-52px 行高）。操作圖示保持淺灰，hover 時才加深。

> 呼應理念「自然互動」——極簡的表格設計把注意力留給資料本身，減少視覺干擾。

---

### 原則 7：操作意圖清晰

所有操作場景遵循固定模式：

- **按鈕配對**：「輪廓取消 + 深色確認」，確認按鈕永遠在右側
- **危險操作**：使用紅色填充按鈕，打破深藍慣例，強化風險警示
- **新增引導**：清單末尾使用虛線邊框按鈕，視覺輕量但可操作性清晰
- **破壞性操作**：與 Toast 配對回饋（「刪除專案」→「專案已刪除」）

按鈕標籤使用「動詞 + 名詞」（儲存專案、刪除金鑰），避免裸動詞和通用確認。

> 呼應理念「自然互動」——固定的操作模式讓互動可預測，使用者不需要猜測下一步會發生什麼。

---

### 原則 8：色調分層取代陰影

深度透過色調差異和低對比邊框傳達，而非陰影堆疊。陰影僅用於真正「浮」在頁面上的元素：Modal、Drawer、Card hover、Focus ring。

靜態卡片、表格容器、側邊欄一律不加陰影，用邊框足矣。

---

### 原則 9：品牌一致性

- Logo 最小高度 32px，周邊安全距離為 Logo 高度的 2 倍
- 白色背景用深藍 Logo，深色背景用白色反白 Logo
- 圖形標誌可獨立使用（favicon、App icon）
- 禁止在彩色或複雜圖案背景上疊放 Logo

---

## 二、設計系統

> 本節提供色碼、字號、間距等具體數值。

---

### 2-1 色彩系統

#### 主色

| 名稱 | 色碼 | 用途 |
|------|------|------|
| Primary Navy | `#0A2B41` | 側邊欄、主按鈕、標題 |
| Brand Amber | `#FDB338` | Logo 點綴、視覺焦點（≤5%） |
| Blue Light | `#E6F0FF` | Pill 標籤背景、選中底色 |

**Primary 互動狀態：** Default `#0A2B41` → Hover `#2E4A5E` → Pressed `#061A28` → Disabled `#F0F0F0`

#### 語意色

| 名稱 | 填充 | 淺色背景 | 文字 / 邊框 |
|------|------|---------|------------|
| Info | `#1677FF` | `#E6F4FF` | `#0958D9` / `#91CAFF` |
| Success | `#52C41A` | `#F6FFED` | `#389E0D` / `#B7EB8F` |
| Warning | `#FDB338` | `#FFFCF0` | `#AD6800` / `#FFC861` |
| Error | `#F5222D` | `#FFF1F0` | `#CF1322` / `#FFA39E` |
| Purple | `#8B5CF6` | `#F5F3FF` | `#7C3AED` / `#DDD6FE` |

#### 中性色

| 名稱 | 色碼 | 用途 |
|------|------|------|
| Text Primary | `#1F1F1F` | 主體文字、標題 |
| Text Secondary | `#595959` | 表頭、輔助說明 |
| Text Description | `#8C8C8C` | Placeholder、禁用提示 |
| Text Disabled | `#BFBFBF` | 禁用狀態文字 |
| Text Inverse | `#FFFFFF` | 深色背景上的文字 |
| Border Default | `#D9D9D9` | 卡片邊框、分隔線 |
| Border Strong | `#BFBFBF` | 強調邊框 |
| Border Subtle | `#F0F0F0` | 表格行分隔 |
| Surface Default | `#FFFFFF` | 主要背景（≥70%） |
| Surface Secondary | `#FAFAFA` | 卡片背景、Hover 底色 |
| Surface Tertiary | `#F5F5F5` | 輸入框背景、斑馬紋 |
| Surface Disabled | `#F0F0F0` | 禁用元素背景 |
| Surface Page | `#F5F5F5` | 頁面底色 |
| Surface Inverse | `#1F1F1F` | Toast、Tooltip 背景 |

#### 色彩比例

| 類別 | 佔比 |
|------|------|
| 白色 / 淺灰系 | 70-75% |
| 深海軍藍系 | 15-20%（含側邊欄） |
| 輔助色 / 狀態色 | 5-8% |
| 琥珀黃點綴 | ≤ 5% |

---

### 2-2 字體排版

#### 字體選擇

| 語言 | 字體 | 用途 |
|------|------|------|
| 英文 & 數字 | Inter | UI 文字、數據展示 |
| 中文 | Noto Sans TC | 中文 UI 文字 |
| 程式碼 | IBM Plex Mono | 色碼、技術識別碼 |

```css
font-family: 'Inter', 'Noto Sans TC', -apple-system, BlinkMacSystemFont, sans-serif;
```

#### 字體層級

| 層級 | 字號 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| Display | 36px | Bold 700 | 44px | 大型數據展示 |
| H1 | 28px | Bold 700 | 36px | 頁面主標題 |
| H2 | 24px | Semibold 600 | 32px | 區塊標題 |
| H3 | 20px | Semibold 600 | 28px | 卡片標題 |
| H4 | 16px | Semibold 600 | 24px | 表單區塊標題 |
| Body Large | 16px | Regular 400 | 24px | 重要說明正文 |
| Body | 14px | Regular 400 | 22px | 標準正文、表格內容 |
| Body Small | 13px | Regular 400 | 20px | 次要說明、表頭 |
| Caption | 12px | Regular 400 | 18px | 輔助說明、時間戳記 |
| Overline | 11px | Medium 500 | 16px | 大寫標籤、分類名稱 |
| Label | 13px | Medium 500 | 18px | 表單 Label |
| Data Large | 28px | Semibold 600 | 36px | 重要 KPI |
| Data Medium | 20px | Semibold 600 | 28px | 圖表數值 |

---

### 2-3 圓角系統

| 元件類型 | 圓角 | 適用場景 |
|---------|------|---------|
| 大型卡片 | 12px | 內容卡片、Table 容器、Modal |
| Choicebox | 10px | 卡片式選擇器 |
| 按鈕 / 輸入框 | 8px | 按鈕（md/lg）、Input、Note、Toast |
| 小型元素 | 6px | Badge、Tooltip、Toggle button |
| 微型元素 | 4px | 按鈕（sm）、Checkbox |
| 全圓角 | full | Pill 標籤、Avatar、Switch、Progress |

**禁止：** 0px 直角、>16px 超大圓角（full 例外）

---

### 2-4 間距系統

#### 基礎網格（8px 單位）

| 等級 | 數值 | 典型用途 |
|------|------|---------|
| XS | 2px | 微調（Pill 垂直 padding） |
| SM | 4px | 圖示與文字間距 |
| MD | 8px | 行內元素間距 |
| LG | 16px | 卡片內區塊分隔 |
| XL | 24px | 卡片內 padding、卡片間距 |
| 2XL | 32px | 主要區塊分隔 |
| 3XL | 48px | 頁面區域留白 |
| 4XL | 64px | 全版分區（謹慎使用） |

**禁止：** 15px、18px、22px 等非 8 倍數間距。

#### 常用場景

| 場景 | 數值 |
|------|------|
| 卡片之間 | 24px |
| 卡片內 padding | 24px（標準）/ 20px（緊湊） |
| 卡片內區塊分隔 | 16px |
| 頁面左右邊距 | 24-32px |
| 側邊欄寬度 | 220-260px |
| 主內容最大寬度 | 1200px |
| 表格行高 | 48px |
| 表頭行高 | 40px |
| 按鈕高度 | 32 / 40 / 48px |

#### 陰影

| 等級 | 數值 | 用途 |
|------|------|------|
| xs | `0 1px 2px rgba(0,0,0,0.05)` | 微小提升 |
| sm | `0 1px 3px rgba(0,0,0,0.08)` | Card hover、Toggle |
| md | `0 4px 6px rgba(0,0,0,0.07)` | Dropdown |
| lg | `0 8px 24px rgba(0,0,0,0.1)` | Drawer |
| xl | `0 20px 60px rgba(0,0,0,0.15)` | Modal |
| focus | `0 0 0 3px rgba(10,43,65,0.08)` | 焦點指示器 |
| error | `0 0 0 3px rgba(245,34,45,0.08)` | 錯誤焦點 |

#### 動畫

| 時長 | 用途 |
|------|------|
| 150ms | 色彩變化（hover、focus） |
| 200ms | Switch、transform |
| 250ms | Drawer 滑入 |
| 400ms | Progress bar 填充 |
| 1s | Spinner 旋轉（連續） |

禁止裝飾性動畫。Easing 一律使用 `ease` 或 `ease-in-out`。

---

## 三、元件規範

> 以下 24 個元件按字母排序。所有色碼來自 Figma Design Tokens。

---

### 3-1 Avatar

| 屬性 | 數值 |
|------|------|
| 形狀 | 圓形 (50%) |
| 尺寸 | 24 / 32 / 40 / 48 / 64px |
| 縮寫字號 | 尺寸 × 0.38 |
| 縮寫字重 | Semibold 600 |
| 狀態燈比例 | 尺寸 × 0.28 |
| 堆疊重疊 | -10px |
| 狀態色 | Online `#52C41A` / Away `#FDB338` / Busy `#F5222D` / Offline `#BFBFBF` |

---

### 3-2 Badge / Pill

| 屬性 | Small | Medium | Large |
|------|-------|--------|-------|
| 字號 | 11px | 12px | 13px |
| Padding | 1px 6px | 2px 8px | 3px 10px |
| 字重 | Medium 500 | Medium 500 | Medium 500 |
| 圓角 (Badge) | 6px | 6px | 6px |
| 圓角 (Pill) | full | full | full |

7 種語意色：default, primary, info, success, warning, error, purple

Pill 僅用於資料型態標籤（整數、文字、布林、日期），普通狀態標籤使用 Badge。

---

### 3-3 Breadcrumbs

- 字號 14px，分隔符 "/" `#8C8C8C`
- Active（最後一層）：`#1F1F1F` / Medium 500
- 前面層級：`#8C8C8C` / Regular 400，hover → `#1F1F1F`

---

### 3-4 Button

| 屬性 | Small | Medium | Large |
|------|-------|--------|-------|
| 高度 | 32px | 40px | 48px |
| 字號 | 12px | 14px | 16px |
| Padding X | 12px | 20px | 24px |
| 圓角 | 4px | 8px | 8px |
| Icon 尺寸 | 16px | 16px | 20px |
| Gap | 4px | 4px | 8px |

5 種樣式：Primary, Secondary, Error, Ghost, Warning

形狀：標準、Icon-only (square / circle)、Rounded (行銷用)

| Variant | Default | Hover | Pressed | Disabled |
|---------|---------|-------|---------|----------|
| Primary | `#0A2B41` | `#2E4A5E` | `#061A28` | `#F0F0F0` |
| Secondary | `#FFFFFF` | `#FAFAFA` | `#F5F5F5` | `#F0F0F0` |
| Error | `#F5222D` | `#FF4D4F` | `#CF1322` | `#F0F0F0` |
| Ghost | transparent | `#FAFAFA` | `#F5F5F5` | — |
| Warning | `#FDB338` | `#FFC861` | `#D68C24` | `#F0F0F0` |

---

### 3-5 Card

- 圓角 12px，邊框 1px `#D9D9D9`
- Padding 24px（標準）/ 20px（緊湊）
- Header: 16px 24px + 底部分隔線
- Footer: 12px 24px + `#FAFAFA` 背景
- Hoverable: translateY(-2px) + shadow

---

### 3-6 Checkbox

- 尺寸 16×16px，圓角 4px
- 未選中 1.5px `#D9D9D9`，hover → `#0A2B41`
- 選中 `#0A2B41`，勾選 `#FFFFFF`
- Indeterminate：橫線圖標
- Label 間距 8px，字號 14px

---

### 3-7 Choicebox

- 圓角 10px，邊框 1.5px
- 未選中 `#D9D9D9`，選中 `#0A2B41` + 背景 `#F0F4F7`
- Padding 14px 16px
- 勾選圈 18px `#0A2B41`
- 支援單選 / 多選

---

### 3-8 Drawer

- 寬度 400px，最大 90vw
- Header/Body Padding 20px 24px
- 遮罩 `rgba(0,0,0,0.4)` + blur(2px)
- 動畫 0.25s ease，支援左右兩側

---

### 3-9 Feedback

- Emoji：24px，選中 2px `#0A2B41` + `#E7EAEC`
- Inline Yes/No：4px 12px padding，6px 圓角

---

### 3-10 Input

| 屬性 | Small | Medium | Large |
|------|-------|--------|-------|
| 高度 | 32px | 40px | 48px |
| 字號 | 13px | 14px | 16px |
| Padding X | 10px | 12px | 16px |
| 圓角 | 8px | 8px | 8px |

- Focus：`#0A2B41` + ring `rgba(10,43,65,0.08)`
- Error：`#F5222D` + ring `rgba(245,34,45,0.08)`
- Label 13px / Medium 500，間距 6px
- Prefix/Suffix `#8C8C8C`

---

### 3-11 Modal

| 尺寸 | 寬度 |
|------|------|
| Small | 360px |
| Medium | 480px |
| Large | 640px |

- 圓角 12px，標題 16px / Semibold 600
- Header/Body 20px 24px，Footer 16px 24px
- 遮罩 + blur，動畫 scale(0.96→1) 0.2s

---

### 3-12 Note / Alert

5 種語意：default, info, success, warning, error

- Padding 12px 16px，圓角 8px
- Title 14px / Semibold 600，Body 14px / Regular 400
- Icon 間距 10px

---

### 3-13 Progress

| 尺寸 | 高度 |
|------|------|
| Small | 4px |
| Medium | 8px |
| Large | 12px |

- Track `#F0F0F0`，圓角 full，動畫 0.4s ease
- 5 種色彩：primary, info, success, warning, error

---

### 3-14 Radio

- 尺寸 16px，圓形
- 未選中 1.5px `#D9D9D9`，hover → `#0A2B41`
- 選中 5px solid `#0A2B41`
- Label 間距 8px，選項間距 12px
- 支援垂直 / 水平排列

---

### 3-15 Search Input

- 搜尋圖標 16px，左 12px
- 清除按鈕 24×24px，右 8px
- ⌘K 提示：20px 高、4px 圓角
- Escape 清除內容

---

### 3-16 Select

- 與 Input 共用尺寸（32/40/48px）
- Chevron 16px，支援 Prefix、Label、Error

---

### 3-17 Spinner

- Circle：16/20/28/36px，stroke 3px，track 0.2 opacity
- Dots：4/6/8px，pulse 動畫 1.2s
- 旋轉 1s linear infinite

---

### 3-18 Switch

| 屬性 | Small | Medium |
|------|-------|--------|
| Track | 32×18px | 40×22px |
| Dot | 14px | 18px |

- Active `#0A2B41`，Inactive `#D9D9D9`
- Dot `#FFFFFF` + shadow，動畫 0.2s

---

### 3-19 Table

- 行高 48px，表頭 40px，容器圓角 12px
- Cell Padding 16px / 14px
- 表頭 13px Medium `#595959`，內容 14px Regular
- 僅水平線 `#F0F0F0`（表頭 `#D9D9D9`），Hover `#FAFAFA`

---

### 3-20 Tabs

**Primary：** 底線 2px `#0A2B41`，40px 高，padding 10px 16px

**Secondary：** Pill 風格，`#FAFAFA` 容器 8px，active `#FFFFFF` + shadow

Active `#1F1F1F` / 500，Inactive `#8C8C8C` / 400

---

### 3-21 Textarea

- Padding 12px，圓角 8px，字號 14px，行高 1.6
- 最小 3 行，垂直 resize
- 字數計數器：12px mono，右下角

---

### 3-22 Toast

- 背景 `#1F1F1F`，文字 `#FFFFFF`
- Padding 10px 16px，圓角 8px，最小寬度 200px
- 語意圖標：✓ `#52C41A` / ✕ `#F5222D` / ⚠ `#FDB338`
- 2.5s 自動消失 + fade out，bottom center，可堆疊

---

### 3-23 Toggle Group

- 容器 `#FAFAFA` + 1px `#D9D9D9`，8px 圓角，3px padding
- 按鈕 6px 16px，6px 圓角
- Active `#FFFFFF` + shadow，字號 13px

---

### 3-24 Tooltip

- 背景 `#1F1F1F`，文字 `#FFFFFF`
- Padding 5px 10px，圓角 6px
- 4 方向，偏移 8px，fadeIn 0.15s
