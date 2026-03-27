document.addEventListener("DOMContentLoaded", () => {
  const chatWindow = document.getElementById("chat-window");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");

  const TIMEOUT_MS = 120000; // 120 seconds timeout (extended for AlphaMemo scraping)

  // Enhanced addMessage to support Carousel
  function addMessage(content, sender) {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add(
      "message",
      sender === "user" ? "user-message" : "bot-message",
    );

    const contentDiv = document.createElement("div");
    contentDiv.classList.add("message-content");

    if (content && typeof content === "object" && content.type === "carousel") {
      // Render Carousel
      renderCarousel(contentDiv, content.cards);
    } else {
      // Standard Text
      let text = "";
      if (content === null || content === undefined) {
        text = "（無內容）";
      } else {
        text = typeof content === "string" ? content : JSON.stringify(content);
      }

      // Parse basic markdown-like bold syntax (**text**) to HTML <b>text</b>
      let formattedText = text.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
      formattedText = formattedText.replace(/\n/g, "<br>");
      contentDiv.innerHTML = formattedText;
    }

    msgDiv.appendChild(contentDiv);
    chatWindow.appendChild(msgDiv);

    // Scroll to bottom
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return msgDiv;
  }

  function renderCarousel(container, cards) {
    container.style.background = "transparent";
    container.style.padding = "0";
    container.style.boxShadow = "none";

    const wrapper = document.createElement("div");
    wrapper.className = "carousel-wrapper";

    const carousel = document.createElement("div");
    carousel.className = "carousel-container";

    // Arrows
    const prevBtn = document.createElement("button");
    prevBtn.className = "nav-btn prev";
    prevBtn.innerHTML = "←";
    const nextBtn = document.createElement("button");
    nextBtn.className = "nav-btn next";
    nextBtn.innerHTML = "→";

    const dotsContainer = document.createElement("div");
    dotsContainer.className = "carousel-dots";

    cards.forEach((card, index) => {
      const cardDiv = document.createElement("div");
      cardDiv.className = "carousel-card";

      // Header
      const header = document.createElement("div");
      header.className = "card-header";
      const icons = ["📰", "📊", "💰"];
      const icon = icons[index] || "📄";
      header.innerHTML = `<span style="font-size:1.5rem">${icon}</span> <span class="card-title">${card.title}</span>`;
      cardDiv.appendChild(header);

      // Body
      const body = document.createElement("div");
      body.className = "card-content";
      const bodyId = "card-body-" + Date.now() + "-" + index;
      body.id = bodyId;
      cardDiv.appendChild(body);

      carousel.appendChild(cardDiv);

      // Create Dot
      const dot = document.createElement("div");
      dot.className = "dot" + (index === 0 ? " active" : "");
      dotsContainer.appendChild(dot);

      // Deferred Render
      setTimeout(() => {
        const bodyEl = document.getElementById(bodyId);
        if (!bodyEl) return;

        if (card.type === "markdown") {
          bodyEl.classList.add("text-content");
          let text = card.content
            .replace(/\*\*(.*?)\*\*/g, "<b>$1</b>")
            .replace(/\n/g, "<br>");
          bodyEl.innerHTML = text;
        } else if (card.type === "chart_chips") {
          renderChipsChart(bodyId, card.data);
        } else if (card.type === "grid_fundamentals") {
          renderFundamentalsGrid(bodyEl, card.data);
        }
      }, 100);
    });

    // Scroll Events for Dots
    carousel.addEventListener("scroll", () => {
      const index = Math.round(carousel.scrollLeft / carousel.offsetWidth);
      const dots = dotsContainer.querySelectorAll(".dot");
      dots.forEach((d, i) => d.classList.toggle("active", i === index));
    });

    // Arrow Clicks
    prevBtn.onclick = () =>
      carousel.scrollBy({ left: -250, behavior: "smooth" });
    nextBtn.onclick = () =>
      carousel.scrollBy({ left: 250, behavior: "smooth" });

    wrapper.appendChild(prevBtn);
    wrapper.appendChild(carousel);
    wrapper.appendChild(nextBtn);

    container.appendChild(wrapper);
    container.appendChild(dotsContainer);
  }

  function renderFundamentalsGrid(container, data) {
    if (!data || Object.keys(data).length === 0) {
      container.innerHTML =
        "<div style='text-align:center;color:#888'>暫無數據</div>";
      return;
    }

    container.className = "fund-grid";
    const fields = [
      { key: "eps", label: "EPS (元)" },
      { key: "revenue_yoy", label: "營收 YoY" },
      { key: "target_price", label: "法人目標價" },
      { key: "roe", label: "ROE" },
    ];

    fields.forEach((f) => {
      const item = document.createElement("div");
      item.className = "fund-item";
      item.innerHTML = `
            <div class="fund-label">${f.label}</div>
            <div class="fund-value">${data[f.key] || "N/A"}</div>
          `;
      container.appendChild(item);
    });
  }

  async function renderChipsChart(containerId, data) {
    const chartRoot = document.getElementById(containerId);
    if (!chartRoot) return;

    try {
      if (!data || data.length === 0) {
        chartRoot.innerHTML =
          "<div style='text-align:center;color:#888'>暫無籌碼數據</div>";
        return;
      }

      // Use ComposedChart for Bars + Lines
      const {
        ComposedChart,
        Bar,
        Line,
        XAxis,
        YAxis,
        CartesianGrid,
        Tooltip,
        Legend,
        ResponsiveContainer,
      } = Recharts;

      chartRoot.style.height = "250px";
      chartRoot.style.width = "100%";

      const ChartComponent = React.createElement(
        ResponsiveContainer,
        { width: "100%", height: "100%" },
        React.createElement(
          ComposedChart,
          { data: data, margin: { top: 5, right: 5, left: -20, bottom: 5 } },
          React.createElement(CartesianGrid, {
            strokeDasharray: "3 3",
            stroke: "rgba(255,255,255,0.1)",
          }),
          React.createElement(XAxis, {
            dataKey: "date",
            stroke: "#888",
            tick: { fontSize: 10 },
          }),
          React.createElement(YAxis, {
            yAxisId: "left",
            stroke: "#888",
            tick: { fontSize: 10 },
          }),
          React.createElement(YAxis, {
            yAxisId: "right",
            orientation: "right",
            stroke: "#82ca9d",
            tick: { fontSize: 10 },
          }),
          React.createElement(Tooltip, {
            contentStyle: {
              backgroundColor: "#1a1a1a",
              borderColor: "#333",
              color: "#fff",
              fontSize: "12px",
            },
            itemStyle: { color: "#fff" },
          }),
          React.createElement(Legend, { wrapperStyle: { fontSize: "10px" } }),

          // Bars for Daily Volume
          React.createElement(Bar, {
            yAxisId: "left",
            dataKey: "foreign",
            name: "外資(張)",
            fill: "#ff9f1c",
            barSize: 10,
          }),
          React.createElement(Bar, {
            yAxisId: "left",
            dataKey: "trust",
            name: "投信(張)",
            fill: "#2ec4b6",
            barSize: 10,
          }),

          // Lines for Cumulative
          React.createElement(Line, {
            yAxisId: "right",
            type: "monotone",
            dataKey: "cum_foreign",
            name: "外資累積",
            stroke: "#ffd60a",
            strokeWidth: 2,
            dot: false,
          }),
          React.createElement(Line, {
            yAxisId: "right",
            type: "monotone",
            dataKey: "cum_trust",
            name: "投信累積",
            stroke: "#32d74b",
            strokeWidth: 2,
            dot: false,
          }),
        ),
      );

      if (ReactDOM.createRoot) {
        if (!chartRoot._reactRoot) {
          chartRoot._reactRoot = ReactDOM.createRoot(chartRoot);
        }
        chartRoot._reactRoot.render(ChartComponent);
      } else {
        ReactDOM.render(ChartComponent, chartRoot);
      }
    } catch (e) {
      console.error("Chips Chart Error:", e);
      chartRoot.innerHTML = `<div style='color:red;font-size:12px'>圖表錯誤</div>`;
    }
  }

  function addLoadingIndicator() {
    const msgDiv = document.createElement("div");
    msgDiv.classList.add("message", "bot-message", "loading-msg");

    const contentDiv = document.createElement("div");
    contentDiv.classList.add("message-content");
    contentDiv.innerHTML = `
      <div class="reasoning-chain" id="reasoning-text">Sophia 正在接收指令...</div>
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    `;

    msgDiv.appendChild(contentDiv);
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;

    // Start status cycling
    const statuses = [
      "Sophia 正在調度 Arthur 挖掘數據...",
      "Arthur 正在計算法人級量化指標...",
      "Oscar 正在執行二次數據核驗...",
      "Sophia 正在建構多維度戰情室...",
    ];
    let i = 0;
    const interval = setInterval(() => {
      const el = document.getElementById("reasoning-text");
      if (el && i < statuses.length) {
        el.textContent = statuses[i++];
      } else {
        clearInterval(interval);
      }
    }, 1500);

    return { msgDiv, interval };
  }

  function addRetryButton(errorMsg, originalMessage) {
    const retryBtn = document.createElement("button");
    retryBtn.textContent = "🔄 重試";
    retryBtn.className = "retry-btn";
    retryBtn.onclick = () => {
      errorMsg.remove();
      userInput.value = originalMessage;
      sendMessage();
    };
    errorMsg.querySelector(".message-content").appendChild(retryBtn);
  }

  async function fetchWithTimeout(url, options, timeout = TIMEOUT_MS) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === "AbortError") {
        throw new Error("TIMEOUT");
      }
      throw error;
    }
  }

  async function renderTrendChart(containerId, data) {
    const chartRoot = document.getElementById(containerId);
    if (!chartRoot) return;

    try {
      // 1. Library Check
      if (
        typeof Recharts === "undefined" ||
        typeof React === "undefined" ||
        typeof ReactDOM === "undefined"
      ) {
        throw new Error("Visualization libraries (React/Recharts) missing.");
      }

      const {
        LineChart,
        Line,
        XAxis,
        YAxis,
        Tooltip,
        ResponsiveContainer,
        CartesianGrid,
        ReferenceArea,
      } = Recharts;

      // 2. Data Check
      if (!data || data.length === 0) {
        chartRoot.innerHTML =
          '<div style="color:rgba(255,255,255,0.4); font-size:12px; padding:10px; text-align:center;">ℹ️ 暫無趨勢數據</div>';
        return;
      }

      // 3. Ensure Container Height
      chartRoot.style.height = "250px";
      chartRoot.style.width = "100%";
      chartRoot.innerHTML = ""; // Clear loading message

      // 4. Transform Data (Ensure numbers)
      const chartData = data.map((d) => ({
        date: d.date,
        score: parseFloat(d.score),
        index: d.index ? parseFloat(d.index) : null,
      }));

      // 5. Render Chart
      const ChartComponent = React.createElement(
        ResponsiveContainer,
        { width: "100%", height: "100%" },
        React.createElement(
          LineChart,
          {
            data: chartData,
            margin: { top: 10, right: 10, left: -20, bottom: 0 },
          },
          // SVG Definitions for Gradients
          React.createElement(
            "defs",
            {},
            React.createElement(
              "linearGradient",
              { id: "strengthGradient", x1: "0", y1: "0", x2: "0", y2: "1" },
              React.createElement("stop", {
                offset: "0%",
                stopColor: "#ff4d4d",
                stopOpacity: 1,
              }),
              React.createElement("stop", {
                offset: "50%",
                stopColor: "#e6e600",
                stopOpacity: 1,
              }),
              React.createElement("stop", {
                offset: "100%",
                stopColor: "#00c853",
                stopOpacity: 1,
              }),
            ),
          ),

          // Background Zones
          React.createElement(ReferenceArea, {
            y1: 7,
            y2: 10,
            fill: "rgba(255, 68, 68, 0.08)",
            strokeOpacity: 0,
          }),
          React.createElement(ReferenceArea, {
            y1: 4,
            y2: 7,
            fill: "rgba(150, 150, 150, 0.05)",
            strokeOpacity: 0,
          }),
          React.createElement(ReferenceArea, {
            y1: 0,
            y2: 4,
            fill: "rgba(52, 211, 153, 0.08)",
            strokeOpacity: 0,
          }),

          React.createElement(CartesianGrid, {
            strokeDasharray: "3 3",
            stroke: "rgba(255,255,255,0.1)",
          }),
          React.createElement(XAxis, {
            dataKey: "date",
            stroke: "#888",
            tick: { fontSize: 10 },
          }),
          React.createElement(YAxis, {
            yAxisId: "left",
            domain: [0, 10],
            stroke: "#888",
            tick: { fontSize: 10 },
          }),
          React.createElement(YAxis, {
            yAxisId: "right",
            orientation: "right",
            domain: ["auto", "auto"],
            hide: true,
          }),

          React.createElement(Tooltip, {
            contentStyle: {
              backgroundColor: "#1a1a1a",
              borderColor: "#333",
              color: "#fff",
              fontSize: "12px",
            },
            itemStyle: { color: "#fff" },
          }),

          // Strength Line
          React.createElement(Line, {
            yAxisId: "left",
            type: "monotone",
            dataKey: "score",
            name: "市場強度",
            stroke: "url(#strengthGradient)",
            strokeWidth: 3,
            dot: { r: 3, fill: "#ff4d4d" },
            activeDot: { r: 5 },
          }),

          // Index Line (Background Context)
          React.createElement(Line, {
            yAxisId: "right",
            type: "monotone",
            dataKey: "index",
            name: "加權指數",
            stroke: "rgba(255,255,255,0.3)",
            strokeWidth: 1.5,
            dot: false,
          }),
        ),
      );

      if (ReactDOM.createRoot) {
        if (!chartRoot._reactRoot) {
          chartRoot._reactRoot = ReactDOM.createRoot(chartRoot);
        }
        chartRoot._reactRoot.render(ChartComponent);
      } else {
        ReactDOM.render(ChartComponent, chartRoot);
      }
    } catch (e) {
      console.error("Chart Rendering Error:", e);
      chartRoot.innerHTML = `<div style='color:#ff4444; font-size:12px; padding:10px; border:1px solid #500; background:#300; border-radius:4px;'>❌ 圖表錯誤: ${e.message}</div>`;
    }
  }

  async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message
    addMessage(text, "user");
    const originalMessage = text;
    userInput.value = "";

    // Add loading state
    const { msgDiv: loadingMsg, interval } = addLoadingIndicator();

    try {
      const response = await fetchWithTimeout("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: text }),
      });

      // Remove loading and stop interval
      loadingMsg.remove();
      clearInterval(interval);

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ response: "伺服器錯誤" }));
        const errorMsg = addMessage(
          `❌ ${errorData.response || "伺服器發生錯誤，請稍後再試"}`,
          "bot",
        );
        addRetryButton(errorMsg, originalMessage);
        return;
      }

      const data = await response.json();

      // Add bot response
      const botMsgDiv = addMessage(data.response, "bot");

      // Apply background class if present (Market Strength Enhancement)
      if (data.bg_class) {
        const contentEl = botMsgDiv.querySelector(".message-content");
        contentEl.classList.add(data.bg_class);
        contentEl.style.animation = "pulse-gold 2s infinite";
      }

      // If we have chart data, render it!
      if (data.chart_type === "line" && data.chart_data) {
        const contentEl = botMsgDiv.querySelector(".message-content");
        renderTrendChart(contentEl, data.chart_data);
      }
    } catch (error) {
      loadingMsg.remove();
      clearInterval(interval);

      let errorMessage = "發生錯誤，請稍後再試。";
      if (error.message === "TIMEOUT") {
        errorMessage =
          "⏱️ 請求逾時，系統可能正在處理大量資料。請稍後再試或簡化查詢。";
      } else if (
        error.message.includes("NetworkError") ||
        error.message.includes("Failed to fetch")
      ) {
        errorMessage = "🌐 網路連線問題，請檢查您的網路連線。";
      }

      const errorMsg = addMessage(errorMessage, "bot");
      addRetryButton(errorMsg, originalMessage);
      console.error("Error:", error);
    }
  }

  sendBtn.addEventListener("click", sendMessage);

  userInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  });

  // Focus input on load
  userInput.focus();

  // Assign to window for global access
  window.sendMessage = sendMessage;
  window.sendQuickMessage = function (msg) {
    const userInput = document.getElementById("user-input");
    if (userInput) {
      userInput.value = msg;
      sendMessage();
    }
  };
});
