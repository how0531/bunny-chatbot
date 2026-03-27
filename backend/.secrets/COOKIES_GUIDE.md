# 手動匯出 AlphaMemo Cookies 教學

## 方法 1：使用 Cookie-Editor 擴充套件（推薦）

### 步驟 1：安裝擴充套件

1. 打開 Chrome
2. 前往：https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
3. 點擊「加到 Chrome」安裝

### 步驟 2：登入 AlphaMemo

1. 前往 https://www.alphamemo.ai/sign-in
2. 用 Google 帳號登入
3. 確認登入成功（看到首頁）

### 步驟 3：匯出 Cookies

1. 點擊瀏覽器右上角的 **Cookie-Editor** 圖示
2. 點擊右上角的 **「Export」** 按鈕
3. 選擇 **「Export as JSON」**
4. 複製所有 JSON 內容

### 步驟 4：保存到檔案

1. 在專案資料夾創建：`backend/.secrets/alphamemo_cookies.json`
2. 貼上剛才複製的 JSON
3. 保存檔案

---

## 方法 2：手動從 DevTools 複製

### 步驟 1：打開 DevTools

1. 在 AlphaMemo 頁面按 F12
2. 切換到「Application」分頁
3. 左側選單：Storage → Cookies → https://www.alphamemo.ai

### 步驟 2：複製重要的 Cookies

從您的截圖，需要這些 cookies：

- `sb-sp-auth-token-1`
- `CloudFront-Key-Pair-Id`
- `CloudFront-Policy`
- `CloudFront-Signature`

### 步驟 3：建立 JSON 檔案

在 `backend/.secrets/alphamemo_cookies.json` 貼上：

```json
[
  {
    "name": "sb-sp-auth-token-1",
    "value": "從 DevTools 複製這裡的值",
    "domain": ".alphamemo.ai",
    "path": "/",
    "expires": -1,
    "secure": true,
    "httpOnly": false,
    "sameSite": "Lax"
  },
  {
    "name": "CloudFront-Key-Pair-Id",
    "value": "從 DevTools 複製",
    "domain": "www.alphamemo.ai",
    "path": "/",
    "expires": -1,
    "secure": false,
    "httpOnly": false,
    "sameSite": "None"
  }
  // ... 其他 cookies
]
```

---

## 完成後

建立好 `backend/.secrets/alphamemo_cookies.json` 後，告訴我「完成」，我會繼續更新爬蟲代碼！
