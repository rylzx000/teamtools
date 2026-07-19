(function () {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function toast(message) {
    const old = $(".toast");
    if (old) old.remove();
    const node = document.createElement("div");
    node.className = "toast";
    node.setAttribute("role", "status");
    node.textContent = message;
    document.body.appendChild(node);
    window.setTimeout(() => node.remove(), 2200);
  }

  const mockFpaFormConfig = {
    systems: [
      { value: "claimcar", label: "车险理赔核心系统" },
      { value: "claimoth", label: "非车险理赔核心系统" },
      { value: "onlineclaim", label: "在线理赔服务平台" },
      { value: "clqp", label: "零配件报价系统" }
    ],
    countTimings: [
      { value: "估算早期", label: "1.39 估算早期", default: true },
      { value: "估算中期", label: "1.21 估算中期" },
      { value: "估算晚期", label: "1.10 估算晚期" }
    ],
    completenessLevels: [
      { value: "A/B_SPECIAL", label: "1.10 A/B 级且采取特殊设计", default: true },
      { value: "UNSPECIFIED_OR_CD", label: "1.00 无明确级别或 C/D" },
      { value: "A_FULL_LIFECYCLE", label: "1.30 A 级且全生命周期措施" }
    ]
  };

  function hydrateConfigSelects(form) {
    $$("[data-config-select]", form).forEach((select) => {
      const options = mockFpaFormConfig[select.dataset.configSelect] || [];
      if (!options.length) return;
      const placeholder = select.querySelector("option[value='']");
      select.replaceChildren();
      if (placeholder) select.appendChild(placeholder);
      options.forEach((item) => {
        const option = new Option(item.label, item.value);
        option.selected = Boolean(item.default);
        select.appendChild(option);
      });
    });
  }

  function initTasks() {
    const rows = $$("tbody tr[data-status]");
    const count = $("[data-visible-count]");
    const refreshTime = $("[data-refresh-time]");
    const filters = $$("[data-status-filter]");

    function paint(status) {
      let visible = 0;
      rows.forEach((row) => {
        const match = status === "all" || row.dataset.status === status;
        row.hidden = !match;
        if (match) visible += 1;
      });
      if (count) count.textContent = String(visible);
    }

    filters.forEach((button) => {
      button.addEventListener("click", () => {
        filters.forEach((item) => item.classList.toggle("active", item === button));
        paint(button.dataset.statusFilter || "all");
      });
    });
    paint("all");

    const refresh = $("[data-refresh]");
    if (refresh) {
      refresh.addEventListener("click", () => {
        if (refreshTime) {
          refreshTime.textContent = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
        }
        toast("任务列表已刷新");
      });
    }

    const adminToggle = $("[data-admin-toggle]");
    if (adminToggle) {
      adminToggle.addEventListener("change", () => {
        document.body.classList.toggle("show-admin", adminToggle.checked);
      });
    }
  }

  function initSubmit() {
    const form = $("[data-submit-form]");
    if (!form) return;
    const textarea = $("textarea[name='markdown']", form);
    const charCount = $("[data-char-count]", form);
    const fileInput = $("input[name='mdFile']", form);
    const fileNote = $("[data-file-note]", form);
    const dropzone = $("[data-upload-dropzone]", form);
    const alert = $("[data-form-alert]", form);
    const apiKeyInput = $("[data-api-key]", form);
    const rememberKey = $("[data-remember-key]", form);
    let selectedFile = null;
    const savedKey = localStorage.getItem("teamtools:fpa:deepseek-key") || "";
    hydrateConfigSelects(form);

    if (apiKeyInput && savedKey) {
      apiKeyInput.value = savedKey;
      if (rememberKey) rememberKey.checked = true;
    }

    function setAlert(type, message) {
      if (!alert) return;
      alert.hidden = false;
      alert.className = "form-alert " + (type === "error" ? "is-error" : "is-success");
      alert.textContent = message;
    }

    if (textarea && charCount) {
      textarea.addEventListener("input", () => {
        charCount.textContent = String(textarea.value.length);
      });
    }

    function updateFileNote(file) {
      if (!fileNote) return;
      if (!file) {
        fileNote.textContent = "文件不超过 256KB；可与粘贴内容同时提交。";
        if (dropzone) dropzone.classList.remove("is-selected");
        selectedFile = null;
        return;
      }
      selectedFile = file;
      fileNote.textContent = `${file.name} · ${(file.size / 1024).toFixed(1)}KB`;
      if (dropzone) dropzone.classList.add("is-selected");
    }

    if (fileInput) {
      fileInput.addEventListener("change", () => {
        const file = fileInput.files && fileInput.files[0];
        updateFileNote(file);
      });
    }

    if (dropzone && fileInput) {
      ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
          event.preventDefault();
          dropzone.classList.add("is-dragging");
        });
      });
      ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
          event.preventDefault();
          dropzone.classList.remove("is-dragging");
        });
      });
      dropzone.addEventListener("drop", (event) => {
        const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
        if (!file) return;
        if (typeof DataTransfer !== "undefined") {
          const transfer = new DataTransfer();
          transfer.items.add(file);
          fileInput.files = transfer.files;
        }
        updateFileNote(file);
      });
    }

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const data = new FormData(form);
      const markdown = String(data.get("markdown") || "").trim();
      const file = selectedFile || (fileInput && fileInput.files ? fileInput.files[0] : null);
      const target = String(data.get("targetDays") || "").trim();
      const system = String(data.get("system") || "").trim();
      const apiKey = String(data.get("apiKey") || "").trim();

      if (!system) {
        setAlert("error", "请先选择系统。");
        return;
      }
      if (!markdown && !file) {
        setAlert("error", "请粘贴 Markdown 内容，或上传一个 .md 文件。");
        return;
      }
      if (file && file.size > 256 * 1024) {
        setAlert("error", "上传文件超过 256KB，请压缩内容后再提交。");
        return;
      }
      if (target && !/^\d+(\.\d)?$/.test(target)) {
        setAlert("error", "目标人天最多保留 1 位小数。");
        return;
      }
      if (apiKey) {
        sessionStorage.setItem("teamtools:fpa:deepseek-session-key", "1");
      } else {
        sessionStorage.removeItem("teamtools:fpa:deepseek-session-key");
      }
      sessionStorage.setItem("teamtools:fpa:auto-call", "1");

      if (apiKey && rememberKey && rememberKey.checked) {
        localStorage.setItem("teamtools:fpa:deepseek-key", apiKey);
      } else if (rememberKey && !rememberKey.checked) {
        localStorage.removeItem("teamtools:fpa:deepseek-key");
      }
      setAlert("success", "任务已创建，AI 请求包已生成，即将进入任务详情页。");
      window.setTimeout(() => {
        window.location.href = "fpa-detail.html?task=latest";
      }, 650);
    });
  }

  function initDetail() {
    const copyTask = $("[data-copy-task]");
    const taskId = $("[data-task-id]");
    if (copyTask && taskId) {
      copyTask.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(taskId.textContent || "");
          toast("任务 ID 已复制");
        } catch (_) {
          toast("当前浏览器不允许复制，请手动选中任务 ID");
        }
      });
    }

    const aiState = $("[data-ai-call-state]");
    const aiNote = $("[data-ai-call-note]");
    const aiTitle = $("[data-ai-call-title]");
    const hasLocalKey = Boolean(
      localStorage.getItem("teamtools:fpa:deepseek-key") ||
      sessionStorage.getItem("teamtools:fpa:deepseek-session-key")
    );
    const shouldAutoCall = sessionStorage.getItem("teamtools:fpa:auto-call") === "1";

    if (shouldAutoCall) {
      sessionStorage.removeItem("teamtools:fpa:auto-call");
      if (hasLocalKey) {
        if (aiState) aiState.textContent = "调用中";
        if (aiTitle) aiTitle.textContent = "调用中";
        if (aiNote) aiNote.textContent = "已检测到本机 API Key，正在自动模拟浏览器端 DeepSeek 调用；不会向后端上传 API Key。";
        toast("已进入详情页，自动发起模型调用");
      } else if (aiNote) {
        if (aiTitle) aiTitle.textContent = "等待配置 API Key";
        aiNote.textContent = "任务已创建，等待配置 API Key 后调用模型。";
      }
    }

    $$("[data-ai-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.aiAction;
        if (action === "call" || action === "recall") {
          if (aiState) aiState.textContent = "调用中";
          if (aiTitle) aiTitle.textContent = "调用中";
          if (aiNote) aiNote.textContent = "正在模拟浏览器端 DeepSeek 调用；不会向后端上传 API Key。";
          toast(action === "recall" ? "已重新发起模型调用" : "已发起模型调用");
          return;
        }
        if (action === "return") {
          if (aiState) aiState.textContent = "已回传";
          if (aiTitle) aiTitle.textContent = "已回传，等待校验";
          if (aiNote) aiNote.textContent = "已回传，等待后端校验。";
          toast("AI 结果已回传，等待后端校验");
        }
      });
    });
  }

  initTasks();
  initSubmit();
  initDetail();
})();
