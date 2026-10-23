// Download buttons on the preview page. page.ts inlines this file and allows it by hash in the
// page's content security policy; no other script can run there.
const css = document.getElementById("diagram-css").textContent;
const SVG_NS = "http://www.w3.org/2000/svg";
const PNG_SCALE = 2;

// A standalone copy of the diagram with its stylesheet, so it keeps its colors outside the page.
function standaloneSvg(svg, { bakeTheme }) {
  const copy = svg.cloneNode(true);
  const style = document.createElementNS(SVG_NS, "style");
  style.textContent = css;
  copy.insertBefore(style, copy.firstChild);
  if (bakeTheme) {
    // An image cannot follow the system theme later, so freeze the one on screen now. Inline
    // custom properties beat the stylesheet, including its dark-mode media query.
    const computed = getComputedStyle(svg);
    for (const name of css.match(/--(?:pele|tone|shadow)[\w-]*(?=:)/g) ?? []) {
      copy.style.setProperty(name, computed.getPropertyValue(name));
    }
  }
  return new XMLSerializer().serializeToString(copy);
}

function save(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function savePng(svg, filename) {
  const { width, height } = svg.viewBox.baseVal;
  const image = new Image();
  image.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(width * PNG_SCALE);
    canvas.height = Math.ceil(height * PNG_SCALE);
    const context = canvas.getContext("2d");
    context.fillStyle = getComputedStyle(svg).getPropertyValue("--pele-bg");
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => save(blob, filename), "image/png");
  };
  const markup = standaloneSvg(svg, { bakeTheme: true });
  // The canvas size above is what counts; drop max-width so the image is not squeezed.
  image.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(markup.replace("max-width:100%;", ""));
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-download]");
  if (!button) return;
  const section = button.closest(".diagram");
  const svg = section.querySelector("svg.pele");
  const name = section.dataset.filename;
  if (button.dataset.download === "svg") {
    const markup = standaloneSvg(svg, { bakeTheme: false });
    save(new Blob([markup], { type: "image/svg+xml" }), `${name}.svg`);
  } else {
    savePng(svg, `${name}.png`);
  }
});
