const CAT_LABEL = { news: "新闻", papers: "论文", opensource: "开源", community: "社区" };
let DATA = { items: [] };
let activeCat = "all";

function fmtTime(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit" });
}

function matchesCat(item, cat) {
  if (cat === "all") return true;
  if (cat === "policy") return item.is_policy === true;
  return item.category === cat;
}

function render() {
  const search = document.getElementById("search").value.trim().toLowerCase();
  const src = document.getElementById("source-filter").value;
  const list = document.getElementById("list");
  const items = DATA.items.filter(it =>
    matchesCat(it, activeCat) &&
    (!src || it.source === src) &&
    (!search || it.title.toLowerCase().includes(search))
  );
  if (items.length === 0) {
    list.innerHTML = '<p style="color:var(--muted)">暂无内容。</p>';
  } else {
    list.innerHTML = items.map(it => `
      <div class="card">
        <a href="${escapeHtml(it.url)}" target="_blank" rel="noopener">${escapeHtml(it.title)}</a>
        <div class="meta">
          <span class="badge">${CAT_LABEL[it.category] || it.category}</span>
          <span>${escapeHtml(it.source)}</span>
          <span>${fmtTime(it.published)}</span>
          ${it.is_policy ? '<span class="badge">政策</span>' : ''}
        </div>
      </div>`).join("");
  }
  document.getElementById("count").textContent = `共 ${items.length} 条`;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function initSources() {
  const sel = document.getElementById("source-filter");
  const names = [...new Set(DATA.items.map(i => i.source))].sort();
  for (const n of names) {
    const o = document.createElement("option");
    o.value = n; o.textContent = n; sel.appendChild(o);
  }
}

function bind() {
  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeCat = btn.dataset.cat;
      render();
    });
  });
  document.getElementById("search").addEventListener("input", render);
  document.getElementById("source-filter").addEventListener("change", render);
}

async function main() {
  try {
    const res = await fetch("data.json?t=" + Date.now());
    DATA = await res.json();
  } catch (e) {
    document.getElementById("list").innerHTML =
      '<p style="color:var(--muted)">加载 data.json 失败。</p>';
    return;
  }
  document.getElementById("updated").textContent = fmtTime(DATA.generated_at);
  initSources();
  bind();
  render();
}

main();
