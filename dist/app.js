let timeline = [];

const timelineElement = document.querySelector("#timeline");
const renderTimeline = () => {
  timelineElement.replaceChildren(...timeline.map((event) => {
    const item = document.createElement("li");
    const time = document.createElement("time");
    const title = document.createElement("h3");
    const detail = document.createElement("p");
    time.textContent = event.time;
    title.textContent = event.title;
    detail.textContent = event.detail;
    item.append(time, title, detail);
    return item;
  }));
};

const loadFixtureProjection = async () => {
  try {
    const response = await fetch("./data/root-task-observer.json");
    if (!response.ok) throw new Error("fixture unavailable");
    const projection = await response.json();
    timeline = projection.timeline.map((event, index) => ({
      time: `evidence ${index + 1}`,
      title: event.title,
      detail: event.detail
    }));
    document.querySelector(".task-meta code").textContent = projection.rootThread;
    document.querySelector(".runtime-pill").firstChild.textContent = `${projection.runtime} `;
  } catch {
    timeline = [{ time: "gap", title: "Fixture projection unavailable", detail: "The observer cannot infer source activity while its sanitized projection is unavailable." }];
  }
  renderTimeline();
};

loadFixtureProjection();

document.querySelector("#follow-up-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = document.querySelector("#follow-up");
  const text = input.value.trim();
  if (!text) return;
  timeline.push({ time: "preview", title: "Follow-up staged locally", detail: "Preview only: no Codex turn was started. The entered instruction remains in this browser session." });
  input.value = "";
  renderTimeline();
});

document.querySelector("#interrupt").addEventListener("click", () => {
  document.querySelector("#provenance-result").textContent = "Preview only: production interrupt sends a supported action and waits for correlated source evidence.";
});

document.querySelector("#finish").addEventListener("click", () => {
  document.querySelector("#provenance-result").textContent = "Preview only: Finish is an Orbita lifecycle action and never rewrites the source outcome.";
});

document.querySelector("#show-provenance").addEventListener("click", () => {
  document.querySelector("#provenance-result").textContent = "Source: sanitized M0 root-turn and live-controls fixtures pinned to codex-cli 0.170.0.";
});
