(function () {
  "use strict";

  // ==========================================================
  // CONFIG
  // ==========================================================
  const API = {
    ask: "/ask",
    documents: "/api/documents",
    upload: "/api/documents/upload",
    conversations: "/api/conversations",
  };

  const SUGGESTIONS = [
    { icon: "📎", text: "Upload a research PDF and ask me anything about it" },
    { icon: "🧬", text: "What are the key findings about frailty indices?" },
    { icon: "💊", text: "What does the research say about spinal anaesthesia?" },
    { icon: "🔬", text: "Summarize the main research topics available" },
  ];

  // ==========================================================
  // STATE
  // ==========================================================
  let activeConversationId = null;
  let conversations = [];
  let documents = [];
  let isLoading = false;

  // ==========================================================
  // DOM
  // ==========================================================
  const chatArea = document.getElementById("chat-area");
  const chatMessages = document.getElementById("chat-messages");
  const welcomeScreen = document.getElementById("welcome-screen");
  const questionInput = document.getElementById("question-input");
  const sendBtn = document.getElementById("send-btn");
  const newChatBtn = document.getElementById("new-chat-btn");
  const conversationList = document.getElementById("conversation-list");
  const documentList = document.getElementById("document-list");
  const docCardsBar = document.getElementById("doc-cards-bar");
  const docCardsContainer = document.getElementById("doc-cards-container");
  const sidebar = document.getElementById("sidebar");
  const sidebarOverlay = document.getElementById("sidebar-overlay");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebarFileInput = document.getElementById("sidebar-file-input");
  const attachFileInput = document.getElementById("attach-file-input");
  const uploadModal = document.getElementById("upload-modal");
  const uploadModalFilename = document.getElementById("upload-modal-filename");
  const uploadModalStatus = document.getElementById("upload-modal-status");

  // ==========================================================
  // INIT
  // ==========================================================
  async function init() {
    bindEvents();
    autoResizeInput();
    await Promise.all([loadConversations(), loadDocuments()]);
    renderWelcome();
  }

  function bindEvents() {
    sendBtn.addEventListener("click", handleSend);
    questionInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    });
    questionInput.addEventListener("input", autoResizeInput);
    questionInput.addEventListener("input", updateSendBtn);
    newChatBtn.addEventListener("click", startNewChat);
    if (sidebarToggle) sidebarToggle.addEventListener("click", toggleSidebar);
    if (sidebarOverlay) sidebarOverlay.addEventListener("click", closeSidebar);
    sidebarFileInput.addEventListener("change", handleFileSelect);
    attachFileInput.addEventListener("change", handleFileSelect);
  }

  function autoResizeInput() {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 150) + "px";
  }

  function updateSendBtn() {
    sendBtn.disabled = !questionInput.value.trim() || isLoading;
  }

  // ==========================================================
  // SEND QUESTION
  // ==========================================================
  async function handleSend() {
    var question = questionInput.value.trim();
    if (!question || isLoading) return;

    // Create conversation if needed
    if (!activeConversationId) {
      await createNewConversation(question.substring(0, 60));
    }

    hideWelcome();
    renderUserMessage({ content: question, created_at: new Date().toISOString() });
    questionInput.value = "";
    autoResizeInput();
    updateSendBtn();

    setLoading(true);
    var thinkingEl = renderThinking();
    scrollToBottom();

    try {
      var resp = await fetch(API.ask, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question, conversation_id: activeConversationId }),
      });
      if (!resp.ok) throw new Error("Server error: " + resp.status);

      var data = await resp.json();
      removeEl(thinkingEl);

      if (data.error) {
        renderErrorMessage({ content: data.error, created_at: new Date().toISOString() }, question);
      } else {
        renderAIMessage({
          content: data.answer || "No answer generated.",
          sources: data.sources || [],
          created_at: new Date().toISOString(),
        });
      }
    } catch (err) {
      removeEl(thinkingEl);
      renderErrorMessage({
        content: "Unable to reach MediResearch AI. Please check the server.",
        created_at: new Date().toISOString(),
      }, question);
    } finally {
      setLoading(false);
      scrollToBottom();
      await loadConversations(); // refresh sidebar
    }
  }

  function setLoading(v) {
    isLoading = v;
    sendBtn.disabled = v;
    var icon = sendBtn.querySelector(".send-icon");
    var spin = sendBtn.querySelector(".spinner");
    if (icon && spin) { icon.style.display = v ? "none" : "block"; spin.style.display = v ? "block" : "none"; }
  }

  // ==========================================================
  // FILE UPLOAD
  // ==========================================================
  async function handleFileSelect(e) {
    var files = e.target.files;
    if (!files || files.length === 0) return;

    for (var i = 0; i < files.length; i++) {
      await uploadFile(files[i]);
    }

    e.target.value = "";
  }

  async function uploadFile(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Only PDF files are accepted.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      alert("File too large. Maximum 50 MB.");
      return;
    }

    // Ensure conversation exists
    if (!activeConversationId) {
      await createNewConversation("Research: " + file.name);
      hideWelcome();
    }

    showUploadModal(file.name);

    var formData = new FormData();
    formData.append("file", file);
    formData.append("conversation_id", activeConversationId);

    try {
      updateUploadStatus("Processing PDF...");
      var resp = await fetch(API.upload, { method: "POST", body: formData });
      if (!resp.ok) throw new Error("Upload failed: " + resp.status);

      var data = await resp.json();

      if (data.error) {
        updateUploadStatus("Error: " + data.error);
        await delay(2000);
      } else if (data.duplicate) {
        updateUploadStatus("Already uploaded ✓");
        await delay(1200);
      } else {
        updateUploadStatus("Ready ✓");
        await delay(1000);
      }
    } catch (err) {
      updateUploadStatus("Upload failed");
      await delay(2000);
    }

    hideUploadModal();
    await Promise.all([loadDocuments(), loadConversationDocs()]);
  }

  function showUploadModal(filename) {
    uploadModalFilename.textContent = filename;
    uploadModalStatus.textContent = "Uploading...";
    uploadModal.classList.remove("hidden");
  }

  function updateUploadStatus(status) {
    uploadModalStatus.textContent = status;
  }

  function hideUploadModal() {
    uploadModal.classList.add("hidden");
  }

  // ==========================================================
  // CONVERSATIONS — API
  // ==========================================================
  async function loadConversations() {
    try {
      var resp = await fetch(API.conversations);
      var data = await resp.json();
      conversations = data.conversations || [];
      renderConversationList();
    } catch (e) { console.warn("Failed to load conversations", e); }
  }

  async function createNewConversation(title) {
    try {
      var resp = await fetch(API.conversations, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title || "New Chat" }),
      });
      var data = await resp.json();
      activeConversationId = data.conversation.id;
      await loadConversations();
    } catch (e) { console.error("Failed to create conversation", e); }
  }

  async function switchConversation(id) {
    activeConversationId = id;
    renderConversationList();

    try {
      var resp = await fetch(API.conversations + "/" + id);
      var data = await resp.json();
      var conv = data.conversation;

      if (!conv) { renderWelcome(); return; }

      if (conv.messages && conv.messages.length > 0) {
        hideWelcome();
        chatMessages.innerHTML = "";
        conv.messages.forEach(function (msg) {
          if (msg.role === "user") renderUserMessage(msg);
          else if (msg.role === "ai") renderAIMessage(msg);
          else if (msg.role === "error") renderErrorMessage(msg, null);
        });
        scrollToBottom();
      } else {
        chatMessages.innerHTML = "";
        renderWelcome();
      }

      // Show document cards
      if (conv.documents && conv.documents.length > 0) {
        renderDocCards(conv.documents);
      } else {
        hideDocCards();
      }
    } catch (e) { console.error("Failed to load conversation", e); }

    closeSidebar();
  }

  async function deleteConversation(id, ev) {
    ev.stopPropagation();
    try {
      await fetch(API.conversations + "/" + id, { method: "DELETE" });
      if (activeConversationId === id) {
        activeConversationId = null;
        chatMessages.innerHTML = "";
        hideDocCards();
        renderWelcome();
      }
      await loadConversations();
    } catch (e) { console.error("Failed to delete conversation", e); }
  }

  function startNewChat() {
    activeConversationId = null;
    chatMessages.innerHTML = "";
    hideDocCards();
    renderWelcome();
    renderConversationList();
    questionInput.value = "";
    autoResizeInput();
    updateSendBtn();
    questionInput.focus();
    closeSidebar();
  }

  async function loadConversationDocs() {
    if (!activeConversationId) return;
    try {
      var resp = await fetch(API.conversations + "/" + activeConversationId);
      var data = await resp.json();
      if (data.conversation && data.conversation.documents) {
        renderDocCards(data.conversation.documents);
      }
    } catch (e) { /* ignore */ }
  }

  // ==========================================================
  // DOCUMENTS — API
  // ==========================================================
  async function loadDocuments() {
    try {
      var resp = await fetch(API.documents);
      var data = await resp.json();
      documents = data.documents || [];
      renderDocumentList();
    } catch (e) { console.warn("Failed to load documents", e); }
  }

  async function deleteDocument(id, ev) {
    if (ev) ev.stopPropagation();
    try {
      await fetch(API.documents + "/" + id, { method: "DELETE" });
      await Promise.all([loadDocuments(), loadConversationDocs()]);
    } catch (e) { console.error("Failed to delete document", e); }
  }

  // ==========================================================
  // RENDER: SIDEBAR CONVERSATIONS
  // ==========================================================
  function renderConversationList() {
    conversationList.innerHTML = "";

    if (conversations.length === 0) {
      var empty = document.createElement("div");
      empty.className = "sidebar-doc-empty";
      empty.textContent = "No conversations yet";
      conversationList.appendChild(empty);
      return;
    }

    var groups = groupByDate(conversations);
    groups.forEach(function (g) {
      var lbl = document.createElement("div");
      lbl.className = "conversation-group-label";
      lbl.textContent = g.label;
      conversationList.appendChild(lbl);

      g.items.forEach(function (conv) {
        var item = document.createElement("div");
        item.className = "conversation-item" + (conv.id === activeConversationId ? " active" : "");
        item.innerHTML =
          '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>' +
          '<span class="conversation-item-title">' + esc(conv.title) + '</span>' +
          '<button class="conversation-item-delete" title="Delete"><svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>';

        item.addEventListener("click", function () { switchConversation(conv.id); });
        item.querySelector(".conversation-item-delete").addEventListener("click", function (e) { deleteConversation(conv.id, e); });
        conversationList.appendChild(item);
      });
    });
  }

  function groupByDate(items) {
    var now = new Date();
    var todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var yesterday = new Date(todayStart); yesterday.setDate(yesterday.getDate() - 1);
    var week = new Date(todayStart); week.setDate(week.getDate() - 7);

    var g = { today: { label: "Today", items: [] }, yesterday: { label: "Yesterday", items: [] }, week: { label: "Previous 7 Days", items: [] }, older: { label: "Older", items: [] } };

    items.forEach(function (item) {
      var d = new Date(item.updated_at || item.created_at);
      if (d >= todayStart) g.today.items.push(item);
      else if (d >= yesterday) g.yesterday.items.push(item);
      else if (d >= week) g.week.items.push(item);
      else g.older.items.push(item);
    });

    return Object.values(g).filter(function (x) { return x.items.length > 0; });
  }

  // ==========================================================
  // RENDER: SIDEBAR DOCUMENTS
  // ==========================================================
  function renderDocumentList() {
    documentList.innerHTML = "";

    if (documents.length === 0) {
      var empty = document.createElement("div");
      empty.className = "sidebar-doc-empty";
      empty.textContent = "No documents uploaded";
      documentList.appendChild(empty);
      return;
    }

    documents.forEach(function (doc) {
      var item = document.createElement("div");
      item.className = "sidebar-doc-item";

      var statusClass = doc.status === "ready" ? "ready" : doc.status === "processing" ? "processing" : doc.status === "error" ? "error" : "";
      var statusIcon = doc.status === "ready" ? "✓" : doc.status === "processing" ? "⏳" : doc.status === "error" ? "✗" : "•";

      item.innerHTML =
        '<span class="sidebar-doc-item-icon">📄</span>' +
        '<span class="sidebar-doc-item-name">' + esc(doc.filename) + '</span>' +
        '<span class="sidebar-doc-item-status ' + statusClass + '">' + statusIcon + '</span>' +
        '<button class="sidebar-doc-item-delete" title="Delete"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>';

      item.querySelector(".sidebar-doc-item-delete").addEventListener("click", function (e) { deleteDocument(doc.id, e); });
      documentList.appendChild(item);
    });
  }

  // ==========================================================
  // RENDER: DOCUMENT CARDS (top of chat)
  // ==========================================================
  function renderDocCards(docs) {
    docCardsContainer.innerHTML = "";

    if (!docs || docs.length === 0) { hideDocCards(); return; }

    docs.forEach(function (doc) {
      var card = document.createElement("div");
      card.className = "doc-card";

      var statusClass = doc.status === "ready" ? "ready" : doc.status === "processing" ? "processing" : "error";
      var statusText = doc.status === "ready" ? "Ready ✓" : doc.status === "processing" ? "Processing..." : "Error";
      var meta = "";
      if (doc.page_count) meta += doc.page_count + " pages";
      if (doc.chunk_count) meta += (meta ? " · " : "") + doc.chunk_count + " chunks";

      card.innerHTML =
        '<span class="doc-card-icon">📄</span>' +
        '<div class="doc-card-info">' +
          '<div class="doc-card-name">' + esc(doc.filename) + '</div>' +
          '<div class="doc-card-meta"><span class="doc-card-status ' + statusClass + '">' + statusText + '</span>' + (meta ? '<span>' + meta + '</span>' : '') + '</div>' +
        '</div>' +
        '<button class="doc-card-remove" title="Remove"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>';

      card.querySelector(".doc-card-remove").addEventListener("click", function () { deleteDocument(doc.id); });
      docCardsContainer.appendChild(card);
    });

    docCardsBar.classList.remove("hidden");
  }

  function hideDocCards() {
    docCardsBar.classList.add("hidden");
    docCardsContainer.innerHTML = "";
  }

  // ==========================================================
  // RENDER: WELCOME
  // ==========================================================
  function renderWelcome() {
    welcomeScreen.innerHTML = "";

    var icon = document.createElement("img");
    icon.src = "/static/assets/favicon.svg";
    icon.alt = "MediResearch AI";
    icon.className = "welcome-icon";
    welcomeScreen.appendChild(icon);

    var title = document.createElement("h2");
    title.className = "welcome-title";
    title.innerHTML = "Welcome to <span>MediResearch AI</span>";
    welcomeScreen.appendChild(title);

    var subtitle = document.createElement("p");
    subtitle.className = "welcome-subtitle";
    subtitle.textContent = "Your AI-powered medical research assistant";
    welcomeScreen.appendChild(subtitle);

    var instruction = document.createElement("p");
    instruction.className = "welcome-instruction";
    instruction.textContent = "Upload a research paper and ask questions about it. Get evidence-based answers with source citations.";
    welcomeScreen.appendChild(instruction);

    var grid = document.createElement("div");
    grid.className = "welcome-suggestions";
    SUGGESTIONS.forEach(function (s) {
      var card = document.createElement("button");
      card.className = "suggestion-card";
      card.innerHTML = '<span class="suggestion-card-icon">' + s.icon + '</span><span>' + esc(s.text) + '</span>';
      card.addEventListener("click", function () {
        questionInput.value = s.text;
        autoResizeInput();
        updateSendBtn();
        questionInput.focus();
      });
      grid.appendChild(card);
    });
    welcomeScreen.appendChild(grid);

    welcomeScreen.style.display = "flex";
    chatMessages.style.display = "none";
  }

  function hideWelcome() {
    welcomeScreen.style.display = "none";
    chatMessages.style.display = "flex";
  }

  // ==========================================================
  // RENDER: MESSAGES
  // ==========================================================
  var DNA_SVG = '<svg viewBox="0 0 64 64" fill="none"><path d="M20 8C20 8 44 20 44 32C44 44 20 56 20 56" stroke="#3b82f6" stroke-width="3" stroke-linecap="round"/><path d="M44 8C44 8 20 20 20 32C20 44 44 56 44 56" stroke="#06d6a0" stroke-width="3" stroke-linecap="round"/></svg>';
  var DNA_ERR = '<svg viewBox="0 0 64 64" fill="none"><path d="M20 8C20 8 44 20 44 32C44 44 20 56 20 56" stroke="#ef4444" stroke-width="3" stroke-linecap="round"/><path d="M44 8C44 8 20 20 20 32C20 44 44 56 44 56" stroke="#ef4444" stroke-width="3" stroke-linecap="round"/></svg>';

  function renderUserMessage(msg) {
    var row = document.createElement("div");
    row.className = "message-row user-message";
    row.innerHTML =
      '<div class="message-avatar">U</div>' +
      '<div class="message-body">' +
        '<div class="message-sender">You</div>' +
        '<div class="message-content">' + esc(msg.content) + '</div>' +
        '<div class="message-timestamp">' + fmtTime(msg.created_at) + '</div>' +
      '</div>';
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  function renderAIMessage(msg) {
    var row = document.createElement("div");
    row.className = "message-row ai-message";

    var sourcesHtml = "";
    if (msg.sources && msg.sources.length > 0) sourcesHtml = buildSourcesHtml(msg.sources);

    row.innerHTML =
      '<div class="message-avatar">' + DNA_SVG + '</div>' +
      '<div class="message-body">' +
        '<div class="message-sender">MediResearch AI</div>' +
        '<div class="message-content">' + fmtAnswer(msg.content) + '</div>' +
        sourcesHtml +
        '<div class="message-timestamp">' + fmtTime(msg.created_at) + '</div>' +
      '</div>';

    chatMessages.appendChild(row);

    var toggle = row.querySelector(".sources-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        var list = row.querySelector(".sources-list");
        toggle.classList.toggle("expanded");
        list.classList.toggle("visible");
      });
    }
    scrollToBottom();
  }

  function buildSourcesHtml(sources) {
    var cards = "";
    sources.forEach(function (s) {
      cards +=
        '<div class="source-card">' +
          '<span class="source-card-icon">📄</span>' +
          '<div class="source-card-details">' +
            srcDetail("Source", s.source || "Unknown") +
            srcDetail("Page", s.page != null ? s.page : "N/A") +
            srcDetail("Chunk", s.chunk != null ? s.chunk : "N/A") +
          '</div>' +
        '</div>';
    });
    return '<div class="sources-container">' +
      '<button class="sources-toggle"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>' +
      sources.length + ' Source' + (sources.length !== 1 ? 's' : '') + '</button>' +
      '<div class="sources-list">' + cards + '</div></div>';
  }

  function srcDetail(label, value) {
    return '<span class="source-card-detail"><span class="label">' + label + ':</span><span class="value">' + esc(String(value)) + '</span></span>';
  }

  function renderErrorMessage(msg, question) {
    var row = document.createElement("div");
    row.className = "message-row ai-message";
    row.innerHTML =
      '<div class="message-avatar">' + DNA_ERR + '</div>' +
      '<div class="message-body">' +
        '<div class="message-sender" style="color:var(--error)">Error</div>' +
        '<div class="message-content error-content">' +
          '<p class="error-text">' + esc(msg.content) + '</p>' +
          '<button class="retry-btn"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>Retry</button>' +
        '</div>' +
        '<div class="message-timestamp">' + fmtTime(msg.created_at) + '</div>' +
      '</div>';
    chatMessages.appendChild(row);

    if (question) {
      row.querySelector(".retry-btn").addEventListener("click", function () {
        row.remove();
        questionInput.value = question;
        autoResizeInput();
        updateSendBtn();
        handleSend();
      });
    }
    scrollToBottom();
  }

  function renderThinking() {
    var el = document.createElement("div");
    el.className = "thinking-indicator";
    el.innerHTML =
      '<div class="message-avatar">' + DNA_SVG + '</div>' +
      '<div class="thinking-bubble"><span class="thinking-dot"></span><span class="thinking-dot"></span><span class="thinking-dot"></span></div>';
    chatMessages.appendChild(el);
    return el;
  }

  // ==========================================================
  // SIDEBAR TOGGLE
  // ==========================================================
  function toggleSidebar() { sidebar.classList.toggle("open"); sidebarOverlay.classList.toggle("visible"); }
  function closeSidebar() { sidebar.classList.remove("open"); sidebarOverlay.classList.remove("visible"); }

  // ==========================================================
  // UTILITIES
  // ==========================================================
  function scrollToBottom() { requestAnimationFrame(function () { chatArea.scrollTop = chatArea.scrollHeight; }); }
  function removeEl(el) { if (el && el.parentNode) el.parentNode.removeChild(el); }
  function delay(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function esc(text) {
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(text));
    return d.innerHTML;
  }

  function fmtTime(iso) {
    try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
    catch (e) { return ""; }
  }

  function fmtAnswer(text) {
    var paras = text.split(/\n\n+/);
    var html = paras.map(function (p) {
      var t = p.trim();
      if (!t) return "";
      t = esc(t).replace(/\n/g, "<br>");
      // Bold markers
      t = t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      return "<p>" + t + "</p>";
    }).filter(function (x) { return x !== ""; }).join("");
    return html || "<p>" + esc(text) + "</p>";
  }

  // ==========================================================
  // START
  // ==========================================================
  document.addEventListener("DOMContentLoaded", init);
})();
