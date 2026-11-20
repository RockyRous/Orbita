let timeline = [];
let preview = { events: [], lifecycle: "Open" };

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

const renderProjection = (projection) => {
  timeline = projection.timeline.map((event, index) => ({
    time: `evidence ${index + 1}`,
    title: event.title,
    detail: event.detail
  }));
  timeline.push(...preview.events.map((event) => ({ time: "preview", title: event.title, detail: event.detail })));
  document.querySelector(".task-meta code").textContent = projection.rootThread;
  document.querySelector(".runtime-pill").firstChild.textContent = `${projection.runtime} `;
  document.querySelector("#finish").textContent = preview.lifecycle === "Finished" ? "Task finished" : "Finish task";
  renderTimeline();
};

const loadFixtureProjection = async () => {
  try {
    const response = await fetch("/api/projection");
    if (!response.ok) throw new Error("fixture unavailable");
    const responseBody = await response.json();
    preview = responseBody.preview;
    renderProjection(responseBody.projection);
  } catch {
    timeline = [{ time: "gap", title: "Fixture projection unavailable", detail: "The observer cannot infer source activity while its sanitized projection is unavailable." }];
    preview = { events: [], lifecycle: "Open" };
    renderTimeline();
  }
};

loadFixtureProjection();

const previewAction = async (action) => {
  const response = await fetch(`/api/preview/${action}`, { method: "POST" });
  if (!response.ok) throw new Error("preview action unavailable");
  const body = await response.json();
  preview = body.preview;
  renderProjection(body.projection);
};

document.querySelector("#follow-up-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#follow-up");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  await previewAction("follow-up");
});

document.querySelector("#interrupt").addEventListener("click", async () => {
  await previewAction("interrupt");
  document.querySelector("#provenance-result").textContent = "Preview only: no App Server interrupt was sent.";
});

document.querySelector("#finish").addEventListener("click", async () => {
  await previewAction("finish");
  document.querySelector("#provenance-result").textContent = "Preview only: Finish is an Orbita lifecycle action and never rewrites the source outcome.";
});

document.querySelector("#show-provenance").addEventListener("click", () => {
  document.querySelector("#provenance-result").textContent = "Source: sanitized M0 root-turn and live-controls fixtures pinned to codex-cli 0.170.0.";
});
