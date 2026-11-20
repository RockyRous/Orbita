const timeline = [
  { time: "10:12:04", title: "Root task started", detail: "thread/start created <THREAD_1> in the pinned public App Server contract." },
  { time: "10:12:05", title: "Turn accepted", detail: "turn/start returned a correlated source turn and the observer began collecting evidence." },
  { time: "10:12:11", title: "Source outcome observed", detail: "turn/completed reported a completed root turn. No completion was inferred from silence." },
  { time: "10:13:01", title: "Follow-up evidence available", detail: "A second turn completed on the same root thread. Interrupt support is proven separately." }
];

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

renderTimeline();

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
