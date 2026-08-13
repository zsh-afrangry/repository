(() => {
  "use strict";

  const SVG_NS = "http://www.w3.org/2000/svg";
  const DATA_ROOT = "../data";
  const STATIC_ASSETS = window.__TRANSFORMER_STATIC_ASSETS__ || null;
  const THEME_STORAGE_KEY = "transformer-tutorial-theme";
  const LEARNING_STORAGE_KEY = "transformer-tutorial-learning-state";
  const GRAPH_LAYER_INSET = 32;
  const PAGE_WHEEL_LOCK_MS = 720;
  const PAGE_WHEEL_DELTA_THRESHOLD = 20;
  const MATH_RENDER_TIMEOUT_MS = 6000;
  const state = {
    selectedId: null,
    learningId: null,
    lessonId: null,
    showAllEdgeLabels: false,
    showAllEdgeArrows: false,
    showNodeNames: true
  };

  const els = {
    graphCard: document.querySelector("#graphCard"),
    mapSection: document.querySelector(".map-section"),
    graphViewport: document.querySelector("#graphViewport"),
    svg: document.querySelector("#knowledgeGraph"),
    viewportGroup: document.querySelector("#viewportGroup"),
    edgesLayer: document.querySelector("#edgesLayer"),
    edgeLabelsLayer: document.querySelector("#edgeLabelsLayer"),
    nodesLayer: document.querySelector("#nodesLayer"),
    tooltip: document.querySelector("#tooltip"),
    inspector: document.querySelector("#nodeInspector"),
    returnGraph: document.querySelector("#returnGraph"),
    continueLearning: document.querySelector("#continueLearning"),
    viewLabel: document.querySelector("#viewLabel"),
    layerHeadings: document.querySelector(".layer-headings"),
    layerBands: document.querySelector(".layer-bands"),
    lessonSection: document.querySelector("#lessonSection"),
    lessonPlaceholder: document.querySelector("#lessonPlaceholder"),
    lessonDocument: document.querySelector("#lessonDocument"),
    lessonMarkdown: document.querySelector("#lessonMarkdown"),
    themeToggle: document.querySelector("#themeToggle"),
    toggleEdgeLabels: document.querySelector("#toggleEdgeLabels"),
    toggleEdgeArrows: document.querySelector("#toggleEdgeArrows"),
    toggleNodeNames: document.querySelector("#toggleNodeNames"),
    resetLearningState: document.querySelector("#resetLearningState"),
    printNodePositions: document.querySelector("#printNodePositions")
  };

  let nodes = [];
  let edges = [];
  let layerNames = [];
  let nodeById = new Map();
  let graphWidth = 720;
  let graphHeight = 520;
  let graphResizeFrame = 0;
  let dragState = null;
  let suppressNodeClick = false;
  let fullGraphLayoutReady = false;
  let pageWheelLockedUntil = 0;
  let lessonRenderSequence = 0;
  let mathRenderQueue = Promise.resolve();
  let nextLessonTimer = null;
  let fixedFullGraphBounds = null;

  // 将资源路径归一化为打包资源表中的项目根相对路径。
  const normalizeAssetKey = path => {
    const rawPath = String(path || "").split("#")[0].split("?")[0].replaceAll("\\", "/");
    let decodedPath = rawPath;
    try {
      decodedPath = decodeURI(rawPath);
    } catch (error) {
      decodedPath = rawPath;
    }

    const segments = [];
    decodedPath.split("/").forEach(segment => {
      if (!segment || segment === ".") return;
      if (segment === "..") {
        segments.pop();
        return;
      }
      segments.push(segment);
    });

    const joined = segments.join("/");
    const rootIndex = segments.findIndex(segment => ["content", "data", "resources", "frontend"].includes(segment));
    return rootIndex >= 0 ? segments.slice(rootIndex).join("/") : joined;
  };

  const embeddedText = path => STATIC_ASSETS?.text?.[normalizeAssetKey(path)];

  const embeddedResourceUrl = path => {
    if (!STATIC_ASSETS || /^(data:|blob:|https?:)?\/\//.test(String(path))) return null;
    const asset = STATIC_ASSETS.binary?.[normalizeAssetKey(path)];
    return asset ? `data:${asset.mime};base64,${asset.data}` : null;
  };

  const resourceUrl = path => embeddedResourceUrl(path) || path;

  // 读取并解析 JSON 数据文件。
  const readJson = async path => {
    const embedded = embeddedText(path);
    if (typeof embedded === "string") return JSON.parse(embedded);
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Cannot load ${path}`);
    return response.json();
  };

  // 读取文本资源内容。
  const readText = async path => {
    const embedded = embeddedText(path);
    if (typeof embedded === "string") return embedded;
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Cannot load ${path}`);
    return response.text();
  };

  // 将内容资源路径转换为页面可访问路径。
  const assetPath = path => {
    if (/^(https?:)?\/\//.test(path) || path.startsWith("../") || path.startsWith("/")) return path;
    return `../${path}`;
  };

  // 转义 HTML 特殊字符，避免插入不安全标记。
  const escapeHtml = value => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

  // 渲染简单的行内 Markdown 语法。
  const renderInlineMarkdown = value => escapeHtml(value)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

  // 在 marked 不可用时提供基础 Markdown 渲染。
  const markdownToHtml = markdown => {
    const lines = markdown.replace(/\r\n/g, "\n").split("\n");
    const html = [];
    let paragraph = [];
    let listOpen = false;

    // 将累积的段落文本写入 HTML。
    const flushParagraph = () => {
      if (!paragraph.length) return;
      html.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`);
      paragraph = [];
    };

    // 关闭当前打开的无序列表。
    const closeList = () => {
      if (!listOpen) return;
      html.push("</ul>");
      listOpen = false;
    };

    lines.forEach(line => {
      const trimmed = line.trim();
      if (!trimmed) {
        flushParagraph();
        closeList();
        return;
      }

      const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph();
        closeList();
        const level = heading[1].length + 1;
        html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
        return;
      }

      const bullet = trimmed.match(/^[-*]\s+(.+)$/);
      if (bullet) {
        flushParagraph();
        if (!listOpen) {
          html.push("<ul>");
          listOpen = true;
        }
        html.push(`<li>${renderInlineMarkdown(bullet[1])}</li>`);
        return;
      }

      paragraph.push(trimmed);
    });

    flushParagraph();
    closeList();
    return html.join("");
  };

  // 临时保护行间与行内公式，避免反斜杠、下划线等 TeX 内容被 Markdown 解析破坏。
  const protectMath = markdown => {
    const blocks = [];
    const inlines = [];
    // 记录行间公式并返回独立段落占位符。
    const addBlock = tex => {
      const token = `@@MATHJAXBLOCK${blocks.length}@@`;
      blocks.push(`<div class="math-block">\\[${escapeHtml(tex.trim())}\\]</div>`);
      return `\n\n${token}\n\n`;
    };
    // 记录行内公式并返回不会被 marked 改写的占位符。
    const addInline = tex => {
      const token = `@@MATHJAXINLINE${inlines.length}@@`;
      inlines.push(`<span class="math-inline">\\(${escapeHtml(tex.trim())}\\)</span>`);
      return token;
    };
    const protectedMarkdown = markdown
      .replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => addBlock(tex))
      .replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) => addBlock(tex))
      .replace(/\\\((.+?)\\\)/g, (_, tex) => addInline(tex))
      .replace(/(^|[^\\$])\$(?!\$)([^\n$]+?)\$(?!\$)/g, (_, prefix, tex) => `${prefix}${addInline(tex)}`);
    return { protectedMarkdown, blocks, inlines };
  };

  // 将 Markdown 渲染后的公式占位符还原为 MathJax 可识别的公式元素。
  const restoreMath = (html, blocks, inlines) => {
    const withBlocks = blocks.reduce((result, block, index) => {
      const token = `@@MATHJAXBLOCK${index}@@`;
      return result
        .replace(new RegExp(`<p>\\s*${token}\\s*</p>`, "g"), block)
        .replaceAll(token, block);
    }, html);
    return inlines.reduce((result, inline, index) => {
      return result.replaceAll(`@@MATHJAXINLINE${index}@@`, inline);
    }, withBlocks);
  };

  // 判断图片路径是否指向 GIF 文件。
  const isGifSource = src => /\.gif(?:[?#].*)?$/i.test(src.trim());

  // 根据 GIF 路径推导第一帧占位图路径。
  const getGifPosterSource = src => src.replace(/\.gif(?=([?#]|$))/i, ".poster.png");

  // 将 Markdown 中的 GIF 图片替换为点击播放组件。
  const enhanceGifImages = html => {
    const template = document.createElement("template");
    template.innerHTML = html;
    template.content.querySelectorAll("img").forEach(image => {
      const src = image.getAttribute("src") || "";
      if (!isGifSource(src)) return;

      const alt = image.getAttribute("alt") || "GIF 动图";
      const figure = document.createElement("figure");
      figure.className = "gif-player";
      figure.dataset.gifPlayer = "idle";
      figure.dataset.gifSrc = resourceUrl(src);
      figure.dataset.gifAlt = alt;

      const poster = document.createElement("img");
      poster.className = "gif-player__poster";
      poster.src = resourceUrl(getGifPosterSource(src));
      poster.alt = "";
      poster.loading = "lazy";
      poster.decoding = "async";
      poster.setAttribute("aria-hidden", "true");

      const button = document.createElement("button");
      button.className = "gif-player__button";
      button.type = "button";
      button.setAttribute("aria-label", `开始播放 ${alt}`);

      const icon = document.createElement("span");
      icon.className = "gif-player__icon";
      icon.setAttribute("aria-hidden", "true");

      const label = document.createElement("span");
      label.textContent = "开始播放 GIF";

      button.append(icon, label);
      figure.append(poster, button);
      image.replaceWith(figure);
    });
    template.content.querySelectorAll("img").forEach(image => {
      const src = image.getAttribute("src") || "";
      if (isGifSource(src)) return;
      image.src = resourceUrl(src);
    });
    return template.innerHTML;
  };

  // 渲染完整 Markdown，并处理 Obsidian 图片、公式和 GIF。
  const renderMarkdown = markdown => {
    const normalizedMarkdown = markdown.replace(/!\[\[([^\]]+)\]\]/g, (_, rawPath) => {
      const path = rawPath.trim().replace(/^\.\.\/\.\.\//, "../");
      const src = encodeURI(path);
      const alt = path.split("/").pop()?.replace(/\.[^.]+$/, "").replace(/[\[\]]/g, "") || "image";
      return `![${alt}](${src})`;
    });
    const { protectedMarkdown, blocks, inlines } = protectMath(normalizedMarkdown);
    const parser = window.marked;
    if (parser?.setOptions) parser.setOptions({ gfm: true, breaks: false });
    const html = parser?.parse
      ? parser.parse(protectedMarkdown)
      : typeof parser === "function"
        ? parser(protectedMarkdown)
        : markdownToHtml(protectedMarkdown);
    return enhanceGifImages(restoreMath(html, blocks, inlines));
  };

  // 串行执行：等待上一次 MathJax -> 清理旧记录 -> 更新 DOM -> 渲染新公式。
  const disableMathJaxSpeech = mathJax => {
    const options = mathJax?.startup?.document?.options;
    if (options) {
      options.enableSpeech = false;
      options.enableBraille = false;
      options.enableExplorer = false;
      options.enableEnrichment = false;
      if (options.a11y) {
        options.a11y.speech = false;
        options.a11y.braille = false;
      }
    }
    mathJax?.startup?.document?.removeRenderAction?.("attachSpeech");
  };

  const containsMath = html => html.includes("math-block") || html.includes("math-inline");

  const updateLessonMarkdown = (html, renderSequence) => {
    mathRenderQueue = mathRenderQueue
      .catch(error => {
        console.error("上一次 MathJax 渲染失败：", error);
      })
      .then(async () => {
        if (renderSequence !== lessonRenderSequence) return false;

        const container = els.lessonMarkdown;
        const mathJax = window.MathJax;
        if (!container) throw new Error("找不到 #lessonMarkdown 容器");

        if (typeof mathJax?.typesetClear === "function") {
          mathJax.typesetClear([container]);
        }

        container.innerHTML = html;
        prepareGifPosters(container);

        if (!containsMath(html)) return renderSequence === lessonRenderSequence;

        if (mathJax?.startup?.promise) {
          await withTimeout(mathJax.startup.promise, MATH_RENDER_TIMEOUT_MS, "MathJax 初始化超时");
        }
        disableMathJaxSpeech(mathJax);
        if (renderSequence !== lessonRenderSequence) return false;

        if (!mathJax) {
          console.warn("MathJax 未加载，已保留未排版的公式文本。");
          return true;
        }

        if (typeof mathJax.typesetPromise !== "function") {
          console.warn("MathJax.typesetPromise 不可用，已保留未排版的公式文本。");
          return true;
        }

        try {
          await withTimeout(
            mathJax.typesetPromise([container]),
            MATH_RENDER_TIMEOUT_MS,
            "MathJax 公式渲染超时"
          );
        } catch (error) {
          console.error("MathJax 公式渲染失败，已保留未排版的公式文本：", error);
          return true;
        }
        return renderSequence === lessonRenderSequence;
      });

    return mathRenderQueue;
  };

  // 监听 GIF 占位图加载状态并更新播放器样式。
  const prepareGifPosters = container => {
    container.querySelectorAll(".gif-player__poster").forEach(poster => {
      if (poster.complete && poster.naturalWidth > 0) {
        const player = poster.closest(".gif-player");
        player?.classList.add("has-poster");
        if (player) player.style.setProperty("--gif-aspect-ratio", `${poster.naturalWidth} / ${poster.naturalHeight}`);
        return;
      }
      poster.addEventListener("load", () => {
        const player = poster.closest(".gif-player");
        player?.classList.add("has-poster");
        if (player) player.style.setProperty("--gif-aspect-ratio", `${poster.naturalWidth} / ${poster.naturalHeight}`);
      }, { once: true });
      poster.addEventListener("error", () => {
        poster.remove();
      }, { once: true });
    });
  };

  // 将 GIF 播放器从占位状态切换为真实 GIF 播放。
  const playGif = button => {
    const player = button.closest(".gif-player");
    const src = player?.dataset.gifSrc;
    if (!player || !src || player.dataset.gifPlayer !== "idle") return;

    const captionText = player.dataset.gifAlt || "GIF 动图";
    const image = document.createElement("img");
    image.alt = player.dataset.gifAlt || captionText;
    image.decoding = "async";

    const bounds = player.getBoundingClientRect();
    if (bounds.height > 0) player.style.minHeight = `${Math.ceil(bounds.height)}px`;
    player.dataset.gifPlayer = "loading";
    button.disabled = true;
    button.setAttribute("aria-label", `正在加载 ${captionText}`);

    image.addEventListener("load", () => {
      player.dataset.gifPlayer = "playing";
      player.replaceChildren(image);
      window.requestAnimationFrame(() => {
        player.style.minHeight = "";
      });
    }, { once: true });

    image.addEventListener("error", () => {
      player.dataset.gifPlayer = "idle";
      player.style.minHeight = "";
      button.disabled = false;
      button.setAttribute("aria-label", `开始播放 ${captionText}`);
    }, { once: true });

    image.src = src;
  };

  // 清除所有节点的正在学习状态。
  const clearLearningStatuses = () => {
    nodes.forEach(node => {
      if (node.status === "learning") node.status = null;
    });
  };

  // 设置唯一的正在学习节点。
  const setSingleLearningNode = id => {
    clearLearningStatuses();
    const node = id ? nodeById.get(id) : null;
    if (!node || node.status === "mastered") {
      state.learningId = null;
      return null;
    }
    node.status = "learning";
    state.learningId = node.id;
    return node;
  };

  // 获取当前有效的正在学习节点。
  const getLearningNode = () => {
    const current = state.learningId ? nodeById.get(state.learningId) : null;
    if (current && current.status !== "mastered") return current;
    return nodes.find(node => node.status === "learning") || null;
  };

  // 规范化学习状态，确保最多只有一个正在学习节点。
  const normalizeLearningState = () => {
    const learningNode = getLearningNode();
    setSingleLearningNode(learningNode?.id || null);
  };

  // 从本地存储读取学习状态。
  const readSavedLearningState = () => {
    try {
      const raw = window.localStorage.getItem(LEARNING_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (error) {
      console.warn("Unable to read learning state.", error);
      return null;
    }
  };

  // 将已掌握节点和当前学习节点保存到本地存储。
  const saveLearningState = () => {
    normalizeLearningState();
    const masteredIds = nodes
      .filter(node => node.status === "mastered")
      .map(node => node.id);
    const learningNode = state.learningId ? nodeById.get(state.learningId) : null;
    const learningId = learningNode && learningNode.status !== "mastered" ? learningNode.id : null;
    try {
      window.localStorage.setItem(LEARNING_STORAGE_KEY, JSON.stringify({
        masteredIds,
        learningId,
        savedAt: new Date().toISOString()
      }));
    } catch (error) {
      console.warn("Unable to save learning state.", error);
    }
  };

  // 将本地存储中的学习状态应用到节点数据。
  const applySavedLearningState = () => {
    const saved = readSavedLearningState();
    if (!saved) {
      normalizeLearningState();
      return;
    }

    const masteredIds = Array.isArray(saved.masteredIds) ? saved.masteredIds : [];
    const masteredSet = new Set(masteredIds.filter(id => nodeById.has(id)));
    nodes.forEach(node => {
      node.status = masteredSet.has(node.id) ? "mastered" : null;
    });

    const learningId = typeof saved.learningId === "string" && nodeById.has(saved.learningId)
      ? saved.learningId
      : null;
    setSingleLearningNode(learningId && !masteredSet.has(learningId) ? learningId : null);
  };

  // 根据主题、依赖和位置数据构建节点、边和层级索引。
  const buildGraphData = (topicData, dependencyData, positionData = []) => {
    fullGraphLayoutReady = false;
    fixedFullGraphBounds = null;
    const layerKeys = [...new Set(topicData.map(topic => topic.layer || "default"))];
    layerNames = layerKeys.map(layerKey => {
      const topic = topicData.find(item => (item.layer || "default") === layerKey);
      return topic?.layerName || layerKey;
    });
    const positions = new Map(
      (Array.isArray(positionData) ? positionData : [])
        .filter(item => item?.id && Number.isFinite(Number(item.x)) && Number.isFinite(Number(item.y)))
        .map(item => [item.id, { x: Number(item.x), y: Number(item.y) }])
    );

    nodes = topicData.map((topic, order) => {
      const layer = layerKeys.indexOf(topic.layer || "default");
      const initialStatus = ["mastered", "learning"].includes(topic.status) ? topic.status : null;
      const position = positions.get(topic.id);
      return {
        id: topic.id,
        order,
        layer,
        x: position?.x ?? 0,
        y: position?.y ?? 0,
        baseX: position?.x ?? null,
        baseY: position?.y ?? null,
        title: topic.title,
        brief: topic.brief,
        documentPath: topic.documentPath,
        status: initialStatus,
        estimatedMinutes: topic.estimatedMinutes,
        tags: topic.tags || []
      };
    });
    const allNodesPositioned = nodes.length > 0 && nodes.every(node => positions.has(node.id));
    if (allNodesPositioned) {
      const xs = nodes.map(node => node.baseX);
      const ys = nodes.map(node => node.baseY);
      fixedFullGraphBounds = {
        minX: Math.min(...xs),
        maxX: Math.max(...xs),
        minY: Math.min(...ys),
        maxY: Math.max(...ys)
      };
      fullGraphLayoutReady = true;
    }

    nodeById = new Map(nodes.map(node => [node.id, node]));
    edges = dependencyData
      .filter(edge => nodeById.has(edge.prerequisiteId) && nodeById.has(edge.topicId))
      .map(edge => ({
        from: edge.prerequisiteId,
        to: edge.topicId,
        type: edge.type || "required",
        relation: edge.relation || "相关"
      }));
    applySavedLearningState();
  };

  // 计算完整知识图谱中各节点的分栏布局位置。
  const layoutFullGraph = () => {
    const layerInset = Number.parseFloat(
      window.getComputedStyle(els.graphCard).getPropertyValue("--graph-layer-inset")
    ) || GRAPH_LAYER_INSET;
    // 生成稳定的轻微错位值，避免节点完全对齐。
    const staggerUnit = (index, salt) => ((((index + 1) * .61803398875 + salt) % 1) * 2) - 1;
    // 在指定轴上拉开过近节点并限制到栏位内。
    const separateAxis = (items, axis, min, max, preferredGap) => {
      if (items.length < 2) return;
      const ordered = [...items].sort((a, b) => a[axis] - b[axis]);
      const gap = Math.min(preferredGap, Math.max(0, (max - min) / (ordered.length - 1)));
      for (let index = 1; index < ordered.length; index += 1) {
        ordered[index][axis] = Math.max(ordered[index][axis], ordered[index - 1][axis] + gap);
      }
      for (let index = ordered.length - 2; index >= 0; index -= 1) {
        ordered[index][axis] = Math.min(ordered[index][axis], ordered[index + 1][axis] - gap);
      }
      const lowOverflow = min - ordered[0][axis];
      if (lowOverflow > 0) ordered.forEach(node => { node[axis] += lowOverflow; });
      const highOverflow = ordered[ordered.length - 1][axis] - max;
      if (highOverflow > 0) ordered.forEach(node => { node[axis] -= highOverflow; });
      ordered.forEach(node => {
        node[axis] = clamp(node[axis], min, max);
      });
    };
    const columnCount = Math.max(layerNames.length, 1);
    const columnWidth = (graphWidth - layerInset * 2) / columnCount;
    const graphTop = 62;
    const graphBottom = Math.max(graphTop, graphHeight - 72);
    const graphRangeY = graphBottom - graphTop;

    layerNames.forEach((_, layerIndex) => {
      const siblings = nodes
        .filter(item => item.layer === layerIndex)
        .sort((a, b) => a.order - b.order);
      if (!siblings.length) return;

      const columnLeft = layerInset + columnWidth * layerIndex;
      const columnRight = columnLeft + columnWidth;
      const columnPadding = Math.min(28, Math.max(12, columnWidth * .13));
      const usableLeft = columnLeft + columnPadding;
      const usableRight = columnRight - columnPadding;
      const usableWidth = Math.max(1, usableRight - usableLeft);
      const comfortableRows = Math.max(1, Math.floor(graphRangeY / 72));
      const maxColumns = Math.max(1, Math.min(4, Math.floor(usableWidth / 50) + 1));
      const columnSlots = Math.min(maxColumns, Math.max(1, Math.ceil(siblings.length / comfortableRows)));
      const rows = Math.ceil(siblings.length / columnSlots);
      const cellWidth = columnSlots === 1 ? Math.max(1, columnRight - columnLeft - 36) : usableWidth / columnSlots;
      const cellHeight = Math.max(1, graphRangeY / rows);
      const xJitterRange = Math.min(24, Math.max(8, cellWidth * .42));
      const yJitterRange = Math.min(22, Math.max(8, cellHeight * .24));

      siblings.forEach((node, index) => {
        const row = Math.floor(index / columnSlots);
        const col = index % columnSlots;
        const itemsInRow = Math.min(columnSlots, siblings.length - row * columnSlots);
        const centeredCol = col + (columnSlots - itemsInRow) / 2;
        const baseX = columnSlots === 1
          ? columnLeft + columnWidth / 2
          : usableLeft + cellWidth * (centeredCol + .5);
        const baseY = graphTop + cellHeight * (row + .5);
        const shouldStagger = siblings.length > 1;
        const xSeed = staggerUnit(index, layerIndex * .137);
        const ySeed = staggerUnit(index, .37 + layerIndex * .271);
        const x = baseX + (shouldStagger ? xSeed * xJitterRange : 0);
        const y = baseY + (shouldStagger ? ySeed * yJitterRange : 0);

        node.x = clamp(x, columnLeft + 18, columnRight - 18);
        node.y = clamp(y, graphTop, graphBottom);
      });

      for (let pass = 0; pass < 3; pass += 1) {
        for (let aIndex = 0; aIndex < siblings.length; aIndex += 1) {
          for (let bIndex = aIndex + 1; bIndex < siblings.length; bIndex += 1) {
            const a = siblings[aIndex];
            const b = siblings[bIndex];
            const dx = Math.abs(a.x - b.x);
            const dy = Math.abs(a.y - b.y);
            if (dx < 2.5) {
              const direction = ((aIndex + bIndex + pass) % 2 === 0) ? 1 : -1;
              const push = (2.5 - dx) / 2 + .6;
              a.x = clamp(a.x - direction * push, columnLeft + 18, columnRight - 18);
              b.x = clamp(b.x + direction * push, columnLeft + 18, columnRight - 18);
            }
            if (dy < 2.5) {
              const direction = ((aIndex + bIndex + pass) % 2 === 0) ? 1 : -1;
              const push = (2.5 - dy) / 2 + .6;
              a.y = clamp(a.y - direction * push, graphTop, graphBottom);
              b.y = clamp(b.y + direction * push, graphTop, graphBottom);
            }
          }
        }
      }

      separateAxis(siblings, "x", columnLeft + 18, columnRight - 18, 2.5);
      separateAxis(siblings, "y", graphTop, graphBottom, 2.5);
    });
  };

  // 将 position.json 的基准坐标缩放到当前完整图谱容器尺寸。
  const scaleFixedFullGraphLayout = () => {
    if (!fixedFullGraphBounds) return;

    const sourceWidth = Math.max(1, fixedFullGraphBounds.maxX - fixedFullGraphBounds.minX);
    const sourceHeight = Math.max(1, fixedFullGraphBounds.maxY - fixedFullGraphBounds.minY);
    const marginX = Math.min(50, Math.max(24, graphWidth * .055));
    const topMargin = Math.min(62, Math.max(42, graphHeight * .09));
    const bottomMargin = Math.min(78, Math.max(48, graphHeight * .11));
    const targetMinX = marginX;
    const targetMaxX = Math.max(targetMinX, graphWidth - marginX);
    const targetMinY = topMargin;
    const targetMaxY = Math.max(targetMinY, graphHeight - bottomMargin);
    const scaleX = (targetMaxX - targetMinX) / sourceWidth;
    const scaleY = (targetMaxY - targetMinY) / sourceHeight;

    nodes.forEach(node => {
      if (!Number.isFinite(node.baseX) || !Number.isFinite(node.baseY)) return;
      node.x = targetMinX + (node.baseX - fixedFullGraphBounds.minX) * scaleX;
      node.y = targetMinY + (node.baseY - fixedFullGraphBounds.minY) * scaleY;
    });
  };

  // 同步 SVG 尺寸、viewBox 和完整图谱布局状态。
  const syncGraphGeometry = focused => {
    const bounds = focused
      ? els.svg.getBoundingClientRect()
      : els.graphViewport.getBoundingClientRect();
    const measuredWidth = Math.round(bounds.width);
    const measuredHeight = Math.round(bounds.height);
    const nextGraphWidth = measuredWidth > 0 ? measuredWidth : 720;
    const nextGraphHeight = measuredHeight > 0 ? measuredHeight : 520;
    const widthChanged = Math.abs(nextGraphWidth - graphWidth) > 1;
    const heightChanged = Math.abs(nextGraphHeight - graphHeight) > 1;
    if (widthChanged) graphWidth = nextGraphWidth;
    if (heightChanged) graphHeight = nextGraphHeight;
    const viewBox = `0 0 ${graphWidth} ${graphHeight}`;
    if (els.svg.getAttribute("viewBox") !== viewBox) els.svg.setAttribute("viewBox", viewBox);
    if (focused) els.graphCard.style.setProperty("--graph-svg-width", `${graphWidth}px`);
    if (!focused && fixedFullGraphBounds) {
      scaleFixedFullGraphLayout();
    }
    if (!focused && !fixedFullGraphBounds && !fullGraphLayoutReady) {
      layoutFullGraph();
      fullGraphLayoutReady = true;
    }
  };

  // 渲染顶部层级标题并同步栏位背景。
  const syncLayerDisplay = () => {
    els.layerHeadings.replaceChildren(...layerNames.map((name, index) => {
      const span = document.createElement("span");
      span.dataset.layer = String(index);
      span.textContent = `${String(index + 1).padStart(2, "0")} · ${name}`;
      return span;
    }));
    els.layerHeadings.style.gridTemplateColumns = `repeat(${Math.max(layerNames.length, 1)}, 1fr)`;
    syncLayerBands(layerNames.length);
  };

  // 按层级数量渲染图谱栏位背景。
  const syncLayerBands = count => {
    const bandCount = Math.max(count, 1);
    els.layerBands.replaceChildren(...Array.from({ length: bandCount }, () => document.createElement("span")));
    els.layerBands.style.gridTemplateColumns = `repeat(${bandCount}, 1fr)`;
  };

  // 获取指向指定节点的前置节点 ID。
  const incoming = id => edges.filter(edge => edge.to === id).map(edge => edge.from);
  // 获取从指定节点出发的后继节点 ID。
  const outgoing = id => edges.filter(edge => edge.from === id).map(edge => edge.to);
  // 获取指定节点的必需前置知识 ID。
  const prerequisiteIds = id => edges
    .filter(edge => edge.to === id && edge.type === "required")
    .map(edge => edge.from);
  // 判断节点是否已掌握。
  const isMastered = id => nodeById.get(id)?.status === "mastered";
  // 判断指定节点的所有必需前置知识是否完成。
  const prerequisitesComplete = id => prerequisiteIds(id).every(isMastered);
  // 判断节点当前是否可以开始学习。
  const isLearnable = node => Boolean(node) && node.status !== "mastered" && prerequisitesComplete(node.id);
  // 获取与指定节点共享前置节点的同级节点。
  const peers = id => {
    const parents = incoming(id);
    const result = new Set();
    parents.forEach(parentId => outgoing(parentId).forEach(childId => {
      if (childId !== id) result.add(childId);
    }));
    return [...result];
  };

  // 计算节点在界面中应展示的学习状态。
  const statusFor = node => {
    if (node.status === "mastered") return "mastered";
    if (state.learningId === node.id || node.status === "learning") return "learning";
    return prerequisitesComplete(node.id) ? "ready" : "locked";
  };

  // 同步线条标签、箭头和节点名称的显示开关。
  const syncGraphDisplayOptions = () => {
    els.graphCard.classList.toggle("show-edge-labels", state.showAllEdgeLabels);
    els.graphCard.classList.toggle("show-edge-arrows", state.showAllEdgeArrows);
    els.graphCard.classList.toggle("hide-node-names", !state.showNodeNames);
    els.toggleEdgeLabels?.setAttribute("aria-pressed", String(state.showAllEdgeLabels));
    els.toggleEdgeArrows?.setAttribute("aria-pressed", String(state.showAllEdgeArrows));
    els.toggleNodeNames?.setAttribute("aria-pressed", String(state.showNodeNames));
  };

  // 根据当前视图同步图谱工具按钮状态。
  const syncGraphToolbarActions = focused => {
    const learningNode = getLearningNode();
    els.returnGraph.hidden = !focused;
    if (!els.continueLearning) return;
    els.continueLearning.hidden = focused;
    els.continueLearning.disabled = !learningNode;
    if (learningNode) {
      els.continueLearning.textContent = "继续学习";
      // els.continueLearning.setAttribute("title", `继续学习：${learningNode.title}`);
    } else {
      els.continueLearning.textContent = "暂无继续学习";
      // els.continueLearning.removeAttribute("title");
    }
  };

  // 将数值限制在指定范围内。
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  // 判断两个矩形区域是否重叠。
  const rectsOverlap = (a, b, padding = 0) => (
    a.left - padding < b.right &&
    a.right + padding > b.left &&
    a.top - padding < b.bottom &&
    a.bottom + padding > b.top
  );

  const paddedBox = (box, padding = 0) => ({
    left: box.left - padding,
    right: box.right + padding,
    top: box.top - padding,
    bottom: box.bottom + padding
  });

  const pointInBox = (point, box) => (
    point.x >= box.left &&
    point.x <= box.right &&
    point.y >= box.top &&
    point.y <= box.bottom
  );

  const direction = (a, b, c) => ((b.x - a.x) * (c.y - a.y)) - ((b.y - a.y) * (c.x - a.x));

  const pointOnSegment = (point, a, b) => (
    Math.min(a.x, b.x) <= point.x &&
    point.x <= Math.max(a.x, b.x) &&
    Math.min(a.y, b.y) <= point.y &&
    point.y <= Math.max(a.y, b.y)
  );

  const segmentsIntersect = (a, b, c, d) => {
    const d1 = direction(a, b, c);
    const d2 = direction(a, b, d);
    const d3 = direction(c, d, a);
    const d4 = direction(c, d, b);
    const epsilon = .001;

    if (((d1 > epsilon && d2 < -epsilon) || (d1 < -epsilon && d2 > epsilon)) &&
      ((d3 > epsilon && d4 < -epsilon) || (d3 < -epsilon && d4 > epsilon))) return true;
    if (Math.abs(d1) <= epsilon && pointOnSegment(c, a, b)) return true;
    if (Math.abs(d2) <= epsilon && pointOnSegment(d, a, b)) return true;
    if (Math.abs(d3) <= epsilon && pointOnSegment(a, c, d)) return true;
    if (Math.abs(d4) <= epsilon && pointOnSegment(b, c, d)) return true;
    return false;
  };

  const segmentIntersectsBox = (source, target, box, padding = 0) => {
    const expanded = paddedBox(box, padding);
    if (pointInBox(source, expanded) || pointInBox(target, expanded)) return true;
    const topLeft = { x: expanded.left, y: expanded.top };
    const topRight = { x: expanded.right, y: expanded.top };
    const bottomRight = { x: expanded.right, y: expanded.bottom };
    const bottomLeft = { x: expanded.left, y: expanded.bottom };
    return segmentsIntersect(source, target, topLeft, topRight) ||
      segmentsIntersect(source, target, topRight, bottomRight) ||
      segmentsIntersect(source, target, bottomRight, bottomLeft) ||
      segmentsIntersect(source, target, bottomLeft, topLeft);
  };

  // 根据中心点和尺寸生成标签碰撞盒。
  const labelBoxAt = (x, y, width, height = 24) => ({
    left: x - width / 2,
    right: x + width / 2,
    top: y - height / 2,
    bottom: y + height / 2
  });

  // 生成节点和节点文字占用的碰撞区域。
  const nodeCollisionBoxes = (positions, focused = false) => {
    const topOffset = focused ? -30 : -22;
    const bottomOffset = focused ? 58 : 44;
    return [...positions.entries()].map(([id, position]) => {
      const title = nodeById.get(id)?.title || "";
      const labelWidth = title.length * (focused ? 9 : 7) + 24;
      const nodeWidth = Math.max(focused ? 150 : 112, Math.min(focused ? 220 : 170, labelWidth));
      return {
        left: position.x - nodeWidth / 2,
        right: position.x + nodeWidth / 2,
        top: position.y + topOffset,
        bottom: position.y + bottomOffset
      };
    });
  };

  // 生成聚焦视图中的直线边路径。
  const curvePath = (source, target) => {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const distance = Math.hypot(dx, dy);
    if (!distance) return `M ${source.x} ${source.y} L ${target.x} ${target.y}`;

    const ux = dx / distance;
    const uy = dy / distance;
    const sourceOffset = Math.min(0, distance / 3);
    const targetOffset = Math.min(12, distance / 3);
    const startX = source.x + ux * sourceOffset;
    const startY = source.y + uy * sourceOffset;
    const endX = target.x - ux * targetOffset;
    const endY = target.y - uy * targetOffset;
    return `M ${startX} ${startY} L ${endX} ${endY}`;
  };

  // 生成完整图谱中的曲线边路径。
  const fullGraphPath = (source, target) => {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const distance = Math.hypot(dx, dy);
    if (!distance) return `M ${source.x} ${source.y} L ${target.x} ${target.y}`;
    const ux = dx / distance;
    const uy = dy / distance;
    const sourceOffset = Math.min(0, distance / 3);
    const targetOffset = Math.min(8, distance / 3);
    const startX = source.x + ux * sourceOffset;
    const startY = source.y + uy * sourceOffset;
    const endX = target.x - ux * targetOffset;
    const endY = target.y - uy * targetOffset;
    const controlX = (source.x + target.x) / 2 - dy * .08;
    const controlY = (source.y + target.y) / 2 + dx * .08;
    return `M ${startX.toFixed(1)} ${startY.toFixed(1)} Q ${controlX.toFixed(1)} ${controlY.toFixed(1)} ${endX.toFixed(1)} ${endY.toFixed(1)}`;
  };

  // 计算完整图谱边标签的默认显示点。
  const fullGraphLabelPoint = (source, target) => {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const controlX = (source.x + target.x) / 2 - dy * .08;
    const controlY = (source.y + target.y) / 2 + dx * .08;
    return {
      x: source.x * .25 + controlX * .5 + target.x * .25,
      y: source.y * .25 + controlY * .5 + target.y * .25
    };
  };

  // 为聚焦视图边标签寻找不遮挡节点和其他标签的位置，优先沿边移动。
  const findEdgeLabelPosition = (source, target, width, occupiedBoxes, blockedBoxes, blockedSegments = []) => {
    const dx = target.x - source.x;
    const dy = target.y - source.y;
    const distance = Math.hypot(dx, dy) || 1;
    const normalX = -dy / distance;
    const normalY = dx / distance;
    const fractions = [.5, .42, .58, .34, .66, .26, .74, .18, .82, .1, .9];
    const offsets = [0, 14, -14, 28, -28];
    const marginX = width / 2 + 8;
    const marginY = 18;
    let best = null;

    fractions.forEach(fraction => {
      offsets.forEach(offset => {
        const rawX = source.x + dx * fraction + normalX * offset;
        const rawY = source.y + dy * fraction + normalY * offset;
        const x = clamp(rawX, marginX, graphWidth - marginX);
        const y = clamp(rawY, marginY, graphHeight - marginY);
        const box = labelBoxAt(x, y, width);
        const labelHits = occupiedBoxes.filter(item => rectsOverlap(box, item, 6)).length;
        const nodeHits = blockedBoxes.filter(item => rectsOverlap(box, item, 8)).length;
        const lineHits = blockedSegments.filter(item => segmentIntersectsBox(item.source, item.target, box, 5)).length;
        const travel = Math.abs(fraction - .5) * 160 + Math.abs(offset) * 8;
        const clampPenalty = Math.abs(rawX - x) + Math.abs(rawY - y);
        const score = nodeHits * 100000 + labelHits * 70000 + lineHits * 35000 + clampPenalty * 5 + travel;
        if (!best || score < best.score) best = { x, y, box, score };
      });
    });

    return best || {
      x: (source.x + target.x) / 2,
      y: (source.y + target.y) / 2,
      box: labelBoxAt((source.x + target.x) / 2, (source.y + target.y) / 2, width)
    };
  };

  // 在聚焦视图中绘制一条边的关系标签。
  const appendEdgeLabel = (edge, source, target, variant, occupiedBoxes, blockedBoxes, blockedSegments) => {
    if (!edge.relation) return;
    const width = Math.max(34, edge.relation.length * 13 + 18);
    const position = findEdgeLabelPosition(source, target, width, occupiedBoxes, blockedBoxes, blockedSegments);

    const group = document.createElementNS(SVG_NS, "g");
    group.classList.add("edge-label");
    if (variant) group.classList.add(variant);
    group.setAttribute("transform", `translate(${position.x} ${position.y})`);

    const background = document.createElementNS(SVG_NS, "rect");
    background.setAttribute("x", String(-width / 2));
    background.setAttribute("y", "-12");
    background.setAttribute("width", String(width));
    background.setAttribute("height", "24");
    background.setAttribute("rx", "12");

    const text = document.createElementNS(SVG_NS, "text");
    text.setAttribute("y", "1");
    text.textContent = edge.relation;
    group.append(background, text);
    els.edgeLabelsLayer.append(group);
    occupiedBoxes.push(position.box);
  };

  // 在完整图谱中绘制默认隐藏的悬浮关系标签。
  const appendHoverEdgeLabel = (edge, source, target, index) => {
    if (!edge.relation) return null;
    const width = Math.max(34, edge.relation.length * 13 + 18);
    const { x, y } = fullGraphLabelPoint(source, target);
    const group = document.createElementNS(SVG_NS, "g");
    group.classList.add("edge-label", "edge-label--hover");
    group.dataset.edge = String(index);
    group.setAttribute("transform", `translate(${x} ${y})`);

    const background = document.createElementNS(SVG_NS, "rect");
    background.setAttribute("x", String(-width / 2));
    background.setAttribute("y", "-12");
    background.setAttribute("width", String(width));
    background.setAttribute("height", "24");
    background.setAttribute("rx", "12");

    const text = document.createElementNS(SVG_NS, "text");
    text.setAttribute("y", "1");
    text.textContent = edge.relation;
    group.append(background, text);
    els.edgeLabelsLayer.append(group);
    return group;
  };

  // 绘制完整图谱的所有边、命中区域和悬浮标签。
  const renderFullGraphEdges = () => {
    els.edgesLayer.replaceChildren();
    els.edgeLabelsLayer.replaceChildren();
    edges.forEach((edge, index) => {
      const source = nodeById.get(edge.from);
      const target = nodeById.get(edge.to);
      const path = document.createElementNS(SVG_NS, "path");
      const d = fullGraphPath(source, target);
      path.setAttribute("d", d);
      path.classList.add("edge", "edge--full");
      path.dataset.edge = String(index);
      els.edgesLayer.append(path);

      const label = appendHoverEdgeLabel(edge, source, target, index);
      const hitPath = document.createElementNS(SVG_NS, "path");
      hitPath.setAttribute("d", d);
      hitPath.classList.add("edge-hit");
      hitPath.dataset.edge = String(index);
      hitPath.addEventListener("pointerenter", () => {
        path.classList.add("is-hovered");
        label?.classList.add("is-visible");
      });
      hitPath.addEventListener("pointerleave", () => {
        path.classList.remove("is-hovered");
        label?.classList.remove("is-visible");
      });
      els.edgesLayer.append(hitPath);
    });
  };

  // 获取指定层级栏位允许拖拽的边界。
  const layerBounds = layer => {
    const layerInset = Number.parseFloat(
      window.getComputedStyle(els.graphCard).getPropertyValue("--graph-layer-inset")
    ) || GRAPH_LAYER_INSET;
    const columnCount = Math.max(layerNames.length, 1);
    const columnWidth = (graphWidth - layerInset * 2) / columnCount;
    const columnLeft = layerInset + columnWidth * layer;
    const columnRight = columnLeft + columnWidth;
    return {
      minX: columnLeft + 18,
      maxX: columnRight - 18,
      minY: 62,
      maxY: Math.max(62, graphHeight - 72)
    };
  };

  // 将指针事件坐标转换为 SVG 内部坐标。
  const svgPointFromEvent = event => {
    const point = els.svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const ctm = els.svg.getScreenCTM();
    if (!ctm) return null;
    return point.matrixTransform(ctm.inverse());
  };

  // 拖动节点时更新节点坐标并重绘完整图谱边。
  const moveDraggedNode = event => {
    if (!dragState) return;
    const point = svgPointFromEvent(event);
    if (!point) return;
    const dx = point.x - dragState.startPointer.x;
    const dy = point.y - dragState.startPointer.y;
    if (Math.hypot(dx, dy) > 3) dragState.moved = true;

    const bounds = layerBounds(dragState.node.layer);
    dragState.node.x = clamp(dragState.startNode.x + dx, bounds.minX, bounds.maxX);
    dragState.node.y = clamp(dragState.startNode.y + dy, bounds.minY, bounds.maxY);
    dragState.group.setAttribute("transform", `translate(${dragState.node.x} ${dragState.node.y})`);
    renderFullGraphEdges();
    event.preventDefault();
  };

  // 结束节点拖拽并处理拖拽后的点击抑制。
  const endDraggedNode = event => {
    if (!dragState) return;
    if (dragState.moved) {
      suppressNodeClick = true;
      window.setTimeout(() => { suppressNodeClick = false; }, 250);
    }
    dragState.group.releasePointerCapture?.(event.pointerId);
    dragState.group.classList.remove("is-dragging");
    dragState = null;
  };

  // 在完整图谱中启动节点拖拽。
  const startNodeDrag = (event, node, group) => {
    if (state.selectedId || event.button !== 0) return;
    const point = svgPointFromEvent(event);
    if (!point) return;
    dragState = {
      node,
      group,
      pointerId: event.pointerId,
      startPointer: point,
      startNode: { x: node.x, y: node.y },
      moved: false
    };
    group.setPointerCapture?.(event.pointerId);
    group.classList.add("is-dragging");
    els.tooltip.hidden = true;
    event.preventDefault();
  };

  // 将当前完整图谱节点位置打印到控制台。
  const printNodePositions = () => {
    const positions = nodes.map(node => ({
      id: node.id,
      layer: node.layer,
      x: Number(node.x.toFixed(1)),
      y: Number(node.y.toFixed(1))
    }));
    console.table(positions);
    console.log(JSON.stringify(positions, null, 2));
  };

  // 将一组节点沿指定竖栏均匀分布。
  const distributeColumn = (ids, x) => {
    const top = Math.min(128, Math.max(86, graphHeight * .22));
    const bottom = Math.max(top, graphHeight - top);
    const ordered = ids
      .map(id => nodeById.get(id))
      .filter(Boolean)
      .sort((a, b) => a.order - b.order);
    return ordered.map((node, index) => {
      const y = ordered.length === 1 ? graphHeight / 2 : top + ((bottom - top) / (ordered.length - 1)) * index;
      return { id: node.id, x, y };
    });
  };

  // 计算聚焦视图中的前置、当前和后继节点位置。
  const focusedPositions = id => {
    const parentIds = incoming(id);
    const childIds = outgoing(id);
    const laneCenters = [graphWidth / 6, graphWidth / 2, graphWidth * 5 / 6];
    return [
      ...distributeColumn(parentIds, laneCenters[0]),
      ...distributeColumn([id], laneCenters[1]),
      ...distributeColumn(childIds, laneCenters[2])
    ].reduce((map, position) => map.set(position.id, position), new Map());
  };

  // 绘制聚焦视图三条栏位的标题。
  const appendLaneLabels = () => {
    [
      { label: "前置", x: graphWidth / 6 },
      { label: "当前", x: graphWidth / 2 },
      { label: "后续", x: graphWidth * 5 / 6 }
    ].forEach(item => {
      const text = document.createElementNS(SVG_NS, "text");
      text.classList.add("focus-lane-label");
      text.setAttribute("x", item.x);
      text.setAttribute("y", "54");
      text.textContent = item.label;
      els.nodesLayer.append(text);
    });
  };

  // 绘制一个知识节点并绑定交互事件。
  const appendNode = (node, position, selected, before, after, peer, focused = false) => {
    const group = document.createElementNS(SVG_NS, "g");
    group.classList.add("node");
    group.dataset.id = node.id;
    group.dataset.status = statusFor(node);
    group.setAttribute("transform", `translate(${position.x} ${position.y})`);
    group.setAttribute("role", "button");
    group.setAttribute("tabindex", "0");
    group.setAttribute("aria-label", `${node.title}，${node.brief}`);
    if (selected) {
      if (node.id === selected) group.classList.add("is-selected");
      else if (before.has(node.id) || after.has(node.id)) group.classList.add("is-related");
      else if (peer.has(node.id)) group.classList.add("is-peer");
    }

    const halo = document.createElementNS(SVG_NS, "circle");
    halo.setAttribute("r", focused ? "24" : "16");
    halo.classList.add("node-halo");
    const ring = document.createElementNS(SVG_NS, "circle");
    ring.setAttribute("r", focused ? "18" : "13");
    ring.classList.add("node-ring");
    const dot = document.createElementNS(SVG_NS, "circle");
    dot.setAttribute("r", focused ? (node.id === selected ? "14" : "10") : "6.5");
    dot.classList.add("node-dot");
    const label = document.createElementNS(SVG_NS, "text");
    label.setAttribute("y", focused ? "38" : "29");
    label.classList.add("node-label");
    label.textContent = node.title;
    group.append(halo, ring, dot, label);
    group.addEventListener("pointerenter", event => showTooltip(event, node));
    group.addEventListener("pointermove", event => moveTooltip(event));
    group.addEventListener("pointerleave", hideTooltip);
    group.addEventListener("click", event => {
      event.stopPropagation();
      if (suppressNodeClick) {
        suppressNodeClick = false;
        event.preventDefault();
        return;
      }
      els.tooltip.hidden = true;
      selectNode(node.id);
    });
    group.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        els.tooltip.hidden = true;
        selectNode(node.id);
      }
    });
    els.nodesLayer.append(group);
  };

  // 根据当前状态渲染完整图谱或聚焦关系视图。
  const renderGraph = ({ preserveGeometry = false } = {}) => {
    normalizeLearningState();
    const selected = state.selectedId;
    const before = new Set(selected ? incoming(selected) : []);
    const after = new Set(selected ? outgoing(selected) : []);
    const peer = new Set(selected ? peers(selected) : []);
    const focused = Boolean(selected);

    els.graphCard.classList.toggle("is-focused", focused);
    syncGraphDisplayOptions();
    syncGraphToolbarActions(focused);
    els.viewLabel.textContent = focused ? "聚焦关系视图" : "完整知识图谱";
    if (!preserveGeometry) syncGraphGeometry(focused);
    syncLayerBands(focused ? 3 : layerNames.length);
    els.edgesLayer.replaceChildren();
    els.edgeLabelsLayer.replaceChildren();
    els.nodesLayer.replaceChildren();

    if (focused) {
      const positions = focusedPositions(selected);
      const occupiedLabelBoxes = [];
      const blockedBoxes = nodeCollisionBoxes(positions, true);
      appendLaneLabels();
      const focusedEdges = edges
        .map((edge, index) => {
          if (!positions.has(edge.from) || !positions.has(edge.to)) return null;
          if (edge.from !== selected && edge.to !== selected) return null;
          const source = positions.get(edge.from);
          const target = positions.get(edge.to);
          const variant = edge.to === selected ? "is-before" : "is-after";
          return { edge, index, source, target, variant };
        })
        .filter(Boolean);

      focusedEdges.forEach(({ edge, index, source, target, variant }) => {
        const path = document.createElementNS(SVG_NS, "path");
        path.setAttribute("d", curvePath(source, target));
        path.classList.add("edge", variant);
        path.dataset.edge = String(index);
        els.edgesLayer.append(path);
      });

      focusedEdges.forEach(({ edge, index, source, target, variant }) => {
        const blockedSegments = focusedEdges
          .filter(item => item.index !== index)
          .map(item => ({ source: item.source, target: item.target }));
        appendEdgeLabel(edge, source, target, variant, occupiedLabelBoxes, blockedBoxes, blockedSegments);
      });

      positions.forEach((position, id) => {
        appendNode(nodeById.get(id), position, selected, before, after, peer, true);
      });
      els.viewportGroup.setAttribute("transform", "translate(0 0)");
      return;
    }

    renderFullGraphEdges();

    nodes.forEach(node => appendNode(node, node, selected, before, after, peer));
    updateTransform();
  };

  // 同步右侧聚焦关系卡片内容。
  const syncNodeInspector = id => {
    const node = nodeById.get(id);
    if (!node) {
      els.inspector.hidden = true;
      return null;
    }

    const before = incoming(id);
    const after = outgoing(id);
    document.querySelector("#inspectorNumber").textContent = String(node.order + 1).padStart(2, "0");
    document.querySelector("#inspectorTag").textContent = layerNames[node.layer];
    document.querySelector("#inspectorName").textContent = node.title;
    document.querySelector("#inspectorBrief").textContent = node.brief;
    document.querySelector("#beforeCount").textContent = before.length;
    document.querySelector("#afterCount").textContent = after.length;
    const learnHere = document.querySelector("#learnHere");
    learnHere.setAttribute("aria-disabled", "false");
    learnHere.disabled = false;
    els.inspector.hidden = false;
    return node;
  };

  // 选择节点并打开右侧聚焦关系卡片。
  const selectNode = id => {
    els.tooltip.hidden = true;
    const node = syncNodeInspector(id);
    if (!node) return;
    state.selectedId = id;
    renderGraph();
  };

  // 清除节点选择并返回完整知识图谱。
  const clearSelection = () => {
    if (!state.selectedId && els.inspector.hidden) return;
    state.selectedId = null;
    els.inspector.hidden = true;
    renderGraph();
  };

  // 将“标记为已掌握”按钮恢复为默认状态。
  const resetCompleteButton = (disabled = true) => {
    const button = document.querySelector("#completeLesson");
    if (!button) return;
    button.disabled = disabled;
    button.innerHTML = "标记为已掌握 <span aria-hidden=\"true\">✓</span>";
  };

  // 查找完成当前节点后下一个可学习节点。
  const findNextLearnableNode = finishedId => {
    const finished = nodeById.get(finishedId);
    const nextByOrder = nodes
      .slice(finished ? finished.order + 1 : 0)
      .find(isLearnable);
    return nextByOrder || nodes.find(isLearnable) || null;
  };

  // 平滑滚动到指定区块顶部。
  const scrollToSectionTop = element => {
    if (!element) return;
    window.requestAnimationFrame(() => {
      const top = element.getBoundingClientRect().top + window.scrollY;
      pageWheelLockedUntil = window.performance.now() + PAGE_WHEEL_LOCK_MS;
      window.scrollTo({ top, behavior: "smooth" });
    });
  };

  // 等待两个动画帧以便 DOM 布局稳定。
  const waitForNextFrame = () => new Promise(resolve => {
    window.requestAnimationFrame(() => window.requestAnimationFrame(resolve));
  });

  const withTimeout = (promise, timeoutMs, message) => new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => reject(new Error(message)), timeoutMs);
    Promise.resolve(promise)
      .then(resolve, reject)
      .finally(() => window.clearTimeout(timer));
  });

  // 获取页面区块相对文档顶部的位置。
  const getSectionTop = element => {
    if (!element) return 0;
    return element.getBoundingClientRect().top + window.scrollY;
  };

  // 判断滚轮事件是否发生在可编辑控件内。
  const isEditableWheelTarget = target => {
    if (!(target instanceof Element)) return false;
    return Boolean(target.closest("input, textarea, select, [contenteditable='true']"));
  };

  // 平滑滚动回页面顶部。
  const scrollToPageTop = () => {
    pageWheelLockedUntil = window.performance.now() + PAGE_WHEEL_LOCK_MS;
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // 处理整页滚轮分页跳转逻辑。
  const handlePageWheel = event => {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (isEditableWheelTarget(event.target)) return;
    if (Math.abs(event.deltaY) < PAGE_WHEEL_DELTA_THRESHOLD) return;
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;

    const now = window.performance.now();
    if (now < pageWheelLockedUntil) {
      event.preventDefault();
      return;
    }

    const scrollY = window.scrollY || document.documentElement.scrollTop || 0;
    const tolerance = 18;
    const mapElement = els.mapSection || els.graphCard;
    const mapTop = getSectionTop(mapElement);
    const lessonTop = getSectionTop(els.lessonSection);

    if (event.deltaY > 0) {
      if (scrollY < mapTop - tolerance) {
        event.preventDefault();
        scrollToSectionTop(mapElement);
        return;
      }

      if (scrollY < lessonTop - tolerance) {
        event.preventDefault();
        scrollToSectionTop(els.lessonSection);
      }
      return;
    }

    if (scrollY <= tolerance) return;

    if (scrollY <= lessonTop + tolerance && scrollY > mapTop + tolerance) {
      event.preventDefault();
      scrollToSectionTop(mapElement);
      return;
    }

    if (scrollY <= mapTop + tolerance) {
      event.preventDefault();
      scrollToPageTop();
    }
  };

  // 应用浅色或暗色主题到页面。
  const setTheme = theme => {
    const isDark = theme === "dark";
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    els.themeToggle?.setAttribute("aria-pressed", String(isDark));
    els.themeToggle?.setAttribute("aria-label", isDark ? "切换浅色模式" : "切换暗色模式");
    els.themeToggle?.querySelector(".theme-toggle__text")?.replaceChildren(isDark ? "浅色" : "暗色");
  };

  // 获取初始主题偏好。
  const getInitialTheme = () => {
    try {
      const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
      if (savedTheme === "dark" || savedTheme === "light") return savedTheme;
    } catch (error) {
      console.warn("Unable to read theme preference.", error);
    }
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  };

  // 切换主题并保存用户偏好。
  const toggleTheme = () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch (error) {
      console.warn("Unable to save theme preference.", error);
    }
  };

  // 从指定节点开始或查看学习内容。
  const beginLearning = async id => {
    if (nextLessonTimer !== null) {
      window.clearTimeout(nextLessonTimer);
      nextLessonTimer = null;
    }

    const node = nodeById.get(id);
    if (!node) return;
    const currentStatus = statusFor(node);
    const canStartLearning = currentStatus !== "locked" && currentStatus !== "mastered";
    resetCompleteButton(true);
    state.selectedId = id;
    if (canStartLearning) {
      setSingleLearningNode(id);
      saveLearningState();
    }
    syncNodeInspector(id);
    renderGraph();
    scrollToSectionTop(els.lessonSection);
    await renderLesson(node);
  };

  // 加载并渲染指定节点对应的 Markdown 文档。
  const renderLesson = async node => {
    const renderSequence = ++lessonRenderSequence;
    const button = document.querySelector("#completeLesson");
    if (button) button.disabled = true;
    els.lessonSection.setAttribute("aria-busy", "true");
    try {
      const markdown = await readText(assetPath(node.documentPath));
      if (renderSequence !== lessonRenderSequence) return;

      state.lessonId = node.id;
      const masteredCount = nodes.filter(item => item.status === "mastered").length;
      const completion = Math.max(2, Math.round((masteredCount / Math.max(nodes.length, 1)) * 100));
      els.lessonSection.classList.remove("is-empty");
      els.lessonSection.setAttribute("aria-labelledby", "lessonBreadcrumb");
      els.lessonPlaceholder?.remove();
      els.lessonDocument.hidden = false;
      document.querySelector("#lessonLayer").textContent = layerNames[node.layer];
      document.querySelector("#lessonBreadcrumb").textContent = node.title;
      document.querySelector("#lessonPosition").textContent = `第 ${node.order + 1} / ${nodes.length} 节`;
      document.querySelector("#lessonProgressValue").textContent = `${completion}%`;
      document.querySelector("#progressRing").style.setProperty("--progress", completion);
      const rendered = await updateLessonMarkdown(renderMarkdown(markdown), renderSequence);
      if (!rendered || renderSequence !== lessonRenderSequence) return;

      if (button) button.disabled = state.lessonId !== state.learningId || statusFor(node) !== "learning";
    } catch (error) {
      if (renderSequence === lessonRenderSequence) console.error(`文档“${node.title}”加载失败：`, error);
    } finally {
      if (renderSequence === lessonRenderSequence) els.lessonSection.removeAttribute("aria-busy");
    }
  };

  // 将当前正在学习的节点标记为已掌握并推进学习流程。
  const completeLesson = () => {
    if (els.lessonSection.getAttribute("aria-busy") === "true") return;
    if (!state.learningId) return;
    const finished = nodeById.get(state.learningId);
    if (!finished) return;
    if (state.lessonId !== finished.id || statusFor(finished) !== "learning") return;
    clearLearningStatuses();
    finished.status = "mastered";
    state.learningId = null;
    saveLearningState();
    const next = findNextLearnableNode(finished.id);
    const button = document.querySelector("#completeLesson");
    button.innerHTML = "已掌握，做得好 <span aria-hidden=\"true\">✓</span>";
    button.disabled = true;
    renderGraph();
    scrollToSectionTop(els.lessonSection);
    if (next) {
      nextLessonTimer = window.setTimeout(() => {
        nextLessonTimer = null;
        void beginLearning(next.id);
      }, 900);
    }
  };

  // 重置学习进度并刷新图谱状态。
  const resetLearningState = () => {
    if (nextLessonTimer !== null) {
      window.clearTimeout(nextLessonTimer);
      nextLessonTimer = null;
    }
    try {
      window.localStorage.removeItem(LEARNING_STORAGE_KEY);
    } catch (error) {
      console.warn("Unable to reset learning state.", error);
    }
    nodes.forEach(node => { node.status = null; });
    setSingleLearningNode(nodes[0]?.id || null);
    state.lessonId = null;
    saveLearningState();
    const button = document.querySelector("#completeLesson");
    if (button) {
      resetCompleteButton();
      button.disabled = true;
    }
    document.querySelector("#lessonProgressValue").textContent = "0%";
    document.querySelector("#progressRing").style.setProperty("--progress", 0);
    renderGraph({ preserveGeometry: true });
  };

  // 显示节点悬浮提示。
  const showTooltip = (event, node) => {
    const statusText = { mastered: "已掌握", learning: "正在学习", ready: "未学习", locked: "缺少前置知识" };
    els.tooltip.innerHTML = `
      <div class="tooltip__tag">${layerNames[node.layer]} · ${statusText[statusFor(node)] || statusFor(node)}</div>
      <strong>${escapeHtml(node.title)}</strong>
      <p>${escapeHtml(node.brief)}</p>
    `;
    els.tooltip.hidden = false;
    moveTooltip(event);
  };

  // 根据鼠标位置移动并约束悬浮提示。
  const moveTooltip = event => {
    const bounds = els.graphViewport.getBoundingClientRect();
    const pointerX = event.clientX - bounds.left;
    const pointerY = event.clientY - bounds.top;
    const gap = 16;
    const margin = 8;
    const width = els.tooltip.offsetWidth || 260;
    const height = els.tooltip.offsetHeight || 90;
    const maxX = Math.max(margin, bounds.width - width - margin);
    const maxY = Math.max(margin, bounds.height - height - margin);
    // 将提示框位置限制在图谱视口内。
    const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
    const candidates = [
      { x: pointerX - width - gap, y: pointerY - height / 2, fits: pointerX - width - gap >= margin },
      { x: pointerX - width / 2, y: pointerY + gap, fits: pointerY + gap + height <= bounds.height - margin },
      { x: pointerX - width / 2, y: pointerY - height - gap, fits: pointerY - height - gap >= margin },
      { x: pointerX + gap, y: pointerY - height / 2, fits: pointerX + gap + width <= bounds.width - margin },
    ];
    const position = candidates.find(candidate => candidate.fits) || candidates[0];
    const x = clamp(position.x, margin, maxX);
    const y = clamp(position.y, margin, maxY);
    els.tooltip.style.left = `${x}px`;
    els.tooltip.style.top = `${y}px`;
  };

  // 隐藏节点悬浮提示。
  const hideTooltip = () => { els.tooltip.hidden = true; };

  // 重置图谱视口变换。
  const updateTransform = () => {
    els.viewportGroup.setAttribute("transform", "translate(0 0)");
  };

  // 在窗口尺寸变化后延迟到下一帧重绘图谱。
  const scheduleGraphRender = () => {
    if (!nodes.length) return;
    window.cancelAnimationFrame(graphResizeFrame);
    graphResizeFrame = window.requestAnimationFrame(renderGraph);
  };

  // 绑定页面、图谱、学习和主题相关事件。
  const bindEvents = () => {
    els.svg.addEventListener("click", event => {
      if (event.target === els.svg) clearSelection();
    });

    els.returnGraph.addEventListener("click", clearSelection);
    els.continueLearning?.addEventListener("click", () => {
      const learningNode = getLearningNode();
      if (learningNode) void beginLearning(learningNode.id);
    });
    document.querySelector("#learnHere").addEventListener("click", () => { void beginLearning(state.selectedId); });
    document.querySelector("#completeLesson").addEventListener("click", completeLesson);
    document.querySelector("#startMap")?.addEventListener("click", () => {
      scrollToSectionTop(els.mapSection || els.graphCard);
    });
    document.querySelector("#backToMap")?.addEventListener("click", () => {
      scrollToSectionTop(els.mapSection || els.graphCard);
    });
    els.resetLearningState?.addEventListener("click", resetLearningState);
    els.printNodePositions?.addEventListener("click", printNodePositions);
    els.toggleEdgeLabels?.addEventListener("click", () => {
      state.showAllEdgeLabels = !state.showAllEdgeLabels;
      syncGraphDisplayOptions();
    });
    els.toggleEdgeArrows?.addEventListener("click", () => {
      state.showAllEdgeArrows = !state.showAllEdgeArrows;
      syncGraphDisplayOptions();
    });
    els.toggleNodeNames?.addEventListener("click", () => {
      state.showNodeNames = !state.showNodeNames;
      syncGraphDisplayOptions();
    });
    els.lessonDocument?.addEventListener("click", event => {
      const button = event.target instanceof Element
        ? event.target.closest(".gif-player__button")
        : null;
      if (button) playGif(button);
    });
    els.themeToggle?.addEventListener("click", toggleTheme);
    window.addEventListener("resize", scheduleGraphRender);
    window.addEventListener("wheel", handlePageWheel, { passive: false });
  };

  // 显示数据加载失败状态并输出错误。
  const showLoadError = error => {
    els.viewLabel.textContent = "数据加载失败";
    els.nodesLayer.replaceChildren();
    els.edgesLayer.replaceChildren();
    els.graphCard.classList.remove("is-focused");
    console.error(error);
  };

  // 初始化主题、数据、事件和首屏图谱。
  const init = async () => {
    try {
      setTheme(getInitialTheme());
      const [topicData, dependencyData, positionData] = await Promise.all([
        readJson(`${DATA_ROOT}/topics.json`),
        readJson(`${DATA_ROOT}/dependencies.json`),
        readJson(`${DATA_ROOT}/position.json`)
      ]);
      buildGraphData(topicData, dependencyData, positionData);
      syncLayerDisplay();
      document.querySelector("#topicCount").textContent = nodes.length;
      document.querySelector("#edgeCount").textContent = edges.length;
      bindEvents();
      renderGraph();
    } catch (error) {
      showLoadError(error);
    }
  };

  void init();
})();
