"use strict";

const state = { records: [], filtered: [] };
const search = document.querySelector("#search");
const family = document.querySelector("#family");
const sort = document.querySelector("#sort");
const cards = document.querySelector("#cards");
const status = document.querySelector("#status");
const visibleCount = document.querySelector("#visible-count");
const details = document.querySelector("#details");

const labels = {
  category: "来源分类 / Source category",
  department: "部门 / Department",
  location: "地点 / Location",
  posted_at: "发布日期 / Posted",
  deadline: "申请截止 / Deadline",
  positions: "岗位数量 / Positions",
  duration: "合同期限 / Duration",
  start_date: "入职时间 / Start date",
  work_mode: "工作方式 / Work mode",
  extension: "可续约 / Extension",
  salary: "薪酬 / Compensation",
  reference: "参考编号 / Reference",
  observed_at: "最近观察 / Last observed",
  review_status: "审核状态 / Review status",
};

function shown(value) {
  return value === null || value === undefined || value === "" ? "未报告 / Not reported" : String(value);
}

function familyName(value) {
  const names = {
    postdoc: "博士后 / Postdoc",
    doctoral: "博士生 / Doctoral",
    faculty: "教职 / Faculty",
    internship: "实习 / Internship",
    research_scientist: "科研人员 / Research scientist",
    research_software: "科研软件 / Research software",
    technical_staff: "技术人员 / Technical staff",
    research_support: "科研支持 / Research support",
  };
  return names[value] || shown(value);
}

function salary(record) {
  if (record.salary_min !== null && record.salary_min !== undefined) {
    const range = record.salary_max !== record.salary_min ? ` – ${record.salary_max}` : "";
    return `${record.salary_currency} ${record.salary_min}${range} / ${record.salary_period}`;
  }
  return shown(record.salary_text);
}

function safeLink(url) {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" ? parsed.href : null;
  } catch (_) {
    return null;
  }
}

function field(label, value) {
  const wrapper = document.createElement("div");
  const term = document.createElement("dt");
  const description = document.createElement("dd");
  term.textContent = label;
  description.textContent = shown(value);
  wrapper.append(term, description);
  return wrapper;
}

function detail(record) {
  document.querySelector("#detail-family").textContent = familyName(record.job_family);
  document.querySelector("#detail-title").textContent = shown(record.title);
  document.querySelector("#detail-institution").textContent = shown(record.institution);
  const list = document.querySelector("#detail-fields");
  list.replaceChildren(
    field(labels.category, record.category),
    field(labels.department, record.department),
    field(labels.location, record.location),
    field(labels.posted_at, record.posted_at),
    field(labels.deadline, record.deadline),
    field(labels.positions, record.positions),
    field(labels.duration, record.duration_months === null ? record.duration_text : `${record.duration_months} months`),
    field(labels.start_date, record.start_date || record.start_date_text),
    field(labels.work_mode, record.work_mode || record.work_mode_text),
    field(labels.extension, record.extension_possible === null ? record.extension_text : record.extension_possible),
    field(labels.salary, salary(record)),
    field(labels.reference, record.reference_code),
    field(labels.observed_at, record.observed_at),
    field(labels.review_status, record.review_status),
  );
  const links = document.querySelector("#detail-links");
  links.replaceChildren();
  for (const [label, url] of [
    ["聚合站条目 / Source listing", safeLink(record.canonical_url)],
    ["官方公告 / Official announcement", safeLink(record.official_announcement_url)],
  ]) {
    if (!url) continue;
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.target = "_blank";
    anchor.rel = "noopener noreferrer";
    anchor.textContent = label;
    links.append(anchor);
  }
  details.showModal();
}

function card(record) {
  const article = document.createElement("article");
  article.tabIndex = 0;
  const tag = document.createElement("p");
  tag.className = "tag";
  tag.textContent = familyName(record.job_family);
  const title = document.createElement("h2");
  title.textContent = shown(record.title);
  const institution = document.createElement("p");
  institution.className = "institution";
  institution.textContent = shown(record.institution);
  const meta = document.createElement("div");
  meta.className = "meta";
  for (const value of [record.location, record.deadline ? `截止 ${record.deadline}` : null]) {
    if (!value) continue;
    const item = document.createElement("span");
    item.textContent = value;
    meta.append(item);
  }
  article.append(tag, title, institution, meta);
  article.addEventListener("click", () => detail(record));
  article.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") detail(record);
  });
  return article;
}

function applyFilters() {
  const needle = search.value.trim().toLocaleLowerCase();
  const selectedFamily = family.value;
  state.filtered = state.records.filter((record) => {
    const haystack = [record.title, record.institution, record.department, record.location, record.category]
      .filter(Boolean).join(" ").toLocaleLowerCase();
    return (!needle || haystack.includes(needle)) && (!selectedFamily || record.job_family === selectedFamily);
  });
  state.filtered.sort((a, b) => {
    if (sort.value === "institution") return shown(a.institution).localeCompare(shown(b.institution));
    if (sort.value === "observed") return shown(b.observed_at).localeCompare(shown(a.observed_at));
    const today = new Date().toISOString().slice(0, 10);
    const deadlineKey = (record) => {
      if (!record.deadline) return `2-${record.title}`;
      const group = record.deadline.slice(0, 10) < today ? "1" : "0";
      return `${group}-${record.deadline}`;
    };
    return deadlineKey(a).localeCompare(deadlineKey(b));
  });
  cards.replaceChildren(...state.filtered.map(card));
  visibleCount.textContent = state.filtered.length;
  status.textContent = state.filtered.length ? "" : "没有匹配条目 / No matching records";
}

async function start() {
  try {
    const response = await fetch("/api/postings", { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.records = await response.json();
    const families = [...new Set(state.records.map((record) => record.job_family).filter(Boolean))].sort();
    for (const value of families) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = familyName(value);
      family.append(option);
    }
    applyFilters();
  } catch (error) {
    status.textContent = `无法读取数据库 / Could not load database: ${error.message}`;
  }
}

for (const control of [search, family, sort]) control.addEventListener("input", applyFilters);
document.querySelector("#close").addEventListener("click", () => details.close());
details.addEventListener("click", (event) => {
  if (event.target === details) details.close();
});
start();
