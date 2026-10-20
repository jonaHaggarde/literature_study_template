// Terminal-styled placeholder page. No network calls, no Claude
// invocation — see ../../gui-dev-notes.md. This just echoes what you
// type back into the scrollback with a note that it isn't connected
// yet, so the interaction shape (prompt, history, scrollback) is real
// even though the backend isn't.

const scrollback = document.getElementById("scrollback");
const input = document.getElementById("cmdInput");
const history = [];
let historyPos = -1;

function appendLine(text, cls) {
  const div = document.createElement("div");
  div.className = "console-line" + (cls ? " " + cls : "");
  div.textContent = text;
  scrollback.appendChild(div);
  scrollback.scrollTop = scrollback.scrollHeight;
}

appendLine("Literature Study Console (prototype)", "console-system");
appendLine("Nothing typed here reaches Claude yet — this page will call the local server's /chat endpoint once it exists.", "console-system");

input.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    const text = input.value.trim();
    if (!text) return;
    history.push(text);
    historyPos = history.length;
    appendLine("you › " + text, "console-user");
    appendLine("[offline] Not connected yet — see gui-dev-notes.md.", "console-system");
    input.value = "";
  } else if (e.key === "ArrowUp") {
    if (historyPos > 0) { historyPos--; input.value = history[historyPos]; }
    e.preventDefault();
  } else if (e.key === "ArrowDown") {
    if (historyPos < history.length - 1) { historyPos++; input.value = history[historyPos]; }
    else { historyPos = history.length; input.value = ""; }
    e.preventDefault();
  }
});

input.focus();
