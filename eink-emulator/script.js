const scaleInput = document.getElementById("scale");
const gridInput = document.getElementById("grid");
const ditherInput = document.getElementById("dither");
const display = document.getElementById("display");
const timeElement = document.getElementById("time");

const updateScale = () => {
  const scale = Number(scaleInput.value);
  display.style.transform = `scale(${scale})`;
};

const updateToggles = () => {
  display.classList.toggle("grid", gridInput.checked);
  display.classList.toggle("dither", ditherInput.checked);
};

const updateTime = () => {
  const now = new Date();
  const hours = now.getHours().toString().padStart(2, "0");
  const minutes = now.getMinutes().toString().padStart(2, "0");
  timeElement.textContent = `${hours}:${minutes}`;
};

scaleInput.addEventListener("input", updateScale);
gridInput.addEventListener("change", updateToggles);
ditherInput.addEventListener("change", updateToggles);

updateScale();
updateToggles();
updateTime();
setInterval(updateTime, 1000 * 30);
